using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;

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
    ///   ① 归一化后的形状必须**命中回补库** (R575: 由 LLM 成功轮回补, 零词表; 表外 ⇒ 交远端);
    ///      结构面 (字符白名单/长度/无问号) 先于回补面 ⇒ 含内容字的形状永不被吸收。
    ///   ② 归一化后长度 ≤14 且**每个字符都属复述白名单字符集** ⇒ 任何内容字 (细/换/法/增加/命令...) 立即 false。
    ///   ③ 无问号 ⇒ 疑问句永远走远端。
    /// 用途限制: 本判只允许**前置门直接 Skip** (本地消化 = 回放上一条答复原文, 零远端调用);
    /// 调用方必须让 <see cref="MechanicalPass"/> 优先于本判 (新诉求/疑问/长文本永不被吸收)。
    /// </summary>
    public static bool IsPureRepeat(string? userMessage) => IsPureRepeat(userMessage, null);

    /// <summary>
    /// R575 回补面 (既有机制 `agent.nlp.NlpGate` 接线, 零词表): 结构面通过 ∧ 该形状已被 LLM 成功轮
    /// 回补过 (签名入库) ⇒ 判为纯复述 ⇒ 本地回放上一条答复 (零远端调用)。
    /// 白名单字符集 (②) 仍在 ⇒ 回补**不能**把含内容字的形状吃进来 (R434 硬线保持:
    /// 「重做一遍」即便被误回补也仍为 false)。<paramref name="patches"/> = 机检/差分器具注入的补丁集合
    /// (空 ⇒ 读回补库); 无补丁 ⇒ 一律交远端 (安全方向不变)。
    /// </summary>
    public static bool IsPureRepeat(string? userMessage, IReadOnlyCollection<string>? patches)
    {
        var m = (userMessage ?? string.Empty).Trim();
        return IsRepeatShape(userMessage)
               && (agent.nlp.NlpGate.IsPatched(m, agent.nlp.NlpGate.FaceRepeat, patches)      // ① 逐字补丁 (历史库, 只读)
                   || agent.nlp.NlpGate.IsLearned(m, agent.nlp.NlpGate.FaceRepeat, patches == null));  // ①' 形状通道 (实库模式)
    }

    /// <summary>
    /// 结构面 (与回补无关): 长度 ≤24 ∧ 去标点后 ≤14 字且**每字符都属复述白名单** ∧ 无问号。
    /// 回补面只能在**族内**加强 (「谁属于复述族」由回补决定, 「能不能吸收」仍由本判决定)。
    /// </summary>
    public static bool IsRepeatShape(string? userMessage)
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
        return true;
    }

    /// <summary>
    /// R575 回补点 (W2 — 「LLM 返回后回补闸数据」的唯一写入点): 远端轮**成功**后由链侧调用,
    /// 按输入所属**结构面**登记回补签名 ⇒ 下次同形状输入可在本地面成立 (使用中自动升级)。
    /// 族外输入 (含内容字/问号/数字/长文) 一律不登记 ⇒ 回补不会把内容诉求吃进本地面。
    /// </summary>
    public static void LearnOnSuccess(string? userMessage, bool success)
    {
        if (!success) return;
        var m = (userMessage ?? string.Empty).Trim();
        if (m.Length == 0) return;
        // RF0002 §2.1 (用户令 2026-09-19「不补回」): 写入通道由**逐字补丁**换成**形状** ——
        // 学到的是能力 (面/长度带/字符集), 同面不同措辞的下一句也能本地命中; 逐字字符串不再写库。
        if (IsRepeatShape(m))
        {
            agent.nlp.NlpGate.LearnFromRemote(m, agent.nlp.NlpGate.FaceRepeat, localizable: true);
            return;
        }
        if (LocalParaphraseChannel.IsParaphraseShape(m))
            agent.nlp.NlpGate.LearnFromRemote(m, agent.nlp.NlpGate.FaceParaphrase, localizable: true);
    }

    /// <summary>R465: 复述族白名单字符集 (复述标记 + 指代词的全部用字; 任何集合外字符 ⇒ 不是纯复述)。
    /// R575: 吸收面由**回补库**承担 (零标记表) —— 字符集是**结构护栏**, 顺序上先于回补判定。</summary>
    private const string RepeatFamilyChars = "再讲遍次重复述从头说要你上面那条这句话的来回新下念看给把一吧哦嗯啊呀啦哇";

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
        // R575 (零词表): 结论区只认**字母标记** S/P (前后不得是字母, 防 "Send"/"Python" 误命中);
        // 中文/英文词面标记不再作判 ⇒ 模型答词面时落 no_marker 交远端 (fail-safe, 不猜)。
        foreach (System.Text.RegularExpressions.Match m in
                 System.Text.RegularExpressions.Regex.Matches(conclusion, @"(?<![A-Za-z])([SsPp])(?![A-Za-z])"))
        {
            Note(m.Groups[1].Value == "S" || m.Groups[1].Value == "s", m.Index);
        }
        if (lastSkip < 0 && lastPass < 0) return TurnGateOutcome.Undecided("no_marker", text);
        return TurnGateOutcome.Decide(lastSkip > lastPass ? TurnGateVerdict.Skip : TurnGateVerdict.Pass, text);
    }

    /// <summary>
    /// R413 机械前置门 (零 token, 确定性): 只要消息里有任何「必须走远端」的**结构信号** ⇒
    /// 直接 Pass, **根本不问 r1**。目的 = 把假阴性 (新诉求/纠正被误跳) 结构性消掉,
    /// 而不是靠小模型判对。R575: 信号面 = 问号 / 代码或路径符 / 数字 / 长度 ≥ 阈值 (零词表);
    /// 词面信号 (疑问词/请求词/纠正词) 已删 —— 无结构信号的短消息交 r1, 且 r1 判 Skip 时还要过
    /// 认可族结构确认 (见链侧后置否决) ⇒ 真诉求不被跳成空话。
    /// </summary>
    public static bool MechanicalPass(string? userMessage)
    {
        if (string.IsNullOrWhiteSpace(userMessage)) return true;      // 说不清 ⇒ 保守走远端
        var m = userMessage.Trim();
        foreach (var ch in "?？")
            if (m.Contains(ch)) return true;
        foreach (var ch in "`/\\")
            if (m.Contains(ch)) return true;
        for (var i = 0; i < m.Length; i++)
            if (char.IsDigit(m[i])) return true;                       // 数字 ⇒ 可能带参数 (保守)
        return m.Length >= SubstantiveLengthThreshold;                 // 长消息 ⇒ 大概率有实质内容 (保守)
    }

    /// <summary>长度阈值: ≥ 该长度视为有实质内容 (保守走远端; 宁可少省, 不可误跳)。</summary>
    private const int SubstantiveLengthThreshold = 24;

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
