using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;


/// <summary>
/// 数据源统计
/// </summary>
public class DataSourceStats
{
    public DataSourceType SourceType { get; set; }
    public int SnippetCount { get; set; }
    public int TotalTokens { get; set; }
    public double AvgRelevanceScore { get; set; }
    public long RecallTimeMs { get; set; }
}
