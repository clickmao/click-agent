using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;


/// <summary>
/// 上下文摘要（轻量级）
/// </summary>
public class ContextSummary
{
    public int TotalSnippets { get; set; }
    public Dictionary<DataSourceType, int> SnippetsBySource { get; set; } = new();
    public List<string> KeyTopics { get; set; } = new();
    public int EstimatedTokens { get; set; }
    public DateTime GeneratedAt { get; set; } = DateTime.UtcNow;
}
