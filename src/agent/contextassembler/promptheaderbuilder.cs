using agent.core;

namespace agent.context;

/// <summary>
/// Prompt Header 格式选项
/// </summary>
public enum PromptHeaderFormat
{
    /// <summary>简洁模式：仅内容</summary>
    Compact,
    
    /// <summary>标准模式：带标签</summary>
    Standard,
    
    /// <summary>详细模式：带元数据</summary>
    Detailed,
    
    /// <summary>调试模式：含统计</summary>
    Debug
}

/// <summary>
/// Prompt Header 构建器
/// 
/// 参考了 Claude Code 和 Codex 的上下文组织方式
/// </summary>
public class PromptHeaderBuilder
{
    private readonly List<ContextSnippet> _snippets = new();
    private readonly List<string> _warnings = new();
    private PromptHeaderFormat _format = PromptHeaderFormat.Standard;
    private bool _includeTimestamp = false;
    private bool _includeTokenStats = true;
    private bool _includeRelevanceScores = false;
    private string _headerPrefix = "=== CONTEXT";
    private string _headerSuffix = "=== END CONTEXT";
    private int _maxSnippetsPerSource = 3;
    private int _maxContentLength = 800;
    private bool _useMarkdown = true;
    
    public PromptHeaderBuilder()
    {
    }
    
    /// <summary>
    /// 添加片段
    /// </summary>
    public PromptHeaderBuilder AddSnippet(ContextSnippet snippet)
    {
        _snippets.Add(snippet);
        return this;
    }
    
    /// <summary>
    /// 添加片段集合
    /// </summary>
    public PromptHeaderBuilder AddSnippets(IEnumerable<ContextSnippet> snippets)
    {
        _snippets.AddRange(snippets);
        return this;
    }
    
    /// <summary>
    /// 添加警告
    /// </summary>
    public PromptHeaderBuilder AddWarning(string warning)
    {
        _warnings.Add(warning);
        return this;
    }
    
    /// <summary>
    /// 设置格式
    /// </summary>
    public PromptHeaderBuilder WithFormat(PromptHeaderFormat format)
    {
        _format = format;
        return this;
    }
    
    /// <summary>
    /// 包含时间戳
    /// </summary>
    public PromptHeaderBuilder WithTimestamp(bool include = true)
    {
        _includeTimestamp = include;
        return this;
    }
    
    /// <summary>
    /// 包含 Token 统计
    /// </summary>
    public PromptHeaderBuilder WithTokenStats(bool include = true)
    {
        _includeTokenStats = include;
        return this;
    }
    
    /// <summary>
    /// 包含相关性分数
    /// </summary>
    public PromptHeaderBuilder WithRelevanceScores(bool include = true)
    {
        _includeRelevanceScores = include;
        return this;
    }
    
    /// <summary>
    /// 设置分隔符
    /// </summary>
    public PromptHeaderBuilder WithDelimiters(string prefix, string suffix)
    {
        _headerPrefix = prefix;
        _headerSuffix = suffix;
        // 显式自定义分隔符 = 调用者要求 plain 文本壳 (否则 markdown 壳会吞掉自定义分隔符)
        _useMarkdown = false;
        return this;
    }
    
    /// <summary>
    /// 设置每个源的最大片段数
    /// </summary>
    public PromptHeaderBuilder WithMaxSnippetsPerSource(int max)
    {
        _maxSnippetsPerSource = max;
        return this;
    }
    
    /// <summary>
    /// 设置最大内容长度
    /// </summary>
    public PromptHeaderBuilder WithMaxContentLength(int max)
    {
        _maxContentLength = max;
        return this;
    }
    
    /// <summary>
    /// 使用 Markdown 格式
    /// </summary>
    public PromptHeaderBuilder UseMarkdown(bool use = true)
    {
        _useMarkdown = use;
        return this;
    }
    
    /// <summary>
    /// 构建
    /// </summary>
    public string Build()
    {
        var sb = new System.Text.StringBuilder();
        
        // 1. Header
        BuildHeader(sb);
        
        // 2. 内容
        BuildContent(sb);
        
        // 3. 警告
        BuildWarnings(sb);
        
        // 4. Footer
        BuildFooter(sb);
        
        return sb.ToString();
    }
    
    private void BuildHeader(System.Text.StringBuilder sb)
    {
        if (_useMarkdown)
        {
            sb.AppendLine("```context");
        }
        else
        {
            sb.AppendLine(_headerPrefix);
        }
        
        if (_format >= PromptHeaderFormat.Standard)
        {
            sb.AppendLine($"# Multi-Source Context Assembly");
        }
        
        if (_includeTimestamp)
        {
            sb.AppendLine($"# Generated: {DateTime.UtcNow:yyyy-MM-dd HH:mm:ss} UTC");
        }
        
        sb.AppendLine();
    }
    
    private void BuildContent(System.Text.StringBuilder sb)
    {
        // 按相关性排序
        var sortedSnippets = _snippets
            .OrderByDescending(s => s.RelevanceScore)
            .ToList();
        
        // 分组
        var grouped = sortedSnippets
            .GroupBy(s => s.SourceType)
            .OrderByDescending(g => g.Max(s => s.RelevanceScore));
        
        foreach (var group in grouped)
        {
            var sourceName = GetSourceName(group.Key);
            var snippets = group.Take(_maxSnippetsPerSource).ToList();
            
            // Source Header
            if (_useMarkdown)
            {
                sb.AppendLine($"## {sourceName}");
            }
            else
            {
                sb.AppendLine($"[{sourceName}]");
            }
            
            // Snippets
            foreach (var snippet in snippets)
            {
                BuildSnippet(sb, snippet);
            }
            
            sb.AppendLine();
        }
    }
    
    private void BuildSnippet(System.Text.StringBuilder sb, ContextSnippet snippet)
    {
        var content = TruncateContent(snippet);
        
        if (_format >= PromptHeaderFormat.Standard)
        {
            // 带标签
            var tags = snippet.Tags.Any() 
                ? $" [{string.Join(", ", snippet.Tags.Take(3))}]" 
                : "";
            
            if (_includeRelevanceScores)
            {
                var score = $"{snippet.RelevanceScore:P0}";
                sb.AppendLine($"- [{score}] {content}{tags}");
            }
            else
            {
                sb.AppendLine($"- {content}{tags}");
            }
        }
        else
        {
            // 简洁
            sb.AppendLine($"- {content}");
        }
    }
    
    private void BuildWarnings(System.Text.StringBuilder sb)
    {
        if (_warnings.Any() && _format >= PromptHeaderFormat.Detailed)
        {
            sb.AppendLine("### Warnings");
            foreach (var warning in _warnings)
            {
                sb.AppendLine($"- ⚠️ {warning}");
            }
            sb.AppendLine();
        }
    }
    
    private void BuildFooter(System.Text.StringBuilder sb)
    {
        if (_includeTokenStats && _snippets.Any())
        {
            var totalTokens = _snippets.Sum(s => s.EstimatedTokens);
            var snippetCount = _snippets.Count;
            var sourceCount = _snippets.Select(s => s.SourceType).Distinct().Count();
            
            sb.AppendLine("---");
            sb.AppendLine($"Statistics: {snippetCount} snippets | {totalTokens} tokens | {sourceCount} sources");
        }
        
        if (_format >= PromptHeaderFormat.Debug)
        {
            var bySource = string.Join(", ", _snippets
                .GroupBy(s => s.SourceType)
                .Select(g => $"{g.Key}:{g.Count()}"));
            sb.AppendLine($"Sources: {bySource}");
        }
        
        sb.AppendLine();
        
        if (_useMarkdown)
        {
            sb.AppendLine("```");
        }
        else
        {
            sb.AppendLine(_headerSuffix);
        }
    }
    
    private string TruncateContent(ContextSnippet snippet)
    {
        var content = snippet.IsCompressed && !string.IsNullOrEmpty(snippet.CompressedContent)
            ? snippet.CompressedContent
            : snippet.Content;
        
        if (content.Length > _maxContentLength)
        {
            return content[.._maxContentLength] + "...";
        }
        
        return content;
    }
    
    private string GetSourceName(DataSourceType sourceType)
    {
        return sourceType switch
        {
            DataSourceType.Memory => "📚 Memory (RAG)",
            DataSourceType.Session => "💬 Session History",
            DataSourceType.WebSearch => "🌐 Web Search",
            DataSourceType.UserTendency => "👤 User Preference",
            DataSourceType.WorkspaceFiles => "📁 Workspace Files",
            DataSourceType.ToolOutput => "🔧 Tool Output",
            _ => sourceType.ToString()
        };
    }
}

/// <summary>
/// 静态扩展方法
/// </summary>
public static class ContextSnippetExtensions
{
    /// <summary>
    /// 从 Message 创建片段
    /// </summary>
    public static ContextSnippet FromMessage(Message message, double relevanceScore = 0.5)
    {
        return new ContextSnippet
        {
            SourceType = DataSourceType.Session,
            SourceName = "Session",
            Content = $"[{message.Role}] {message.Content}",
            RelevanceScore = relevanceScore,
            CreatedAt = message.Timestamp,
            Metadata = new Dictionary<string, object>
            {
                { "messageId", message.Id },
                { "role", message.Role.ToString() }
            },
            EstimatedTokens = EstimateTokens(message.Content),
            Tags = new List<string> { message.Role.ToString().ToLower() }
        };
    }
    
    /// <summary>
    /// 从 RAG 结果创建片段
    /// </summary>
    public static ContextSnippet FromRAGResult(
        rag.RecallResult result, 
        string sourceName = "RAG Memory")
    {
        return new ContextSnippet
        {
            Id = result.Document.Id,
            SourceType = DataSourceType.Memory,
            SourceName = sourceName,
            Content = result.HighlightedContent ?? result.Document.Content,
            RelevanceScore = result.Score,
            CreatedAt = result.Document.CreatedAt,
            Metadata = result.Document.Metadata,
            Tags = result.Document.Keywords,
            EstimatedTokens = EstimateTokens(result.Document.Content)
        };
    }
    
    /// <summary>
    /// 估算 Token
    /// </summary>
    public static int EstimateTokens(string text)
    {
        if (string.IsNullOrEmpty(text)) return 0;
        
        var chineseChars = text.Count(c => c >= 0x4E00 && c <= 0x9FFF);
        var englishWords = text.Split(' ', StringSplitOptions.RemoveEmptyEntries).Length;
        
        return (int)(chineseChars * 1.5 + englishWords * 1.3);
    }
}
