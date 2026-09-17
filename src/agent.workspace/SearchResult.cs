using Microsoft.Extensions.Logging;

namespace agent.workspace;


/// <summary>
/// 搜索结果
/// </summary>
public class SearchResult
{
    public string FilePath { get; set; } = string.Empty;
    public int LineNumber { get; set; }
    public string Content { get; set; } = string.Empty;
    public int MatchStart { get; set; }
    public int MatchEnd { get; set; }
}
