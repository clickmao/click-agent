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

    // ── L1 规则词面 (中文为主; 命中强模式即结算) ──
    private static readonly string[] CorrectMarkers =
    {
        "不对", "错了", "不是这样", "你说错", "理解错了", "搞错了", "不对吧",
        "重新", "应该是", "我说的是", "你理解成", "纠正", "不是这个意思",
        "wrong", "incorrect", "no,", "not what i meant", "you misunderstood",
    };
    private static readonly string[] AdoptMarkers =
    {
        "好的", "明白了", "懂了", "收到", "谢谢", "没错", "对", "正是",
        "thanks", "got it", "correct", "exactly",
    };

    // R361 对抗修正: 语境豁免 — 否定词出现在转述他人/假设/历史语境时不判罚 (L1 误杀 3 例实证)
    private static readonly string[] ContextExemptions =
    {
        "同事说", "别人说", "他们说", "据说",        // 转述他人
        "如果我说错", "如果我理解", "假如",          // 假设句
        "上次", "之前那个", "历史", "昨天",          // 历史对照
    };

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

        // 强纠正: 纠正词 + (指代词 或 短消息 — 短否定几乎必然针对上一轮)
        foreach (var m in CorrectMarkers)
        {
            if (!lower.Contains(m)) continue;
            var isEnglishMarker = m.All(c => c < 0x80); // 英文标记自带指代 ("not what i meant" 必指上一轮)
            var referential = isEnglishMarker || ContainsReference(lower) || msg.Length <= 24;
            if (referential)
                return new CorrectionVerdict { Kind = CorrectionKind.Correct, Confidence = 0.9, Signal = $"marker:{m}" };
        }

        // 强采纳: 肯定词 + 短消息 (长消息即使含"对"也可能是新话题的转折, 不判)
        foreach (var m in AdoptMarkers)
        {
            if (!lower.Contains(m)) continue;
            if (msg.Length <= 16)
                return new CorrectionVerdict { Kind = CorrectionKind.Adopt, Confidence = 0.85, Signal = $"marker:{m}" };
        }

        return null; // 模糊 → L2
    }

    private static bool ContainsReference(string lower) =>
        lower.Contains("你") || lower.Contains("它") || lower.Contains("这") ||
        lower.Contains("that") || lower.Contains("you") || lower.Contains("it ");

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

        // 微 prompt: 双方各截断 (用户 120 字 / 上一轮 160 字), 指令+输出约束 ≤ 60 tok
        var user = Truncate(userMessage ?? "", 120);
        var prev = Truncate(previousReply ?? "", 160);
        var prompt =
            "判定用户消息相对上一轮回答: 纠正否定上一轮=C, 认可采纳=A, 新话题无关=N。\n" +
            $"上一轮: {prev}\n用户: {user}\n只输出一个字母。";
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
