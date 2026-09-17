using Microsoft.Extensions.Logging;
using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;
using agent.tokencompression;

namespace agent.context;

public partial class ContextAssembler : IContextAssembler
{
    
    /// <summary>
    /// 构建 Prompt Header（优化版，减少格式开销）
    /// </summary>
    private string BuildPromptHeader(
        List<ContextSnippet> snippets,
        ContextAssemblyRequest request)
    {
        if (!snippets.Any())
            return string.Empty;
        
        var sb = new System.Text.StringBuilder();
        
        // 注意: 不加 "=== CONTEXT ===" 包装 —— 由 Prompt.Compose() 统一负责,
        // 避免双重包装污染最终 Prompt
        
        // 按数据源分组
        // v7.14: pinned 源 (会话记忆/Agent 上下文) 恒入选, 其余按相关性补足 — 方向锚不因预算被挤掉
        var pinnedTypes = new HashSet<DataSourceType>
        {
            DataSourceType.SessionMemory,
            DataSourceType.AgentContext,
        };
        var grouped = snippets.GroupBy(s => s.SourceType)
            .OrderByDescending(g => pinnedTypes.Contains(g.Key) ? 2.0 : g.Max(s => s.RelevanceScore))
            .Take(5) // 最多5个数据源 (3→5: pinned 占 2 席后其余源仍有 3 席)
            .ToList();
        
        for (int i = 0; i < grouped.Count; i++)
        {
            var group = grouped[i];
            var sourceName = GetSourceDisplayName(group.Key);
            var snippets_list = group.Take(2).ToList(); // 每个源最多2条
            
            // 数据源标题（简洁格式）
            sb.AppendLine($"[{sourceName}]");
            
            foreach (var snippet in snippets_list)
            {
                var content = snippet.IsCompressed && !string.IsNullOrEmpty(snippet.CompressedContent)
                    ? snippet.CompressedContent
                    : snippet.Content;
                
                // v7.14: pinned 源 (记忆/画像) 内容自控体积, 整块保留;
                // 其余基于 Token 截断
                var truncated = pinnedTypes.Contains(group.Key)
                    ? content
                    : TruncateByTokens(content, 200); // 每条最多200 tokens
                sb.AppendLine(truncated);
            }
            
            if (i < grouped.Count - 1)
                sb.AppendLine();
        }
        
        return sb.ToString();
    }
    
    /// <summary>
    /// 估算 Token 数（改进版，支持中文）
    /// </summary>
    private int EstimateTokens(string text)
    {
        if (string.IsNullOrEmpty(text)) return 0;
        
        double tokens = 0;
        var i = 0;
        
        while (i < text.Length)
        {
            var c = text[i];
            
            // 中文字符范围 (CJK Unified Ideographs)
            if (c >= 0x4E00 && c <= 0x9FFF)
            {
                tokens += 1;
                i++;
            }
            // 日文/韩文
            else if ((c >= 0x3040 && c <= 0x309F) || // Hiragana
                     (c >= 0x30A0 && c <= 0x30FF) || // Katakana
                     (c >= 0xAC00 && c <= 0xD7AF))    // Korean
            {
                tokens += 1;
                i++;
            }
            // 空白字符直接跳过 (必须在 ASCII 分支前判断, 否则死循环)
            else if (char.IsWhiteSpace(c))
            {
                i++;
            }
            // ASCII 字母/数字/标点
            else if (c < 128)
            {
                tokens += 0.25;
                // 统计连续的非空白字符 (整词计 1 个 token)
                while (i < text.Length && text[i] < 128 && !char.IsWhiteSpace(text[i]))
                {
                    i++;
                }
            }
            // 标点符号
            else if (IsPunctuation(c))
            {
                tokens += 0.25;
                i++;
            }
            // 其他Unicode字符
            else
            {
                tokens += 1;
                i++;
            }
        }
        
        return (int)Math.Ceiling(tokens);
    }
    
    /// <summary>
    /// 判断是否为标点符号
    /// </summary>
    private bool IsPunctuation(char c)
    {
        return c == '.' || c == ',' || c == ';' || c == ':' || 
               c == '!' || c == '?' || c == '"' || c == '\'' ||
               c == '(' || c == ')' || c == '[' || c == ']' ||
               c == '{' || c == '}' || c == '-' || c == '_' ||
               c == '+' || c == '=' || c == '/' || c == '\\' ||
               c == '|' || c == '@' || c == '#' || c == '$' ||
               c == '%' || c == '^' || c == '&' || c == '*' ||
               c == '<' || c == '>' || c == '`' || c == '~' ||
               c == '「' || c == '」' || c == '『' || c == '』' || // 中文引号
               c == '【' || c == '】' ||
               c == '—' || c == '…' || c == '·'; // 特殊符号
    }
    
    /// <summary>
    /// 截断内容（基于 Token 而非字符数）
    /// </summary>
    private string TruncateByTokens(string text, int maxTokens)
    {
        if (string.IsNullOrEmpty(text)) return text;
        
        double tokens = 0;
        var i = 0;
        var result = new System.Text.StringBuilder();
        
        while (i < text.Length && tokens < maxTokens)
        {
            var c = text[i];
            
            // 中文字符
            if (c >= 0x4E00 && c <= 0x9FFF)
            {
                result.Append(c);
                tokens += 1;
                i++;
            }
            // 日文/韩文
            else if ((c >= 0x3040 && c <= 0x309F) || (c >= 0x30A0 && c <= 0x30FF) || (c >= 0xAC00 && c <= 0xD7AF))
            {
                result.Append(c);
                tokens += 1;
                i++;
            }
            // ASCII
            else if (c < 128)
            {
                result.Append(c);
                tokens += 0.25;
                i++;
            }
            // 其他
            else
            {
                result.Append(c);
                tokens += 1;
                i++;
            }
        }
        
        if (i < text.Length)
        {
            result.Append("... [截断]");
        }
        
        return result.ToString();
    }
    
    /// <summary>
    /// 提取关键词
    /// </summary>
    /// <summary>停用词表 (v7.8: static readonly, 消每次调用分配)</summary>
    private static readonly HashSet<string> StopWords = new(StringComparer.OrdinalIgnoreCase)
    {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being"
    };
    
    private static List<string> ExtractKeywords(string text)
    {
        return text
            .Split(' ', StringSplitOptions.RemoveEmptyEntries)
            .Where(w => w.Length > 2 && !StopWords.Contains(w))
            .Take(10)
            .ToList();
    }
    
    /// <summary>
    /// 计算消息相关性 (v0.11.0 P3 向量化: 关键词词面 + bge 向量余弦混合打分)
    /// embedder 不可用 → 纯词面 (P1 行为兼容); 可用 → 0.6×词面 + 0.4×语义 (词面精确命中保底, 语义补足同义改写)
    /// </summary>
    private Task<double> CalculateMessageRelevanceAsync(
        Message message, string query, float[]? queryEmbedding,
        List<string>? precomputedKeywords = null, CancellationToken ct = default)
        => agent.contextgradient.MessageRelevanceScorer.ScoreAsync(
            message.Content, query, queryEmbedding, precomputedKeywords, ct);

    // R326 (P16): _queryEmbedding 实例字段已消除 — RecallFromSessionAsync 内局部变量 (DI 单例并发串话修复)
    
    /// <summary>测试入口 (internal): 混合相关性打分 — 直接走静态纯函数 (零 DI 依赖)。</summary>
    internal static Task<double> CalculateMessageRelevanceForTest(
        Message message, string query, agent.contextgradient.ITextEmbedder? embedder)
        => agent.contextgradient.MessageRelevanceScorer.ScoreWithEmbedderAsync(
            message.Content, query, embedder, CancellationToken.None);

    /// <summary>
    /// 判断是否需要网络搜索
    /// </summary>
    private bool ShouldSearchWeb(string message)
    {
        var searchIndicators = new[] 
        { 
            "最新", "今天", "当前", "now", "latest", "recent",
            "搜索", "search", "查找", "find",
            "什么是", "what is", "how to", "怎么", "如何"
        };
        
        return searchIndicators.Any(i => 
            message.Contains(i, StringComparison.OrdinalIgnoreCase));
    }
    
    /// <summary>
    /// 获取数据源显示名称
    /// </summary>
    private string GetSourceDisplayName(DataSourceType sourceType)
    {
        return sourceType switch
        {
            DataSourceType.Memory => "Memory (RAG)",
            DataSourceType.Session => "Session History",
            DataSourceType.WebSearch => "Web Search",
            DataSourceType.UserTendency => "User Preference",
            DataSourceType.WorkspaceFiles => "Workspace Files",
            DataSourceType.ToolOutput => "Tool Output",
            _ => sourceType.ToString()
        };
    }
}
