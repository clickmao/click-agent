using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using System.Threading;
using agent.nlp;

namespace agent.modelqueue;

/// <summary>
/// R498 候选③ (R413 主线补口): **内容承载的本地生成通道**。
///
/// 问题 (R497 遗留, 逐字): 「本地消化通道只有回放/模板, **无内容承载的本地生成** ⇒ 同义改写族
/// 吸收即触发 R413 退化 (登记设计, 不落死代码)」。
///   - 回放 (R465/R475): 只对上一条**实质答复**原样重来, 零信息加工 ⇒ 对「换个说法」无能为力
///     (用户要的是**改写**, 回放原文 = 答非所问)。
///   - 模板 (R489): 纯确认语, 不含内容 ⇒ 用模板冒充改写答复 = R486 类冒充面破口。
///   - 远端: 「换个说法」不含 新诉求/疑问/纠正 机械信号, 也不属复述族 ⇒ 落在残余带里,
///     要么被 r1 误判 Skip (R434 已证 3/4 真诉求被跳空), 要么走远端 (本可零远端)。
///
/// 本类提供**内容承载**的本地生成所缺的两件东西 (本地生成本身走 llama.cpp 长驻端口 = r1):
///   ① <see cref="IsPureParaphrase"/> —— 「同义改写族」的结构判据 (纯函数, 不依赖端口/网络);
///   ② <see cref="Guard"/>        —— 对本地生成结果的**机检守卫** (改写不得改事实)。
///
/// 为什么必须有守卫 (而不是信任小模型的输出): R488 真机实测给出的教训是「本地生成会凭空加内容」
/// (幻觉/复读/反问三连)。改写轮**没有新信息可加**, 唯一的失败方式就是**改动既有事实** ⇒ 守卫把
/// 「事实守恒」做成逐条可机检的不变量, 任何一条破了就**拒收并降级远端** (fail-closed: 最坏等于现状)。
///
/// 开关: <see cref="EnvName"/> == "1" 才启用 (默认**关**)。默认关 = 生产行为逐位不变,
/// 本轮的该通道只以「同网格单变量消融臂」形态存在。
/// </summary>
public static class LocalParaphraseChannel
{
    /// <summary>闸开关 (默认关: 未设/非 "1" ⇒ 不启用)。</summary>
    public const string EnvName = "AGENTFRAMEWORK_LOCAL_PARAPHRASE";

    /// <summary>是否启用 (默认关)。</summary>
    public static bool IsEnabled()
        => IsEnabledValue(Environment.GetEnvironmentVariable(EnvName));

    /// <summary>
    /// 闸口径的**纯函数**形态 (可机检, 不碰环境变量): 只有字面 "1" 算开。
    /// 「未设 / 0 / true / TRUE / 1 (带空格)」一律算关 —— 口径从严, 避免「以为开了」。
    /// </summary>
    public static bool IsEnabledValue(string? raw) => string.Equals(raw, "1", StringComparison.Ordinal);

    /// <summary>
    /// 吸收判定的**单源**组合 (闸 ∧ 判据) —— 接线处与测试读同一个函数。
    /// 否则「闸关了不会吸收」只是接线处的口头承诺, 不可机检。
    /// </summary>
    public static bool ShouldAbsorb(string? userMessage, bool enabled)
        => ShouldAbsorb(userMessage, enabled, null);

    /// <summary>带补丁集合的纯函数形态 (机检/差分器具注入; 空 ⇒ 读回补库)。</summary>
    public static bool ShouldAbsorb(string? userMessage, bool enabled, IReadOnlyCollection<string>? patches)
        => enabled && IsPureParaphrase(userMessage, patches);

    // ─────────────────────────────────────────────────────────────────────────
    // ① 族判据: 「同义改写族」= 只要求把上一条答复**换一种表达**, 不含新诉求
    // ─────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// 改写族白名单字符集 (改写标记 + 指代词的全部用字)。任何集合外字符 ⇒ 不是纯改写。
    /// 纪律 (承 R465): 白名单**只含表达方式用字**, 不含任何内容字 ⇒ 内容字一律落到远端。
    /// 注: 与 <see cref="TurnGateJudge"/> 的复述族字符集存在字面重叠 (说/讲/一/遍/来) —
    /// 两族的**区分靠回补面 + 互斥判据**, 不靠字符集互斥 (见 <see cref="IsPureParaphrase"/> 内注释)。
    /// </summary>
    private const string FamilyChars = "换个种法说讲表述措辞方式别另其不同把这一遍句话来用写的给我吧下了呢啊呀哦重新";

    /// <summary>
    /// R498: 「同义改写族」结构确认 —— 用户只要求把上一条答复**换一种说法**重新表述。
    /// 机械判据 (全过才算 true):
    ///   ① 归一化 (去标点/空白/符号) 后长度 ≤16 ⇒ 长句必然携带新信息, 不吸收;
    ///   ② 无问号 ⇒ 疑问句永远走远端;
    ///   ③ 每字符都属 <see cref="FamilyChars"/> ⇒ 任何内容字/数字/ASCII 字母立即 false;
    ///   ④ 归一化串**命中回补库** (R575: 由 LLM 成功轮回补, 零词表; 表外 ⇒ 交远端);
    ///   ⑤ **与复述族互斥** —— <see cref="TurnGateJudge.IsPureRepeat"/> 为真 ⇒ 本判 false。
    ///      (两族语义不同: 复述 = 原样重来, 改写 = 换表达。互斥由**判据**保证, 不依赖字符集巧合;
    ///       调用方也以「复述判据在前」保证优先级, 本条件是双保险; 补丁按面隔离 ⇒ 同一形状不会两面同真。)
    /// 用途限制: 本判只允许**前置门直接 Skip**, 且本地消化必须是**受 <see cref="Guard"/> 约束的本地生成**;
    /// 调用方必须让 <see cref="TurnGateJudge.MechanicalPass"/> 优先于本判 (新诉求/疑问/长文本永不被吸收)。
    /// </summary>
    public static bool IsPureParaphrase(string? userMessage) => IsPureParaphrase(userMessage, null);

    /// <inheritdoc cref="IsPureParaphrase(string?)"/>
    /// <param name="patches">机检/差分器具注入的补丁集合 (空 ⇒ 读回补库)。</param>
    public static bool IsPureParaphrase(string? userMessage, IReadOnlyCollection<string>? patches)
    {
        var m = (userMessage ?? string.Empty).Trim();
        return IsParaphraseShape(userMessage)
               && !TurnGateJudge.IsPureRepeat(m, patches)                                   // ⑤ 族互斥
               && (NlpGate.IsPatched(m, NlpGate.FaceParaphrase, patches)                    // ④ 逐字补丁 (历史库, 只读)
                   || NlpGate.IsLearned(m, NlpGate.FaceParaphrase, patches == null));       // ④' 形状通道 (实库模式)
    }

    /// <summary>
    /// 结构面 (与回补无关): 长度 ≤32 ∧ 去标点后 ≤16 字且**每字符都属改写白名单** ∧ 无问号。
    /// 回补面只能在**族内**加强 (与复述族同形; R575 回补点按本判决定登记哪一面)。
    /// </summary>
    public static bool IsParaphraseShape(string? userMessage)
    {
        var m = (userMessage ?? string.Empty).Trim();
        if (m.Length == 0 || m.Length > 32) return false;
        var sb = new StringBuilder(m.Length);
        foreach (var ch in m)
        {
            if (ch is '?' or '？') return false;                                    // ② 疑问句永不吸收
            if (char.IsPunctuation(ch) || char.IsWhiteSpace(ch) || char.IsSymbol(ch)) continue;
            sb.Append(ch);
        }
        var n = sb.ToString();
        if (n.Length is 0 or > 16) return false;                                    // ① 有界
        foreach (var ch in n)                                                        // ③ 白名单字符集
            if (FamilyChars.IndexOf(ch) < 0) return false;
        return true;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // ② 生成提示 (规格化: 只吃「上一条答复」一段文本, 不灌 role/成长全文 — R413 铁律)
    // ─────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// 本地改写提示。纪律 (R413 实测铁律): 判别/生成提示必须**规格化且短** —— 灌 role 全文或成长
    /// 全文会挤爆生成预算, 真机表现为输出截断在思考链中途 (无闭合标记) ⇒ 恒降级。本提示只含
    /// **原文 + 硬性约束**, 长度 = 原文长度 + 常量。
    /// </summary>
    public static string BuildPrompt(string sourceReply)
    {
        var src = (sourceReply ?? string.Empty).Trim();
        var sb = new StringBuilder(src.Length + 512);
        sb.Append("任务: 把【原文】换一种说法重新表述一遍。\n");
        sb.Append("硬性约束 (违反任何一条即失败):\n");
        sb.Append("1. 原文里的数字、文件名、命令、标识符必须逐字原样保留, 不得改写、不得遗漏、不得新增。\n");
        sb.Append("2. 不得新增原文没有的动作声明 (例如「已完成」「已部署」「已运行」)。\n");
        sb.Append("3. 只改变表达方式, 不得新增任何事实, 不得删减原文的信息。\n");
        sb.Append("4. 不得反问、不得提问, 输出中不得出现问号。\n");
        sb.Append("5. 只输出改写后的正文 (长度约为原文的 0.5~2 倍), 不要任何前后说明。\n");
        sb.Append("【原文】\n").Append(src).Append('\n');
        sb.Append("【改写】\n");
        return sb.ToString();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // ③ 机检守卫: 改写不得改事实 (fail-closed: 破一条即拒 ⇒ 调用方降级远端)
    // ─────────────────────────────────────────────────────────────────────────

    /// <summary>守卫结论。Reason 恒非空 (可落遥测归因)。</summary>
    public readonly record struct ParaphraseVerdict(bool Ok, string Reason);

    /// <summary>通过。</summary>
    public static readonly ParaphraseVerdict Pass = new(true, "ok");

    /// <summary>拒收 (需降级远端)。</summary>
    public static ParaphraseVerdict Reject(string reason) => new(false, reason);

    /// <summary>长度带下限 (输出/原文)。低于 ⇒ 信息被删减。</summary>
    public const double MinLengthRatio = 0.4;

    /// <summary>长度带上限。高于 ⇒ 输出膨胀 (新增内容的典型征兆)。</summary>
    public const double MaxLengthRatio = 2.5;

    /// <summary>
    /// 动作声明面 (R575): 原为 19 条中文/英文声明词的**静态表**, 词表删除后改由**回补库**承担
    /// (`NlpGate` 的 `claim` 面, 按 token 学习): 输出里出现「回补为动作声明的 token」且原文没有 ⇒ 拒。
    /// 零词表 = 无开发期预制规则; 无补丁 ⇒ 本面不覆盖 (诚实边界: 该面只由回补驱动, 见报告)。
    /// 扫描窗口 (输出侧 token 数上限)。
    /// </summary>
    private const int ClaimTokenScan = 64;

    /// <summary>
    /// R498 改写守卫 (纯函数, 可机检)。逐条穷举 (R503 修归因: **破几条报几条**, 语义不变 —— 任一条破即拒):
    ///   ① 原文非空 ∧ 输出非空 (空输出 ⇒ 拒, 不得当成功 — R411 口径);
    ///   ② 输出无问号 —— 本地轮不得反问 (R488 实测退化: r1 把「测试命令是什么？」当改写输出);
    ///   ③ 输出无思考链/代码围栏泄漏 —— r1 会把推理写进 content (R413 实测, 直接回显 = 泄漏推理);
    ///   ④ **标识符守恒**: 原文里的标识符必须逐个出现在输出中 (大小写不敏感), 少一个即拒;
    ///   ⑤ **标识符禁增**: 输出里的标识符必须都来自原文, 多一个即拒 (凭空造出 = 幻觉);
    ///   ⑥ **动作声明禁增**: 原文没有的动作声明词出现在输出里即拒 (词面 = 回补库 `claim` 面, 零静态表);
    ///   ⑦ **长度带** [0.4, 2.5]。
    /// 诚实边界 (写进报告, 不冒充「语义等价已证明」): 本守卫检的是**结构不变量** (标识符/声明词/长度),
    /// 不是语义等价 —— 语义改写正确性**未被本守卫覆盖**, 只由「同网格人工质量细读」取证。
    /// </summary>
    public static ParaphraseVerdict Guard(string? sourceReply, string? output) => Guard(sourceReply, output, null);

    /// <inheritdoc cref="Guard(string?, string?)"/>
    /// <param name="claimPatches">⑥ 的动作声明词面补丁集合 (空 ⇒ 读回补库; 机检/差分器具注入用)。</param>
    public static ParaphraseVerdict Guard(string? sourceReply, string? output, IReadOnlyCollection<string>? claimPatches)
    {
        var src = (sourceReply ?? string.Empty).Trim();
        if (src.Length == 0) return Reject("source_empty");                          // ① 前置: 原文空 ⇒ 余下各条均不可判
        var text = (output ?? string.Empty).Trim();
        if (text.Length == 0) return Reject("empty_output");                         // ① 前置: 输出空 ⇒ 标识符/长度检查只会产生噪声

        // R503 归因完整性: ②..⑦ **逐条穷举**, 破几条报几条 (拒绝语义与逐条短路版逐位等价 —— 任一条破即拒)。
        // 动机 (R501 t8 实证): 旧版先破先报, 遥测只留 `question_mark`; 而该轮本地输出 msg_len=5 / src_len=612
        // (比值 0.008), 同时破了 ⑦ 长度带 —— 单条归因会把「引擎根本没改写」误读成「守卫禁止问号过于严格」,
        // 进而诱导**削弱一条正确判据**。归因不全 = 归因错。
        var faults = new List<string>(3);
        if (text.IndexOf('?') >= 0 || text.IndexOf('？') >= 0) faults.Add("question_mark");  // ②
        if (text.Contains("```", StringComparison.Ordinal)                            // ③
            || text.Contains(TurnGateJudge.ThinkOpen, StringComparison.Ordinal)
            || text.Contains(TurnGateJudge.ThinkClose, StringComparison.Ordinal)
            || text.Contains("思考", StringComparison.Ordinal)
            || text.Contains("推理过程", StringComparison.Ordinal))
            faults.Add("think_leak");

        var srcIds = new HashSet<string>(Identifiers(src), StringComparer.OrdinalIgnoreCase);
        var lost = new List<string>();                                               // ④ 守恒
        foreach (var tok in srcIds)
            if (text.IndexOf(tok, StringComparison.OrdinalIgnoreCase) < 0)
                lost.Add(tok);
        if (lost.Count > 0) faults.Add("identifier_lost:" + JoinBounded(lost));

        var added = new List<string>();                                              // ⑤ 禁增
        foreach (var tok in Identifiers(text))
            if (!srcIds.Contains(tok))
                added.Add(tok);
        if (added.Count > 0) faults.Add("identifier_added:" + JoinBounded(added));

        var claims = new List<string>();                                             // ⑥ 动作声明禁增 (回补面)
        foreach (var token in TextSignal.KeyTokens(text, ClaimTokenScan))
            if (NlpGate.IsPatched(token, NlpGate.FaceClaim, claimPatches) && !src.Contains(token, StringComparison.Ordinal))
                claims.Add(token);
        if (claims.Count > 0) faults.Add("claim_added:" + JoinBounded(claims));

        var ratio = (double)text.Length / src.Length;                                // ⑦ 长度带
        if (ratio < MinLengthRatio || ratio > MaxLengthRatio)
            faults.Add("length_band:" + ratio.ToString("F2", CultureInfo.InvariantCulture));

        return faults.Count == 0 ? Pass : Reject(string.Join("+", faults));
    }

    /// <summary>
    /// 归因明细的**有界连接**: 最多列 2 个词元, 余者以 `+N` 摘要 (遥测行不得被单条判据撑爆;
    /// 名字面上仍守恒 —— 数目不丢, 明细有界)。空列表不发生 (调用方只在 Count&gt;0 时调用)。
    /// </summary>
    internal static string JoinBounded(IReadOnlyList<string> items)
        => items.Count <= 2 ? string.Join(",", items)
                            : items[0] + "," + items[1] + "+" + (items.Count - 2).ToString(CultureInfo.InvariantCulture);

    /// <summary>
    /// 标识符抽取 (语言无关: 只按字符类判定, 无后缀/关键词表 — 承 R447 语言无关令)。
    /// 词元 = 极大的 ASCII 字母数字串; 保留条件 = 「长度 ≥4」或「长度 ≥2 且含数字」。
    /// 例: LCM-8a88a4729346 → "LCM"(3,无数字,弃) + "8a88a4729346"(保留); ISO-8859-1 → "8859"(保留);
    ///     r1/3B/512 → 保留; 中文相邻字不进入词元 (非 ASCII)。
    /// 诚实边界: 长度 2 且不含数字的短词元 (如 "ok") 不在守恒面内。
    /// </summary>
    public static IEnumerable<string> Identifiers(string? s)
    {
        if (string.IsNullOrEmpty(s)) yield break;
        var sb = new StringBuilder(16);
        var allDigits = true;
        var hasDigit = false;
        for (var i = 0; i <= s!.Length; i++)
        {
            var ch = i < s.Length ? s[i] : '\0';
            var isWordChar = i < s.Length && ch < 128 && char.IsLetterOrDigit(ch);
            if (isWordChar)
            {
                sb.Append(ch);
                if (char.IsDigit(ch)) hasDigit = true; else allDigits = false;
                continue;
            }
            if (sb.Length >= 4 || (sb.Length >= 2 && hasDigit))
                yield return sb.ToString();
            sb.Clear();
            allDigits = true;
            hasDigit = false;
        }
        _ = allDigits;
    }
}
