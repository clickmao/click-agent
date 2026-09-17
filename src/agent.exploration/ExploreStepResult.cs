namespace agent.exploration;


/// <summary>单步探索结果 (打点+回填思考链)。</summary>
public sealed class ExploreStepResult
{
    public bool Ok { get; set; }
    public ExploreSourceKind Kind { get; set; }
    public string Ref { get; set; } = string.Empty;
    public int StepN { get; set; }
    public int BudgetLeft { get; set; }
    public int Ms { get; set; }
    public long Bytes { get; set; }
    /// <summary>探索中发现的新源 (上下文含 URL / 网页含路径 / 目录含子项)</summary>
    public List<ExploreNode> Discovered { get; set; } = new();
    public string? Error { get; set; }
    /// <summary>内容摘要 (回填思考链, ≤400ch)</summary>
    public string Digest { get; set; } = string.Empty;
}
