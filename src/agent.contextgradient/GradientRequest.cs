namespace agent.contextgradient;


/// <summary>压缩请求</summary>
public sealed class GradientRequest
{
    public string Content { get; set; } = string.Empty;
    public double RelevanceScore { get; set; }

    /// <summary>目标 token 预算 (L2 用)</summary>
    public int TokenBudget { get; set; }

    /// <summary>防漂移锚词 (目标关键词 — 压缩后必须保留至少 1 个)</summary>
    public List<string> AnchorWords { get; set; } = new();
}
