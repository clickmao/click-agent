namespace agent.exploration;


public sealed class ThinkMemoryConfig
{
    /// <summary>检索相似度阈值 (保守 — bge 小模型语义漂移防护)</summary>
    public double MinSimilarity { get; set; } = 0.75;
    /// <summary>引用命中后的置信提升量 (用户钦定 "稍微提升")</summary>
    public double CitationBoost { get; set; } = 0.05;
    /// <summary>置信上限</summary>
    public double MaxConfidence { get; set; } = 1.0;
    /// <summary>长期未命中衰减量 (30 天未引用)</summary>
    public double DecayAmount { get; set; } = 0.10;
    public int DecayAfterDays { get; set; } = 30;
    /// <summary>衰减后归档线</summary>
    public double ArchiveBelow { get; set; } = 0.30;
    /// <summary>负样本思考的检索降权乘数</summary>
    public double NegativePenalty { get; set; } = 0.5;
}
