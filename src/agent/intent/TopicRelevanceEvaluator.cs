using agent.intent;

namespace agent.intent;

/// <summary>
/// R308 — 合并判定 API (用户问询驱动): 会话输入相关度的统一评估器。
/// 把两处独立判定 (TaskRelevanceChecker 隔离评分 + topic_drift 画像词面) 收敛为一个
/// TopicRelevanceVerdict, 一次计算多路消费 (subagent 隔离 / L1 牵引提示 / 正常)。
/// 输入共享: 当前轮消息 + 会话锚 (目标实体/意图 + 画像核心主题)。
/// </summary>
public static class TopicRelevanceEvaluator
{
    public sealed record TopicRelevanceVerdict
    {
        public int Score { get; init; }
        public bool IsIsolated { get; init; }
        public bool IsDrift { get; init; }
        public Recommendation Action { get; init; }
        public IReadOnlyList<string> Signals { get; init; } = Array.Empty<string>();
        /// <summary>会话核心主题 (画像 top-1, 供牵引提示文案使用)</summary>
        public string CoreTopic { get; init; } = string.Empty;
    }

    public enum Recommendation
    {
        /// <summary>正常 (与会话主题相关)</summary>
        Normal = 0,
        /// <summary>轻牵引 (偏离但未达隔离阈值 — 回复尾追加衔接提示)</summary>
        SteerHint = 1,
        /// <summary>隔离 (无关任务 — subagent 隔离执行)</summary>
        Isolate = 2,
    }

    /// <summary>
    /// 统一评估。signal 权重: 实体重叠 ±2 (强) / 意图不同 +1 / 显式离题词 +1 / 画像词面偏离 +1 (弱, 替换原二值)。
    /// 指代词/短询问 → 一票 Normal (依赖上文的追问不是新话题)。
    /// isolationThreshold 与 TaskRelevanceChecker.DefaultIsolationThreshold 同源 (2)。
    /// </summary>
    public static TopicRelevanceVerdict Evaluate(
        string incomingMessage,
        IReadOnlyList<string> goalKeyEntities,
        string goalIntent,
        string incomingIntent,
        string coreTopic,
        int isolationThreshold = 2)
    {
        var (isIsolated, score, reason) = TaskRelevanceChecker.Check(
            goalKeyEntities, goalIntent, incomingMessage, incomingIntent, isolationThreshold);

        var signals = new List<string>();
        if (!string.IsNullOrEmpty(reason))
            signals.AddRange(reason.Split(';', StringSplitOptions.RemoveEmptyEntries | TrimEntry)
                .Select(t => t.Trim())
                .Where(t => t.Length > 0));

        // 画像词面信号 (弱, +0): 只做归一化信息补全 — Check 已含实体重叠 (更强),
        // 重复加权会双算。coreTopic 记入 verdict 供牵引文案。
        var coreTopicEffective = coreTopic ?? string.Empty;

        var isDrift = !string.IsNullOrEmpty(coreTopicEffective) &&
                      !coreTopicEffective.ToLowerInvariant().Split(' ', '-', '_')
                          .Any(t => t.Length > 1 && incomingMessage.ToLowerInvariant().Contains(t));

        // R308 修正: Check 的一票否决信号 (指代词/实现询问 — 依赖上文) 同时压制 drift —
        // 依赖上文的追问不是话题漂移 (R301 语义: drift 是"新输入离开核心主题", 追问本来就贴着上文)。
        // R308 修正 (结构): Check 的短询问一票否决会**跳过实体重叠检查** — 偏题新话题 ("红烧肉怎么做?")
        // 被误判追问。evaluator 补算重叠事实: goalEntities 与消息无 4-gram/包含重叠 → 真离题, veto 不生效。
        // 词表移除后 (2026-09-19): 原「指代词 / 实现询问」词表否决 → 改为**证据充分性**否决。
        // TaskRelevanceChecker 的「证据不足 (短消息) / 跨语言」理由即"依赖上文 / 语义不可比"的机制化表达:
        // 证据不足 ⇒ 既不算隔离, 也不算漂移 (追问不被牵引; fail-safe 方向)。
        var evidenceVeto = signals.Any(sg => sg.Contains("证据不足") || sg.Contains("跨语言"));
        // R313: 单字衔接副词精修 — Check 词表含 "再" (单字), "再讲一个糖醋排骨" 这类
        // 衔接副词 + 全新话题实体 会被误判指代 (绝对 veto → drift 恒 false, L1 牵引失效)。
        // 判据: 消息仅以单字副词 ("再"/"然后"/"接着") 开头衔接 + 词面偏离已成立 (isDrift 原始值 true)
        // → 该"指代"只是句式衔接, 不构成上文依赖, veto 不适用。
        // 复合指代 ("再说说刚才那个") 因同时命中复合词 (刚才/那个) 不受此修影响 (Check 归一化
        // Contains 命中任意复合词 → 仍绝对 veto — 真回指安全)。
        // (词表时代的中文衔接副词精修 已移除 — 产品码内不再有任何中文词面判据)
        if (evidenceVeto) isDrift = false;

        if (isDrift && !isIsolated)
            signals.Add("画像词面偏离 (未达隔离阈值)");

        var action = isIsolated ? Recommendation.Isolate
            : isDrift ? Recommendation.SteerHint
            : Recommendation.Normal;

        return new TopicRelevanceVerdict
        {
            Score = score,
            IsIsolated = isIsolated,
            IsDrift = isDrift,
            Action = action,
            Signals = signals,
            CoreTopic = coreTopicEffective,
        };
    }

    private static readonly StringSplitOptions TrimEntry =
        StringSplitOptions.TrimEntries;

    /// <summary>R308: 消息实体与目标实体是否零重叠 (4-gram 交叉, 与 Check 同口径)。</summary>
    private static bool HasNoEntityOverlap(string incomingMessage, IReadOnlyList<string> goalKeyEntities)
    {
        var incoming = TaskRelevanceChecker.ExtractEntities(incomingMessage);
        if (incoming.Count == 0 || goalKeyEntities.Count == 0)
            return false; // 无法判定 → 不当离题事实
        return !goalKeyEntities.Any(e => incoming.Any(i =>
            i.Contains(e, StringComparison.OrdinalIgnoreCase) ||
            e.Contains(i, StringComparison.OrdinalIgnoreCase)));
    }
}
