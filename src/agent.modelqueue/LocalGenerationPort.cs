using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;

/// <summary>
/// R413: 本地生成执行面端口 (可替换 — 产品只依赖本接口, 不依赖任何具体推理后端程序集)。
///
/// 定位 (用户 2026-09-14 口径): 本地生成是「重新整理所有能力 → 精炼合理化链管道 → 提高 KPI」
/// 计划中的一个节点, **与 R351 无关** — R351 移除的是旧的「本地 LLM 使用」路径 (全走远端 API),
/// 不构成对新增 r1 本地生成的禁令。
///
/// 契约纪律 (R408): 实现必须是「进程 + HTTP」形态, 零 P/Invoke; <see cref="IsAvailable"/> 是
/// **真实探测** (模型文件存在 ∧ 二进制可解析), 探测不确定一律 false — 「没测到」≠「通过」。
/// </summary>
public interface ILocalGenerationPort
{
    /// <summary>真实就绪探测 (不得猜; 探测失败 → false)。</summary>
    bool IsAvailable { get; }

    /// <summary>执行面标识 (记账/可观测用, 如 "llama.cpp")。</summary>
    string BackendId { get; }

    /// <summary>生成一轮。失败必须回 <c>Success=false</c> + <c>Error</c> (不得抛穿调用方)。</summary>
    Task<LocalGenerationOutcome> GenerateAsync(LocalGenerationRequest request, CancellationToken ct = default);

    /// <summary>
    /// R465: 预热 —— 把长驻推理服务的**权重装载**提前到宿主启动期, 使它不再落在用户可见的门控轮路径上。
    /// 默认空实现 (测试桩/无本地后端无需实现)。纪律: 预热失败**不得抛穿** (只记账, 供遥测读取)。
    /// </summary>
    Task WarmupAsync(CancellationToken ct = default) => Task.CompletedTask;

    /// <summary>R465: 预热是否成功过 (未预热/失败 ⇒ false); 仅观测用。</summary>
    bool WarmupOk => false;
}

/// <summary>本地生成对话轮 (协议自洽, 不依赖 agent 主程序集)。</summary>
public sealed record LocalChatTurn(string Role, string Content);

/// <summary>本地生成请求。</summary>
public sealed class LocalGenerationRequest
{
    /// <summary>会话标识 (长驻前缀缓存归属; 空 = 一次性请求)。</summary>
    public string? SessionKey { get; init; }
    public int TurnIndex { get; init; } = 1;
    public List<LocalChatTurn> Turns { get; init; } = new();
    public int MaxTokens { get; init; } = 256;

    /// <summary>
    /// R429 决策路径缓存钉死: false ⇒ 该次生成本地关前缀缓存 (CompletionReuse.Reconciliation)。
    /// 默认 true = 既有生产口径 (逐位零回归)。
    /// 依据 (R429 传输级实测): 同一 prompt 在「全量评估」与「部分前缀复用」下 token 序列不等
    /// (180 / 97 / 215), 且可出现 S/P 判定翻转 ⇒ 决策路径不得依赖缓存复用。
    /// </summary>
    public bool CacheReuse { get; init; } = true;
}

/// <summary>
/// 本地生成结果。记账口径 (R411 钉死, 勿改): <see cref="TokensEvaluated"/> = 本轮 prompt 总长,
/// <see cref="PromptNewTokens"/> = 新评估数, <see cref="CachedTokens"/> = 命中复用数;
/// 恒等: TokensEvaluated == PromptNewTokens + CachedTokens。
/// </summary>
public sealed class LocalGenerationOutcome
{
    public bool Success { get; init; }
    public string Content { get; init; } = string.Empty;
    public int TokensEvaluated { get; init; }
    public int PromptNewTokens { get; init; }
    public int CachedTokens { get; init; }
    public int GeneratedTokens { get; init; }
    public long ElapsedMs { get; init; }
    public string? Error { get; init; }
    public string Model { get; init; } = "local";

    /// <summary>R430: prompt 指纹 (SHA-256 前 16 hex; 空 = 后端未上报 — 缺失不等于错误)。</summary>
    public string PromptSha16 { get; init; } = string.Empty;

    /// <summary>R430: 请求体指纹 (覆盖全部请求字段: n_predict/samplers/cache_prompt/seed...)。</summary>
    public string RequestSha16 { get; init; } = string.Empty;

    /// <summary>R430: 请求关键字段摘要 (指纹不同时用于定位)。</summary>
    public string RequestFields { get; init; } = string.Empty;

    /// <summary>记账恒等校验 (口径一致才可采信; 违规 ⇒ 该次结果作废并降级远端)。</summary>
    public bool AccountingConsistent => TokensEvaluated == PromptNewTokens + CachedTokens;
}

/// <summary>本地通道不采用的原因 (拒绝原因必须显式 — 不允许静默跳过)。</summary>
public enum LocalChannelRejectReason
{
    None,
    ChannelDisabled,
    KindNotAllowed,
    ImageRequest,
    PromptTooLong,
    PortMissing,
    PortUnavailable,
    AccountingInconsistent,
}

public sealed record LocalChannelDecision(bool Allowed, LocalChannelRejectReason Reason)
{
    public static readonly LocalChannelDecision Allow = new(true, LocalChannelRejectReason.None);

    public string ReasonText => Reason switch
    {
        LocalChannelRejectReason.None => "ok",
        LocalChannelRejectReason.ChannelDisabled => "channel_disabled",
        LocalChannelRejectReason.KindNotAllowed => "kind_not_allowed",
        LocalChannelRejectReason.ImageRequest => "image_request",
        LocalChannelRejectReason.PromptTooLong => "prompt_too_long",
        LocalChannelRejectReason.PortMissing => "port_missing",
        LocalChannelRejectReason.PortUnavailable => "port_unavailable",
        LocalChannelRejectReason.AccountingInconsistent => "accounting_inconsistent",
        _ => "unknown",
    };
}

/// <summary>
/// 本地通道采用判据 (预注册, 单点可测)。判定顺序 = 配置 → 请求形态 → 端口, 每步都有显式原因。
/// </summary>
public static class LocalChannelPolicy
{
    /// <summary>默认可本地化的任务种类 (轻任务, 输出短且性能不敏感; 与 ModelSelectionPolicy.LowSensitivityKinds 同源)。</summary>
    public static readonly TaskKindHint[] DefaultAllowedKinds =
    {
        TaskKindHint.ContextCompression,
        TaskKindHint.KeywordTagging,
        TaskKindHint.TendencyAnalysis,
        TaskKindHint.IntentClassification,
    };

    public static bool KindAllowed(LocalChannelConfig config, TaskKindHint kind)
    {
        if (config.AllowGeneral && kind == TaskKindHint.General)
            return true;

        if (config.AllowedKinds.Count > 0)
        {
            foreach (var name in config.AllowedKinds)
            {
                if (string.Equals(name, kind.ToString(), StringComparison.OrdinalIgnoreCase))
                    return true;
            }
            return false;
        }

        foreach (var k in DefaultAllowedKinds)
        {
            if (k == kind)
                return true;
        }
        return false;
    }

    public static LocalChannelDecision Evaluate(
        QueuePrompt prompt, TaskKindHint kind, LocalChannelConfig config, ILocalGenerationPort? port)
    {
        if (!config.IsReady)
            return new LocalChannelDecision(false, LocalChannelRejectReason.ChannelDisabled);

        // 带图请求必须落视觉模型 (远端) — 本地通道是纯文本执行面
        if (prompt.ImageUrls.Count > 0)
            return new LocalChannelDecision(false, LocalChannelRejectReason.ImageRequest);

        if (!KindAllowed(config, kind))
            return new LocalChannelDecision(false, LocalChannelRejectReason.KindNotAllowed);

        if (config.MaxPromptTokens > 0 && prompt.EstimatedTokens > config.MaxPromptTokens)
            return new LocalChannelDecision(false, LocalChannelRejectReason.PromptTooLong);

        if (port is null)
            return new LocalChannelDecision(false, LocalChannelRejectReason.PortMissing);

        if (!port.IsAvailable)
            return new LocalChannelDecision(false, LocalChannelRejectReason.PortUnavailable);

        return LocalChannelDecision.Allow;
    }
}

/// <summary>
/// 本地通道计数 (可观测/对账; 全部 Interlocked)。纪律: 未尝试 ⇒ <see cref="Attempted"/>==0,
/// 「没测到」不得当成「通过」——外部判红判绿都要看这四个数。
/// </summary>
public sealed class LocalChannelCounters
{
    /// <summary>真实发起过的本地生成次数 (端口被判据放行后才计)。</summary>
    public long Attempted;

    /// <summary>本地生成成功并直接作为本轮结果返回的次数。</summary>
    public long Succeeded;

    /// <summary>本地发起但失败/记账违规 ⇒ 降级远端的次数 (降级必须可见)。</summary>
    public long Degraded;

    /// <summary>判据拒绝次数 (未发起; 原因见 <see cref="LastRejectReason"/>)。</summary>
    public long Rejected;

    /// <summary>记账恒等式违规次数 (tokens_evaluated != prompt_n + cache_n)。</summary>
    public long AccountingViolations;

    public string? LastRejectReason;
    public string? LastDegradeReason;

    public void RecordAttempt() => Interlocked.Increment(ref Attempted);
    public void RecordSuccess() => Interlocked.Increment(ref Succeeded);
    public void RecordDegrade(string reason)
    {
        Interlocked.Increment(ref Degraded);
        LastDegradeReason = reason;
    }
    public void RecordReject(string reason)
    {
        Interlocked.Increment(ref Rejected);
        LastRejectReason = reason;
    }
    public void RecordAccountingViolation(string reason)
    {
        Interlocked.Increment(ref AccountingViolations);
        LastDegradeReason = reason;
    }

    public long Total => Interlocked.Read(ref Attempted) + Interlocked.Read(ref Rejected);
}


// ─────────────────────────────────────────────────────────────────────────────
// R413 前置门 (Local Turn Gate)
// 语义: 每轮先由本地 r1 判定「用户消息是否携带新增诉求」。
//   Pass = 有新增 ⇒ 照常走远端主调用。
//   Skip = 无新增 (纯认可/确认/寒暄/重复) ⇒ 本地消化, 不发远端主调用。
// 判据预注册: docs/plans/v0.35.0-r413-r1-local-verdict-token-budget.md §7 (分母=臂 A)。
// 反空心纪律: 无法解析/失败/记账违规/空回 **一律 Undecided** ⇒ 调用方必须降级远端;
//   「没测到」≠「假」—— 绝不因解析失败而静默跳过 (那是把增益建立在幻觉上)。
// ─────────────────────────────────────────────────────────────────────────────

/// <summary>R413 前置门结论 (真假判别的语义落点)。</summary>
public enum TurnGateVerdict
{
    /// <summary>携带新增诉求 ⇒ 走远端。</summary>
    Pass = 0,

    /// <summary>无新增诉求 ⇒ 本地消化 (跳过远端主调用)。</summary>
    Skip = 1,
}

/// <summary>R413 前置门判别结果。<c>Decided=false</c> ⇒ 调用方必须降级远端。</summary>
public sealed record TurnGateOutcome(bool Decided, TurnGateVerdict Verdict, string Raw, string? Error)
{
    // R413 证据纪律: 未判定也必须带回原文 (否则"为什么没判出来"无从对账)。
    public static TurnGateOutcome Undecided(string error, string raw = "") => new(false, TurnGateVerdict.Pass, raw, error);
    public static TurnGateOutcome Decide(TurnGateVerdict v, string raw) => new(true, v, raw, null);
}

/// <summary>R413 前置门判别器 (纯函数 — 可机检, 不依赖端口/网络)。</summary>
public static class TurnGateJudge
{
    /// <summary>判别 prompt (挂 role 额外数据: ProfileSeed + 成长经历)。</summary>
    public static string BuildPrompt(string userMessage, string? roleSeed, string? growthBlock)
    {
        var sb = new System.Text.StringBuilder();
        sb.Append("判别用户这一条消息是否携带新的诉求或新信息。\n");
        sb.Append("- S = 无新增: 纯认可/确认/寒暄/致谢/重复上一轮内容/只有表情。\n");
        sb.Append("- P = 有新增: 新问题/新要求/补充条件/纠正/提供新信息。\n");
        sb.Append("示例:\n");
        sb.Append("用户: 好，按这个来。 → S\n");
        sb.Append("用户: 嗯。 → S\n");
        sb.Append("用户: 收到，谢谢。 → S\n");
        sb.Append("用户: 另外，测试命令是什么？ → P\n");
        sb.Append("用户: 不对，你上一轮不准确，请重新确认。 → P\n");
        // R434 承重修正 (真机实测根因): 上面两条 P 例**全带机械信号**(另外/不对/？) ⇒ 生产链里
        // 结构性 MechanicalPass, 根本进不到本门 ⇒ 残余带内 r1 只见 S 例, 学到「短消息 ⇒ S」
        // ⇒ 恒 Skip (R432 实测恒定 Skip 的因果源)。补两条**残余带原生 P 例**
        // (无 ?/？、无问句/诉求/纠正词、无数字、长度<24) 构成带内 S/P 对照。
        sb.Append("用户: 再说一遍。 → P\n");
        sb.Append("用户: 展开说说。 → P\n");
        sb.Append("先思考, 思考结束后必须另起一行只写一个字母 (S 或 P), 不要写其他内容。\n");
        sb.Append("无法确定时也必须写 P (宁可多走一次远端)。\n");
        // R413 实测 (§7.3): 判别提示必须**短** — 角色全文灌入会挤占上下文与生成预算,
        // 真机表现为输出被截断在思考链中途 (只有 <think> 没有闭合) ⇒ 判别恒降级。
        if (!string.IsNullOrWhiteSpace(roleSeed))
        {
            sb.Append("【角色设定】").Append(Clip(roleSeed, 300)).Append('\n');
        }
        if (!string.IsNullOrWhiteSpace(growthBlock))
        {
            sb.Append(Clip(growthBlock, 300)).Append('\n');
        }
        sb.Append("【用户消息】").Append((userMessage ?? string.Empty).Trim()).Append('\n');
        sb.Append("答案:\n");
        return sb.ToString();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // R434 双条件 (真机实测根因): 残余带内 r1 对「短促真诉求」误判 Skip
    //   (「再讲一遍。」「讲细一点。」「从头再说。」实测 3/4 被跳 ⇒ 用户拿到空话, 真诉求丢失)。
    // 修: r1 的 Skip 只在**结构上确认为「认可族」**时生效 ⇒ 否则降级 Pass (宁可多走一次远端)。
    // 方向性: 这是**白名单**(承认哪些可以省) 而非黑名单(猜测哪些不能省) ⇒ 未知一律保守。
    // ─────────────────────────────────────────────────────────────────────────
    private const string AckFamilyChars = "好嗯行明白了知道谢收到多辛苦可以先就的";

    /// <summary>
    /// R434: 「认可族」结构确认 —— 纯认可/确认/致谢短句 (去标点后 ≤10 字, 且字符全属白名单字符集)。
    /// 只作**第二条件**: r1 判 Skip ∧ 本判为真 ⇒ 才允许跳过远端 (r1 不 Skip 时本判无意义);
    /// 结构不确认 ⇒ 降级 Pass (宁多走一次远端, 也不让真诉求被跳成空话)。
    /// </summary>
    public static bool MechanicalAck(string? userMessage)
    {
        var m = (userMessage ?? string.Empty).Trim();
        if (m.Length == 0) return false;
        var n = 0;
        foreach (var ch in m)
        {
            if (char.IsPunctuation(ch) || char.IsWhiteSpace(ch) || char.IsSymbol(ch)) continue;
            if (AckFamilyChars.IndexOf(ch) < 0) return false;
            if (++n > 10) return false;
        }
        return n > 0;
    }

    /// <summary>
    /// R465: 「纯复述族」结构确认 —— 用户只要求把**上一条答复原样重来**, 不含任何新诉求。
    /// 机械判据 (三道全过才算, 任一道不过 ⇒ false):
    ///   ① 归一化 (去标点/空白/符号) 后必须含**完整复述标记** (再讲一遍 / 从头再说 / 重复一遍 ...);
    ///      只含「再讲」「继续」「详细」这类不完整词的**不算** (它们可能要求新内容 ⇒ 走远端)。
    ///   ② 归一化后长度 ≤14 且**每个字符都属复述白名单字符集** ⇒ 任何内容字 (细/换/法/增加/命令...) 立即 false。
    ///   ③ 无问号 ⇒ 疑问句永远走远端。
    /// 用途限制: 本判只允许**前置门直接 Skip** (本地消化 = 回放上一条答复原文, 零远端调用);
    /// 调用方必须让 <see cref="MechanicalPass"/> 优先于本判 (新诉求/疑问/长文本永不被吸收)。
    /// </summary>
    public static bool IsPureRepeat(string? userMessage)
    {
        var m = (userMessage ?? string.Empty).Trim();
        if (m.Length == 0 || m.Length > 24) return false;
        var sb = new System.Text.StringBuilder(m.Length);
        foreach (var ch in m)
        {
            if (ch is '?' or '？') return false;                                   // ③ 疑问句永不吸收
            if (char.IsPunctuation(ch) || char.IsWhiteSpace(ch) || char.IsSymbol(ch)) continue;
            sb.Append(ch);
        }
        var n = sb.ToString();
        if (n.Length is 0 or > 14) return false;
        foreach (var ch in n)                                                      // ② 白名单字符集
            if (RepeatFamilyChars.IndexOf(ch) < 0) return false;
        foreach (var marker in RepeatMarkers)                                       // ① 完整复述标记
            if (n.Contains(marker, StringComparison.Ordinal)) return true;
        return false;
    }

    /// <summary>R465: 复述族白名单字符集 (复述标记 + 指代词的全部用字; 任何集合外字符 ⇒ 不是纯复述)。</summary>
    private const string RepeatFamilyChars = "再讲遍次重复述从头说要你上面那条这句话的来回新下念看给把一吧哦嗯啊呀啦哇";

    /// <summary>R465: 完整复述标记 (穷举; 表外一律不吸收) —— 语义 = 「把上一条答复原样给我」。</summary>
    private static readonly string[] RepeatMarkers =
    {
        "再讲一遍", "再说一遍", "再讲一次", "再说一次", "重复一遍", "重复一次", "复述一遍",
        "从头再说", "从头再讲", "重新说一遍", "重新讲一遍", "再来一遍", "再念一遍", "再看一遍",
        "再说下", "再讲下",
    };

    public static string Clip(string s, int max)
    {
        var t = s.Trim();
        return t.Length <= max ? t : t[..max];
    }

    /// <summary>被跳过轮的本地回复 prompt (一句确认 + 复述方向, 不新增内容)。</summary>
    public static string BuildAckPrompt(string userMessage)
    {
        return "用户上一条是对当前方向的认可或无新增诉求。\n" +
               "请用一句中文确认收到, 并复述当前正在推进的任务方向。\n" +
               "不要新增内容, 不要提问, 不要解释。\n" +
               "【用户消息】" + (userMessage ?? string.Empty).Trim() + "\n" +
               "回答:";
    }

    /// <summary>
    /// 解析本地输出。只认「独立成词的 S/P」(取最后一次出现) ⇒ 兼容 r1 的思考链残留。
    /// 无法判定 ⇒ <c>Decided=false</c> (绝不猜)。
    /// </summary>
    public static TurnGateOutcome Parse(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return TurnGateOutcome.Undecided("empty", raw ?? string.Empty);
        var text = raw.Trim();

        // R413 实测铁律: r1 的 <think> 正文里会同时出现「有新增/无新增」等词 ⇒ 绝不在推理正文里找标记
        // (那等于把增益建在噪声上)。只认「思考块之后」的结论区: 取最后一个 思考块闭合标记 之后的文本;
        // 无思考块时取末尾 64 字符。结论区为空 ⇒ 未判定 (降级远端), 绝不猜。
        var conclusion = text;
        var close = text.LastIndexOf(ThinkClose, StringComparison.Ordinal);
        if (close >= 0) conclusion = text[(close + ThinkClose.Length)..];
        else
        {
            var open = text.LastIndexOf(ThinkOpen, StringComparison.Ordinal);
            if (open >= 0)
            {
                // 有思考块但没闭合 ⇒ 模型被 max_tokens 截断, 结论还没写出来
                return TurnGateOutcome.Undecided("thinking_truncated", text);
            }
            if (conclusion.Length > 64) conclusion = conclusion[^64..];
        }
        conclusion = conclusion.Trim();
        if (conclusion.Length == 0) return TurnGateOutcome.Undecided("empty_conclusion", text);

        int lastSkip = -1, lastPass = -1;
        void Note(bool skip, int idx)
        {
            if (skip) { if (idx > lastSkip) lastSkip = idx; }
            else if (idx > lastPass) lastPass = idx;
        }
        foreach (System.Text.RegularExpressions.Match m in
                 System.Text.RegularExpressions.Regex.Matches(conclusion, @"(?<![A-Za-z])([SsPp])(?![A-Za-z])"))
        {
            Note(m.Groups[1].Value == "S" || m.Groups[1].Value == "s", m.Index);
        }
        foreach (var pat in new[] { "无新增", "无新", "无需", "跳过", "认可", "采纳", "有新增", "新要求", "新问题", "纠正", "继续", "需要" })
        {
            var k = conclusion.LastIndexOf(pat, StringComparison.Ordinal);
            if (k < 0) continue;
            Note(pat is "无新增" or "无新" or "无需" or "跳过" or "认可" or "采纳", k);
        }
        if (lastSkip < 0 && lastPass < 0) return TurnGateOutcome.Undecided("no_marker", text);
        return TurnGateOutcome.Decide(lastSkip > lastPass ? TurnGateVerdict.Skip : TurnGateVerdict.Pass, text);
    }

    /// <summary>
    /// R413 机械前置门 (零 token, 确定性): 只要消息里有任何「必须走远端」的机械信号 ⇒
    /// 直接 Pass, **根本不问 r1**。目的 = 把假阴性 (新诉求/纠正被误跳) 结构性消掉,
    /// 而不是靠小模型判对。表是穷举的、可机检的; 表未覆盖的短消息才交给 r1。
    /// 依据 (真机负控, 2026-09-14): 纯 r1 判别时「另外，测试命令是什么？」「不对，你上一条不准确」
    /// 被判 Skip ⇒ 用户拿到空话。这两条现在有机械信号 (问号/另外/不对/重新) ⇒ 结构性 Pass。
    /// </summary>
    public static bool MechanicalPass(string? userMessage)
    {
        if (string.IsNullOrWhiteSpace(userMessage)) return true;      // 说不清 ⇒ 保守走远端
        var m = userMessage.Trim();
        foreach (var ch in "?？")
            if (m.Contains(ch)) return true;
        foreach (var w in QuestionSignals)
            if (m.Contains(w, StringComparison.Ordinal)) return true;
        foreach (var w in RequestSignals)
            if (m.Contains(w, StringComparison.Ordinal)) return true;
        foreach (var w in CorrectionSignals)
            if (m.Contains(w, StringComparison.Ordinal)) return true;
        foreach (var ch in "`/\\")
            if (m.Contains(ch)) return true;
        for (var i = 0; i < m.Length; i++)
            if (char.IsDigit(m[i])) return true;                       // 数字 ⇒ 可能带参数 (保守)
        return m.Length >= SubstantiveLengthThreshold;                 // 长消息 ⇒ 大概率有实质内容 (保守)
    }

    /// <summary>长度阈值: ≥ 该长度视为有实质内容 (保守走远端; 宁可少省, 不可误跳)。</summary>
    private const int SubstantiveLengthThreshold = 24;

    /// <summary>疑问信号 (问询 ⇒ 必须远端)。</summary>
    private static readonly string[] QuestionSignals =
    {
        "什么", "怎么", "如何", "为什么", "为何", "哪个", "哪一", "谁", "何时", "多少",
        "是否", "能不能", "可以吗", "行吗", "吗", "呢", "请问", "请教",
        "解释", "说明", "介绍", "对比", "区别", "分析",
    };

    /// <summary>新诉求/指令信号 (要做事 ⇒ 必须远端)。</summary>
    private static readonly string[] RequestSignals =
    {
        "请", "帮我", "帮忙", "给我", "我要", "需要", "另外", "还有", "补充", "新增",
        "加", "删", "改", "修", "写", "生成", "创建", "新建", "执行", "运行", "跑",
        "测试", "部署", "提交", "回滚", "优化", "重构", "继续做", "下一步", "现在", "把",
    };

    /// <summary>纠正/失败信号 (用户指出问题 ⇒ 必须远端)。</summary>
    private static readonly string[] CorrectionSignals =
    {
        "不对", "错了", "不正确", "不准确", "有问题", "漏", "缺", "重新", "再确认",
        "纠正", "不是", "没对", "失败", "报错", "异常", "崩溃", "不生效",
    };

    /// <summary>思考链标记 (转义写: 尖括号字面量会被写入通道吃掉, 只有转义可靠)。</summary>
        public const string ThinkClose = "\u003c/think\u003e";
        public const string ThinkOpen = "\u003cthink\u003e";

        /// <summary>
        /// 去掉思考链, 只留结论区 (R413 实测: r1 把推理写进 content ⇒ 直接回显给用户 = 泄漏推理)。
        /// 规则: 有闭合标记 ⇒ 取其后的内容; 有开启无闭合 (被预算截断) ⇒ 空串 (调用方必须兜底)。
        /// </summary>
        public static string StripThinking(string? raw)
        {
            if (string.IsNullOrEmpty(raw)) return string.Empty;
            var text = raw.Trim();
            var close = text.LastIndexOf(ThinkClose, StringComparison.Ordinal);
            if (close >= 0) return text[(close + ThinkClose.Length)..].Trim();
            return text.LastIndexOf(ThinkOpen, StringComparison.Ordinal) >= 0 ? string.Empty : text;
        }
}
    /// <summary>R413 前置门计数 (可观测; Judged==0 ⇒ 未判过, 不得当"通过")。</summary>
public sealed class TurnGateCounters
{
    private long _judged;
    private long _skipped;
    private long _passed;
    private long _degraded;
    private long _accountingViolations;

    private long _mechanicalPasses;

    private long _templateAcks;

    private long _skipRejected;
    // R444: 前置门 (§ Ack 前置) 相关计数 —— 省下的 r1 调用与被破坏的不变量都必须可见。
    private long _mechanicalNonAcks;
    private long _prefilterViolations;

    // R465: 纯复述族直接 Skip 计数 (零 r1 + 零远端调用)。
    private long _mechanicalRepeats;

    private long _cachePinned;
    private int _lastCachedTokens;
    private int _lastEvalTokens = -1;
    private int _lastNewTokens = -1;
    private int _lastGenTokens = -1;

    public long Judged => Interlocked.Read(ref _judged);
    public long MechanicalPasses => Interlocked.Read(ref _mechanicalPasses);
    public long TemplateAcks => Interlocked.Read(ref _templateAcks);
    public long Skipped => Interlocked.Read(ref _skipped);
    public long Passed => Interlocked.Read(ref _passed);
    public long Degraded => Interlocked.Read(ref _degraded);
    public long AccountingViolations => Interlocked.Read(ref _accountingViolations);

    /// <summary>R429: 门判显式关前缀缓存的次数 (端口纪律: 被使用计数必须可观测)。</summary>
    public long CachePinned => Interlocked.Read(ref _cachePinned);

    /// <summary>R429: 最近一次门判的缓存命中数 (cache_n) — 钉死后应恒为 0。</summary>
    public int LastCachedTokens => Volatile.Read(ref _lastCachedTokens);

    /// <summary>R443: 最近一次门判的 prompt 总 token 数 (llama-server 真值; -1 = 未走 r1)。</summary>
    public int LastEvalTokens => Volatile.Read(ref _lastEvalTokens);

    /// <summary>R443: 最近一次门判的**新评估** token 数 (真值; -1 = 未走 r1)。</summary>
    public int LastNewTokens => Volatile.Read(ref _lastNewTokens);

    /// <summary>R443: 最近一次门判的**生成** token 数 (真值; -1 = 未走 r1)。</summary>
    public int LastGenTokens => Volatile.Read(ref _lastGenTokens);

    public string? LastBasis { get; private set; }

    /// <summary>R430: 最近一次门判的 prompt 指纹 (空 = 后端未上报)。</summary>
    public string? LastPromptSha { get; private set; }

    /// <summary>R430: 最近一次门判的请求体指纹。</summary>
    public string? LastRequestSha { get; private set; }

    /// <summary>R430: 最近一次门判的请求关键字段摘要。</summary>
    public string? LastRequestFields { get; private set; }

    /// <summary>R430: 上一次门判实际使用的角色种子指纹 (分辨「种子漂移」与「引擎不确定」)。</summary>
    public string? LastRoleSeedSha { get; private set; }

    private int _lastPromptChars;
    private int _lastRoleSeedChars;
    private int _lastGrowthChars;
    private int _lastGrowthLines;

    /// <summary>R431: 最近一次门判**实发** prompt 的字符数 (未走 r1 = 0)。</summary>
    public int LastPromptChars => Volatile.Read(ref _lastPromptChars);

    /// <summary>R431: 最近一次门判挂的角色种子字符数 (null ⇒ 0)。</summary>
    public int LastRoleSeedChars => Volatile.Read(ref _lastRoleSeedChars);

    /// <summary>R431: 最近一次门判挂的 role 额外数据 (成长经历) 字符数 — null/空 ⇒ 0 (未挂载臂的负控读数)。</summary>
    public int LastGrowthChars => Volatile.Read(ref _lastGrowthChars);

    /// <summary>R431: 成长块渲染出的域行数 (块内 '\n' 计数; 部分行被截断时仍计入已渲染行)。</summary>
    public int LastGrowthLines => Volatile.Read(ref _lastGrowthLines);

    /// <summary>
    /// R431: 记录本次门判**实发** prompt 的形状 (长度取自实际被发出的那一份 prompt, 不做二次重建 ⇒ 无漂移)。
    /// 「挂了 role 额外数据」与「没挂」在读数上必须可区分, 否则挂载只是接口上有字段。
    /// </summary>
    public void RecordPromptShape(int promptChars, int roleSeedChars, string? growthBlock)
    {
        Volatile.Write(ref _lastPromptChars, promptChars);
        Volatile.Write(ref _lastRoleSeedChars, roleSeedChars);
        var g = growthBlock ?? string.Empty;
        Volatile.Write(ref _lastGrowthChars, g.Length);
        var lines = 0;
        foreach (var ch in g) if (ch == '\n') lines++;
        Volatile.Write(ref _lastGrowthLines, lines);
    }

    /// <summary>机械前置门命中 (零 token 直接 Pass, 未询问 r1) — 必须可观测, 否则看不出"省了判别"。</summary>
    public void RecordMechanicalPass() { Interlocked.Increment(ref _mechanicalPasses); LastBasis = "mechanical:pass→remote"; }

    /// <summary>被跳过轮使用非 LLM 模板回复 (真机实证: LLM 生成会复读/反问)。</summary>
    public void RecordTemplateAck() { Interlocked.Increment(ref _templateAcks); }

    public void RecordJudged() => Interlocked.Increment(ref _judged);
    public void RecordSkipped() { Interlocked.Increment(ref _skipped); LastBasis = "gate:skip→local"; }
    public void RecordPassed() { Interlocked.Increment(ref _passed); LastBasis = "gate:pass→remote"; }

    /// <summary>R434: r1 判 Skip 但结构上非「认可族」⇒ 降级 Pass 的次数 (被拒的省钱机会必须可观测)。</summary>
    public long SkipRejected => Interlocked.Read(ref _skipRejected);

    /// <summary>R444: 前置门命中次数 (¬Ack ⇒ 构造性必然 Pass, 未询问 r1)。</summary>
    public long MechanicalNonAcks => Interlocked.Read(ref _mechanicalNonAcks);

    /// <summary>R444: 前置门不变量被破坏次数 (Skip ∧ ¬Ack 本应不可达) — 恒 0 才是 fail-closed。</summary>
    public long PrefilterViolations => Interlocked.Read(ref _prefilterViolations);

    /// <summary>R465: 纯复述族命中次数 (零 r1 + 零远端调用, 本地回放上一条答复原文)。</summary>
    public long MechanicalRepeats => Interlocked.Read(ref _mechanicalRepeats);

    /// <summary>R465: 前置门直接 Skip —— 纯复述族 (只要求原样重来, 无新诉求)。</summary>
    public void RecordMechanicalRepeat() { Interlocked.Increment(ref _mechanicalRepeats); LastBasis = "mechanical:repeat→local"; }

    /// <summary>R434: r1 判 Skip 但结构确认失败 (非认可族) ⇒ 降级 Pass, 宁多走一次远端。</summary>
    public void RecordSkipRejected() { Interlocked.Increment(ref _skipRejected); LastBasis = "gate:skip_rejected_nonack→remote"; }

    /// <summary>R444: 前置门命中 (¬Ack, 零 token 直接 Pass) — 不建 prompt、不问 r1, 判决与后置否决逐位同。</summary>
    public void RecordMechanicalNonAck() { Interlocked.Increment(ref _mechanicalNonAcks); LastBasis = "mechanical:nonack→remote"; }

    /// <summary>R444: 前置门不变量被破坏 (Skip ∧ ¬Ack 竟抵达后置否决) — fail-closed 落盘, 恒 0。</summary>
    public void RecordPrefilterViolation() { Interlocked.Increment(ref _prefilterViolations); }

    public void RecordDegraded(string reason)
    {
        Interlocked.Increment(ref _degraded);
        LastBasis = "gate:degraded:" + reason + "→remote";
    }

    public void RecordAccountingViolation(string reason)
    {
        Interlocked.Increment(ref _accountingViolations);
        LastBasis = "gate:accounting_violation:" + reason + "→remote";
    }

    /// <summary>R429: 门判请求已钉死缓存态 (显式关前缀缓存 + 记录本次 cache_n)。
    /// R443: 同时记录 llama-server 上报的**真值** token 三元组 (tokens_evaluated / prompt_n / gen_n),
    /// 用于把本地 r1 成本口径从「字符/2 折算」升级为「tokenizer 真值」。</summary>
    public void RecordCachePinned(int cachedTokens, string? promptSha = null, string? requestSha = null, string? requestFields = null,
        int evalTokens = -1, int newTokens = -1, int genTokens = -1)
    {
        Interlocked.Increment(ref _cachePinned);
        Volatile.Write(ref _lastCachedTokens, cachedTokens);
        Volatile.Write(ref _lastEvalTokens, evalTokens);
        Volatile.Write(ref _lastNewTokens, newTokens);
        Volatile.Write(ref _lastGenTokens, genTokens);
        LastPromptSha = promptSha;
        LastRequestSha = requestSha;
        LastRequestFields = requestFields;
    }

    /// <summary>R430: 记录本次门判的角色种子指纹 (调用方在构造 prompt 处提供; null = 未走 r1 判别)。</summary>
    public void RecordRoleSeed(string? roleSeed)
    {
        if (roleSeed is null) return;
        LastRoleSeedSha = LocalInputFingerprint.Sha16(roleSeed);
    }
}

/// <summary>R426: 本地关系判官结论 (字母 ∈ {C,A,N}; 交给 CorrectionDetector 的解析面, 不另立语义)。</summary>
public sealed record RelationJudgeOutcome(string Letter, string Raw, int CompletionTokens, int PromptTokens = -1, int PromptNewTokens = -1);

/// <summary>R426: 关系判官本地化计数 (可观测 — <c>Local==0 ∧ Fallback&gt;0</c> ⇒ 本地未生效, 不靠猜)。</summary>
public sealed class RelationJudgeCounters
{
    private long _attempts;
    private long _local;
    private long _fallback;
    private long _accountingViolations;
    private long _cachePinned;

    public long Attempts => Interlocked.Read(ref _attempts);
    public long Local => Interlocked.Read(ref _local);
    public long Fallback => Interlocked.Read(ref _fallback);
    public long AccountingViolations => Interlocked.Read(ref _accountingViolations);

    /// <summary>R429: 判官显式关前缀缓存的次数。</summary>
    public long CachePinned => Interlocked.Read(ref _cachePinned);

    public string? LastSource { get; private set; }
    public string? LastLetter { get; private set; }

    public void RecordAttempt() => Interlocked.Increment(ref _attempts);

    /// <summary>R429: 判官请求已钉死缓存态 (显式关前缀缓存)。</summary>
    public void RecordCachePinned() => Interlocked.Increment(ref _cachePinned);

    public void RecordLocal(string letter)
    {
        Interlocked.Increment(ref _local);
        LastSource = "local";
        LastLetter = letter;
    }

    public void RecordFallback(string reason)
    {
        Interlocked.Increment(ref _fallback);
        LastSource = "remote_fallback:" + reason;
    }

    public void RecordAccountingViolation(string reason)
    {
        Interlocked.Increment(ref _accountingViolations);
        LastSource = "local:accounting_violation:" + reason + "→remote";
    }
}

/// <summary>
/// R426: 本地关系判官输出规范化 (纯函数, 可机检 — 不依赖端口/网络)。
///
/// 纪律与 <see cref="TurnGateJudge.Parse"/> 同源 (R413 实测铁律): **绝不在思考链正文里找标记**
/// (那等于把增益建在噪声上)。只认「思考块闭合之后」的结论区:
/// <list type="bullet">
/// <item>有开无闭 (被 max_tokens 截断) ⇒ 未判定 ⇒ 调用方**远端兜底**;</item>
/// <item>结论区无独立字母 ⇒ 未判定 ⇒ 远端兜底 (绝不猜成 Neutral — 「没测到」≠「判过」);</item>
/// <item>多个独立字母 ⇒ 取**最后**一个 (结论写在推理之后)。</item>
/// </list>
/// </summary>
public static class RelationLetterJudge
{
    /// <summary>
    /// R435: 结论区候选词表 —— **空**（有意）。
    /// 曾经加过「纠正/否定/认可/采纳/新话题/无关 ⇒ 词表定字母」的兜底，被**既有预注册判据 J13** 否决:
    /// `RelationJudgeLocalizationTests.J13` 明文要求「这是采纳」这类**散文必须未判定（交远端）**。
    /// 且四臂实测（A1/A2/A3 vs A0）词表**零增益**（old≡new 逐例相同）⇒ 按「打分不升即回退」撤回。
    /// 结论：判官契约 = 结论区必须有**独立字母**；散文兜底属门（<see cref="TurnGateJudge"/>）的语义，不搬到这里。
    /// </summary>
    private static readonly (string Word, char Letter)[] ConclusionWords =
        System.Array.Empty<(string Word, char Letter)>();

    /// <summary>无思考块闭合标记时，只看结论区尾部这么多字符（镜像 Parse: 防在推理正文里找标记）。</summary>
    private const int ConclusionTailChars = 64;

    /// <summary>规范化: 成功 → <c>true</c> 且 <paramref name="letter"/> ∈ {C,A,N}。</summary>
    public static bool TryNormalize(string? raw, out string letter)
        => TryNormalize(raw, out letter, out _);

    /// <summary>
    /// R435: 带**失败原因**的重载 —— 归因可观测（R434 的缺口：本地原始输出不入遥测,
    /// 遥测里 `letter` 在 fallback 分支被远端文本覆盖 ⇒ 12 条里看不出失败原因）。
    /// 原因枚举（机检可断言）: <c>empty</c> / <c>thinking_truncated</c> / <c>empty_conclusion</c> / <c>no_marker</c> / <c>ok</c>。
    /// </summary>
    public static bool TryNormalize(string? raw, out string letter, out string reason)
    {
        letter = string.Empty;
        reason = "empty";
        if (string.IsNullOrWhiteSpace(raw)) return false;
        var text = raw.Trim();

        var close = text.LastIndexOf(TurnGateJudge.ThinkClose, StringComparison.Ordinal);
        if (close >= 0)
        {
            text = text[(close + TurnGateJudge.ThinkClose.Length)..];
        }
        else if (text.LastIndexOf(TurnGateJudge.ThinkOpen, StringComparison.Ordinal) >= 0)
        {
            reason = "thinking_truncated";   // 有开无闭: 结论还没写出来 (R435: 预算不足的确定形态)
            return false;
        }
        else if (text.Length > ConclusionTailChars)
        {
            // R435: 无思考块 ⇒ 只看尾部 (与 Parse 同规则; 原实现对全文取「最后一个字母」= 允许从推理正文取字母)
            text = text[^ConclusionTailChars..];
        }

        text = text.Trim();
        if (text.Length == 0) { reason = "empty_conclusion"; return false; }

        var last = -1;
        var pick = '\0';
        foreach (System.Text.RegularExpressions.Match m in
                 System.Text.RegularExpressions.Regex.Matches(text, @"(?<![A-Za-z])([CcAaNn])(?![A-Za-z])"))
        {
            last = m.Index;
            pick = char.ToUpperInvariant(m.Groups[1].Value[0]);
        }
        foreach (var (word, letterChar) in ConclusionWords)
        {
            var k = text.LastIndexOf(word, StringComparison.Ordinal);
            if (k > last) { last = k; pick = letterChar; }
        }
        if (last < 0) { reason = "no_marker"; return false; }
        letter = pick.ToString();
        reason = "ok";
        return true;
    }
}
