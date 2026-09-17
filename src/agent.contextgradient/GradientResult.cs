namespace agent.contextgradient;

/// <summary>压缩结果</summary>
public sealed class GradientResult
{
    public GradientLevel Level { get; set; }
    public string Content { get; set; } = string.Empty;

    /// <summary>防漂移校验通过</summary>
    public bool DriftCheckPassed { get; set; }

    /// <summary>语义相似度 (P3: embedder 就绪时 = cos(原,压); 否则 null)</summary>
    public double? SemanticSimilarity { get; set; }

    /// <summary>原始长度 → 压缩后长度</summary>
    public int OriginalChars { get; set; }

    /// <summary>v0.13.3 D2: 哨兵丢失清单 (空 = 无丢失; 宿主负责打点 compression_sentinel)</summary>
    public List<string> SentinelLosses { get; set; } = new();
    public int CompressedChars { get; set; }
}
