using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;


/// <summary>
/// 组装器统计
/// </summary>
public class ContextAssemblerStats
{
    public long TotalAssemblies { get; set; }
    public long TotalSnippets { get; set; }
    public long TotalTokensAssembled { get; set; }
    public double AvgAssemblyTimeMs { get; set; }
    public Dictionary<DataSourceType, long> RecallCountBySource { get; set; } = new();
    public long CacheHits { get; set; }
    public long CacheMisses { get; set; }
}
