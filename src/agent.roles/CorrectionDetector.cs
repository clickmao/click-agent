using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.roles;

/// <summary>
/// R360 (v0.21.0 修订版, 用户钦定): 用户纠正检测器 — Role 成长赏罚链的信号源。
/// 判定: 用户新消息相对上一轮 Role 输出, 是否为「纠正/否定/修正」。
/// 两级判定 (token 经济优先, 用户钦定 "用LLM需注意tokens使用量"):
///   L1 规则层 (0 token): 高信纠正模式 (否定词+指代/直接改写) — 命中即判罚, 不调 LLM;
///      高信采纳模式 (新话题/肯定词) — 命中即判赏。
///   L2 LLM 层 (~120 tokens/次, 仅 L1 模糊时触发): 微 prompt 三分类 CORRECTION/ADOPT/NEUTRAL。
/// 输出: CorrectionVerdict { Kind, Confidence, Signal, Source(rule|llm), TokensUsed }。
/// 约束: 绝不抛异常 (判定失败=NEUTRAL, 不阻断主链); 零反射 (source-gen)。
/// </summary>
public static class CorrectionDetector
{
    public sealed record CorrectionVerdict
    {
        public CorrectionKind Kind { get; init; }
        public double Confidence { get; init; }
        public string Signal { get; init; } = string.Empty;
        public string Source { get; init; } = "rule";
        public int TokensUsed { get; init; }
    }

    public enum CorrectionKind { Neutral = 0, Adopt = 1, Correct = 2 }

    // ── L1 规则词面 — 已按用户令全部移除 (2026-09-19 中文词表清零) ──
    // 判罚/采纳不再有词表捷径: RuleJudge 一律返回 null ⇒ 交 L2 字母判官 (C/A/N, 现有机制)。
    // 保留这三个空数组仅为签名兼容 (RuleJudge 的遍历与豁免前置循环仍在, 空表即恒不命中)。
    private static readonly string[] CorrectMarkers =
    [];
    private static readonly string[] AdoptMarkers =
    [];

    // R361 语境豁免 — 随词表一并移除 (无词面判罚 ⇒ 无需豁免表; 语境判断交 L2)
    private static readonly string[] ContextExemptions =
    [];

    /// <summary>L1 规则判定。返回 null = 模糊 (需 L2)。</summary>
    public static CorrectionVerdict? RuleJudge(string userMessage, string previousReply)
    {
        var msg = (userMessage ?? "").Trim();
        if (msg.Length == 0) return new CorrectionVerdict { Kind = CorrectionKind.Neutral, Confidence = 0.5, Signal = "empty" };

        var lower = msg.ToLowerInvariant();

        // 语境豁免前置: 豁免词命中 → 直接进 L2 (规则不可靠, 让 LLM 语境判)
        foreach (var ex in ContextExemptions)
            if (lower.Contains(ex))
                return null;

        // 判罚/采纳一律交 L2 字母判官 (C/A/N — 现有机制); 无词表 ⇒ L1 不凭词面猜。
        // (原「强纠正: 纠正词 + 指代词/短消息」与「强采纳: 肯定词 + 短消息」两段已按用户令删除:
        //  词面对其它语言/新梗必然漏判, 且短否定/肯定词在转述与假设语境下误杀 — R361 三例实证。)
        return null; // 一律模糊 → L2 判官
    }

    /// <summary>
    /// R435: J 判官 prompt **单一构造点**（本地与远端由同一函数产出 ⇒ 结构上不可能两套提示；
    /// R365/R426 约束）。原尾行是裸片段「只输出一个字母。」⇒ 真机实测（R435 raw 取证, eval/rover/r435/probe-j1-raw.json）
    /// r1 在 7 条实发 prompt 里 **3 条把该片段逐字回声**成「答案」（`只输出一个字母。`），
    /// 结论区不含任何字母 ⇒ 解析失败 ⇒ 每次多打一次**纯多余**的远端请求。
    /// 故改用**前置门已验证的形状**（TurnGateJudge.BuildPrompt）：示例 + 「思考结束后另起一行只写一个字母」+ 以「答案:」收尾。
    /// 语义面不变（仍是 C/A/N 同一分类），无法确定时取 **N=Neutral**（不罚不赏, 不误赏误罚）。
    /// R446: 判官 prompt 形态开关 (默认关; =1 ⇒ 紧凑变体, 见 BuildJudgePromptCompact)。
    /// </summary>
    private static readonly bool JudgePromptCompact =
        Environment.GetEnvironmentVariable("AGENTFRAMEWORK_JUDGE_PROMPT_COMPACT") is "1" or "true";

    /// <summary>R446: 单一构造点按开关分派 (本地/远端同面)。</summary>
    public static string BuildJudgePrompt(string? userMessage, string? previousReply)
        => JudgePromptCompact
            ? BuildJudgePromptCompact(userMessage, previousReply)
            : BuildJudgePromptVerbose(userMessage, previousReply);

    /// <summary>R446: 紧凑变体 (去 4 行示例; 截断口径与 verbose 逐字一致)。</summary>
    public static string BuildJudgePromptCompact(string? userMessage, string? previousReply)
    {
        var cu = Truncate(userMessage ?? "", 120);
        var cp = Truncate(previousReply ?? "", 160);
        return
            "判定用户消息相对上一轮回答: C=纠正/否定上一轮, A=认可/确认/致谢(无新要求), N=新要求或换说法。\n" +
            "先思考, 思考结束后必须另起一行只写一个字母 (C 或 A 或 N), 不要写其他内容。\n" +
            "无法确定时也必须写 N。\n" +
            $"上一轮: {cp}\n用户: {cu}\n" +
            "答案:\n";
    }

    /// <summary>R446: 原 verbose 变体 (逐字未改)。</summary>
    private static string BuildJudgePromptVerbose(string? userMessage, string? previousReply)
    {
        var user = Truncate(userMessage ?? "", 120);
        var prev = Truncate(previousReply ?? "", 160);
        return
            "判定用户消息相对上一轮回答: 纠正否定上一轮=C, 认可采纳=A, 新话题无关=N。\n" +
            "- C = 指出上一轮错了/不对/不准确, 要求改 (如: 好像不太对。)。\n" +
            "- A = 只是认可/确认/致谢, 没有提出任何新要求 (如: 嗯，知道了。 / 好，就这样。)。\n" +
            "- N = 提出新要求, 或要求重复/细化/换说法, 既没认可也没纠正 (如: 详细说说。 / 换一种说法。)。\n" +
            "先思考, 思考结束后必须另起一行只写一个字母 (C 或 A 或 N), 不要写其他内容。\n" +
            "无法确定时也必须写 N。\n" +
            $"上一轮: {prev}\n用户: {user}\n" +
            "答案:\n";
    }

    /// <summary>
    /// L2 微 prompt 判定 (仅 L1 模糊时; ~120 tokens)。llmCaller: (prompt, maxTokens) → (content, tokensUsed)。
    /// LLM 不可用/超时 → NEUTRAL (不罚不赏, 诚实语义)。
    /// </summary>
    public static async Task<CorrectionVerdict> JudgeAsync(
        string userMessage,
        string previousReply,
        Func<string, int, Task<(string Content, int TokensUsed)>> llmCaller,
        CancellationToken ct = default)
    {
        var rule = RuleJudge(userMessage, previousReply);
        if (rule is not null) return rule;

        // R435: 关系判官定义 = 「用户消息 **相对上一轮回答**」的判定 ⇒ 无上一轮时 C/A/N 无定义。
        // 结构性 Neutral (确定性, 不调任何模型): 真机取证 turn1 (prev 空) 本地模型把任务理解成
        // 「给上一轮挑一个字母」⇒ 结论区输出 `\n\nbuild`, 必失败同时白烧一次远端调用。
        // 证据: eval/rover/r435/probe-j2-classified.json → A0/turn1 (tail='\n\nbuild'), 7/7 臂全一致。
        if (string.IsNullOrWhiteSpace(previousReply))
            return new CorrectionVerdict { Kind = CorrectionKind.Neutral, Confidence = 0.9, Signal = "no_prev_reply", Source = "rule", TokensUsed = 0 };

        // R435: prompt 由单一构造点产出 (本地/远端同面); 双方各截断 (用户 120 字 / 上一轮 160 字)
        var prompt = BuildJudgePrompt(userMessage, previousReply);

        string content;
        int tokens;
        try
        {
            (content, tokens) = await llmCaller(prompt, 64).ConfigureAwait(false);
            var wordTry = (content ?? "").Trim().ToUpperInvariant();
            // reasoning 模型思维链可能吃光预算 → 空 content 翻倍重试一次 (R361 对抗实证)
            if (wordTry.Length == 0)
            {
                var (content2, tokens2) = await llmCaller(prompt, 128).ConfigureAwait(false);
                content = content2;
                tokens += tokens2;
            }
        }
        catch
        {
            // LLM 不可用 → NEUTRAL 不罚不赏 (诚实语义, 不阻断主链)
            return new CorrectionVerdict { Kind = CorrectionKind.Neutral, Confidence = 0.5, Signal = "llm_error", Source = "llm", TokensUsed = 0 };
        }
        var word = (content ?? "").Trim().ToUpperInvariant();

        return word switch
        {
            var w when w.StartsWith("C") || w.Contains("CORRECT") => new CorrectionVerdict
                { Kind = CorrectionKind.Correct, Confidence = 0.8, Signal = "llm", Source = "llm", TokensUsed = tokens },
            var w when w.StartsWith("A") || w.Contains("ADOPT") => new CorrectionVerdict
                { Kind = CorrectionKind.Adopt, Confidence = 0.8, Signal = "llm", Source = "llm", TokensUsed = tokens },
            _ => new CorrectionVerdict
                { Kind = CorrectionKind.Neutral, Confidence = 0.6, Signal = "llm:" + Truncate(content ?? "?", 12), Source = "llm", TokensUsed = tokens },
        };
    }

    private static string Truncate(string s, int max) =>
        s.Length <= max ? s : s[..max];
}
