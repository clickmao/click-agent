namespace agent.exploration;


/// <summary>
/// v0.13.0 — 待探索源 (探索图节点)。
/// </summary>
public sealed class ExploreNode
{
    public ExploreSourceKind Kind { get; set; }
    /// <summary>引用: URL / 目录路径 / 文件路径 / 文本片段头 128ch</summary>
    public string Ref { get; set; } = string.Empty;
    /// <summary>发现来源 (null = 用户直接给出/种子)</summary>
    public string? DiscoveredFrom { get; set; }
    /// <summary>是否来自上下文 (用户例: 上下文内 URL > 上下文外目录)</summary>
    public bool FromContext { get; set; }
    public int Priority { get; set; }
    /// <summary>该节点已用步数 (渐进深入计数)</summary>
    public int StepsUsed { get; set; }
}
