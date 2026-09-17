namespace agent.pipeline;


/// <summary>
/// 依赖图
/// </summary>
public class DependencyGraph
{
    public Dictionary<string, List<string>> Edges { get; set; } = new();
    public List<string> TopologicalOrder { get; set; } = new();
}
