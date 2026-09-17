namespace agent.exploration;


/// <summary>思考链单步决策 (LLM 产出 — 宿主解析后注入; 本库不调 LLM)。</summary>
public sealed class ThinkStep
{
    /// <summary>本步假设/论断</summary>
    public string Hypothesis { get; set; } = string.Empty;
    /// <summary>决定探索的源 (空 = 准备收敛)</summary>
    public ExploreNode? NextExplore { get; set; }
    /// <summary>本步采纳的依据 (ThinkMemory 引用提升触发)</summary>
    public List<(string RecordId, string Ref)> Citations { get; set; } = new();
}
