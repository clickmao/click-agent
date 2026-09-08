namespace agent.exploration;

/// <summary>单条依据 (探索/检索所得)。</summary>
public sealed class EvidenceItem
{
    public string Ref { get; set; } = string.Empty;          // URL/文件/RAG id
    public string Domain { get; set; } = string.Empty;       // 来源域 (URL host / 文件根)
    public double SourceHistoryConfidence { get; set; } = 0.5; // think-memory 历史置信
    public double Relevance { get; set; } = 0.5;             // bge 相似度 (与问题)
    public bool SupportsClaim { get; set; } = true;          // 是否支持当前论断
}

/// <summary>
/// v0.13.0 T3 M-A — 依据置信度评估 (用户钦定: 有限时间内多源对比, 不能只看一家)。
/// 置信 = 0.4*历史 + 0.4*相关 + 0.2*多源一致; 单来源封顶 0.65 (medium)。
/// </summary>
public static class EvidenceScorer
{
    public const double HighThreshold = 0.7;
    public const double SingleSourceCap = 0.65;

    public static double Score(IReadOnlyList<EvidenceItem> supporting, double wHistory = 0.4, double wRelevance = 0.4, double wAgreement = 0.2)
    {
        if (supporting.Count == 0) return 0.0;
        var distinctDomains = supporting.Select(e => e.Domain).Distinct(StringComparer.OrdinalIgnoreCase).Count();
        var agreement = Math.Min(1.0, distinctDomains / 2.0); // ≥2 独立域 = 满一致
        var perItem = supporting.Select(e =>
            wHistory * e.SourceHistoryConfidence + wRelevance * e.Relevance + wAgreement * agreement);
        var score = perItem.Average();
        // 用户钦定: 单来源 (仅 1 个独立域) 封顶 medium — 不看一家定论:
        if (distinctDomains <= 1) score = Math.Min(score, SingleSourceCap);
        return Math.Round(Math.Clamp(score, 0.0, 1.0), 4);
    }

    public static string GradeOf(double confidence) => confidence switch
    {
        >= HighThreshold => "high",
        >= 0.4 => "medium",
        > 0 => "low",
        _ => "none",
    };
}
