namespace agent.exploration;


public sealed class StickyRouteConfig
{
    /// <summary>bge 余弦阈值 (v0.13.1 保守起步; F2 阈值实测校准 20+20 对后定值)</summary>
    public double SimilarityThreshold { get; set; } = 0.80;
    /// <summary>粘性 TTL (小时)</summary>
    public int StickyTtlHours { get; set; } = 72;
    /// <summary>启用开关 (用户钦定 config 可设)</summary>
    public bool Enabled { get; set; } = true;
}
