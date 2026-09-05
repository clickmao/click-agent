namespace agent.contextgradient;

/// <summary>梯度层级 (L0 全文 → L3 仅标题)</summary>
public enum GradientLevel
{
    /// <summary>L0: 全文保留 (相关性 ≥ 0.8)</summary>
    Full,

    /// <summary>L1: 首段+要点句保留 (0.5-0.8)</summary>
    SummarySentences,

    /// <summary>L2: 规则压缩 — 去空行/去重复/截断到预算 (0.3-0.5)</summary>
    RuleCompressed,

    /// <summary>L3: 仅保留首行标题/来源标识 (&lt; 0.3)</summary>
    TitleOnly,
}

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

/// <summary>压缩结果</summary>
public sealed class GradientResult
{
    public GradientLevel Level { get; set; }
    public string Content { get; set; } = string.Empty;

    /// <summary>防漂移校验通过</summary>
    public bool DriftCheckPassed { get; set; }

    /// <summary>原始长度 → 压缩后长度</summary>
    public int OriginalChars { get; set; }
    public int CompressedChars { get; set; }
}
