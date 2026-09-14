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

    private long _cachePinned;
    private int _lastCachedTokens;

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

    public string? LastBasis { get; private set; }

    /// <summary>R430: 最近一次门判的 prompt 指纹 (空 = 后端未上报)。</summary>
    public string? LastPromptSha { get; private set; }

    /// <summary>R430: 最近一次门判的请求体指纹。</summary>
    public string? LastRequestSha { get; private set; }

    /// <summary>R430: 最近一次门判的请求关键字段摘要。</summary>
    public string? LastRequestFields { get; private set; }

    /// <summary>R430: 上一次门判实际使用的角色种子指纹 (分辨「种子漂移」与「引擎不确定」)。</summary>
    public string? LastRoleSeedSha { get; private set; }

    /// <summary>机械前置门命中 (零 token 直接 Pass, 未询问 r1) — 必须可观测, 否则看不出"省了判别"。</summary>
    public void RecordMechanicalPass() { Interlocked.Increment(ref _mechanicalPasses); LastBasis = "mechanical:pass→remote"; }

    /// <summary>被跳过轮使用非 LLM 模板回复 (真机实证: LLM 生成会复读/反问)。</summary>
    public void RecordTemplateAck() { Interlocked.Increment(ref _templateAcks); }

    public void RecordJudged() => Interlocked.Increment(ref _judged);
    public void RecordSkipped() { Interlocked.Increment(ref _skipped); LastBasis = "gate:skip→local"; }
    public void RecordPassed() { Interlocked.Increment(ref _passed); LastBasis = "gate:pass→remote"; }

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

    /// <summary>R429: 门判请求已钉死缓存态 (显式关前缀缓存 + 记录本次 cache_n)。</summary>
    public void RecordCachePinned(int cachedTokens, string? promptSha = null, string? requestSha = null, string? requestFields = null)
    {
        Interlocked.Increment(ref _cachePinned);
        Volatile.Write(ref _lastCachedTokens, cachedTokens);
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
public sealed record RelationJudgeOutcome(string Letter, string Raw, int CompletionTokens);

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
    /// <summary>规范化: 成功 → <c>true</c> 且 <paramref name="letter"/> ∈ {C,A,N}。</summary>
    public static bool TryNormalize(string? raw, out string letter)
    {
        letter = string.Empty;
        if (string.IsNullOrWhiteSpace(raw)) return false;
        var text = raw.Trim();

        var close = text.LastIndexOf(TurnGateJudge.ThinkClose, StringComparison.Ordinal);
        if (close >= 0)
        {
            text = text[(close + TurnGateJudge.ThinkClose.Length)..];
        }
        else if (text.LastIndexOf(TurnGateJudge.ThinkOpen, StringComparison.Ordinal) >= 0)
        {
            return false;   // thinking_truncated: 结论还没写出来
        }

        text = text.Trim();
        if (text.Length == 0) return false;

        var last = -1;
        var pick = '\0';
        foreach (System.Text.RegularExpressions.Match m in
                 System.Text.RegularExpressions.Regex.Matches(text, @"(?<![A-Za-z])([CcAaNn])(?![A-Za-z])"))
        {
            last = m.Index;
            pick = char.ToUpperInvariant(m.Groups[1].Value[0]);
        }
        if (last < 0) return false;
        letter = pick.ToString();
        return true;
    }
}
