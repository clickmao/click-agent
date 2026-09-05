using Microsoft.Extensions.Logging;
using System.Text.RegularExpressions;

namespace agent.tokencompression;

/// <summary>
/// Token压缩器接口
/// </summary>
public interface ITokenCompressor
{
    /// <summary>
    /// 压缩上下文
    /// </summary>
    Task<string> CompressAsync(string context, CompressionOptions? options = null);
    
    /// <summary>
    /// 计算Token数
    /// </summary>
    Task<int> CountTokensAsync(string text);
    
    /// <summary>
    /// 截断到指定Token数
    /// </summary>
    Task<string> TruncateAsync(string text, int maxTokens);
    
    /// <summary>
    /// 智能压缩（保留语义）
    /// </summary>
    Task<string> CompressSmartAsync(string context, int maxTokens);
}

/// <summary>
/// 压缩选项
/// </summary>
public class CompressionOptions
{
    /// <summary>
    /// 最大Token数
    /// </summary>
    public int MaxTokens { get; set; } = 500;
    
    /// <summary>
    /// 压缩策略
    /// </summary>
    public CompressionStrategy Strategy { get; set; } = CompressionStrategy.Selective;
    
    /// <summary>
    /// 保留结构（如代码缩进、列表）
    /// </summary>
    public bool PreserveStructure { get; set; } = true;
    
    /// <summary>
    /// 保留关键词
    /// </summary>
    public bool PreserveKeywords { get; set; } = true;
    
    /// <summary>
    /// 保留行号
    /// </summary>
    public bool PreserveLineNumbers { get; set; } = false;
    
    /// <summary>
    /// 保留注释
    /// </summary>
    public bool PreserveComments { get; set; } = false;
    
    /// <summary>
    /// 压缩比 (0.0-1.0)
    /// </summary>
    public double CompressionRatio { get; set; } = 0.5;
    
    /// <summary>
    /// 关键词列表（优先保留）
    /// </summary>
    public List<string>? PriorityKeywords { get; set; }
}

/// <summary>
/// 压缩策略
/// </summary>
public enum CompressionStrategy
{
    /// <summary>总结摘要：保留首尾</summary>
    Summarize,
    
    /// <summary>截断：简单切除</summary>
    Truncate,
    
    /// <summary>选择性保留：保留关键词周围内容</summary>
    Selective,
    
    /// <summary>智能压缩：分析语义保留核心</summary>
    Smart,
    
    /// <summary>增量压缩：渐进式压缩</summary>
    Incremental
}

/// <summary>
/// Token压缩器实现
/// 
/// 参考了以下最佳实践：
/// - Anthropic Claude: 选择性保留关键词
/// - Microsoft Semantic Kernel: 增量压缩策略
/// - LangChain: 保留结构压缩
/// </summary>
public class TokenCompressor : ITokenCompressor
{
    private readonly ILogger<TokenCompressor> _logger;
    
    // 默认保留的关键词
    private readonly HashSet<string> _defaultKeywords = new(StringComparer.OrdinalIgnoreCase)
    {
        // 代码相关
        "function", "class", "method", "return", "if", "else", "for", "while", 
        "foreach", "switch", "case", "break", "continue", "import", "export",
        "public", "private", "protected", "static", "const", "var", "let",
        "async", "await", "try", "catch", "throw", "new", "this", "self",
        
        // Markdown/文档相关
        "#", "##", "###", "-", "*", "1.", "2.", "```", "`",
        "|", "---", "===", "**", "*", "_", "[", "]", "(", ")",
        
        // 通用
        "TODO", "FIXME", "NOTE", "WARNING", "IMPORTANT"
    };
    
    public TokenCompressor(ILogger<TokenCompressor> logger)
    {
        _logger = logger;
    }
    
    /// <summary>
    /// 主压缩入口
    /// </summary>
    public Task<string> CompressAsync(string context, CompressionOptions? options = null)
    {
        options ??= new CompressionOptions();
        
        if (string.IsNullOrWhiteSpace(context))
        {
            return Task.FromResult(string.Empty);
        }
        
        var currentTokens = CountTokensAsync(context).Result;
        if (currentTokens <= options.MaxTokens)
        {
            return Task.FromResult(context);
        }
        
        var result = options.Strategy switch
        {
            CompressionStrategy.Summarize => Summarize(context, options.MaxTokens),
            CompressionStrategy.Truncate => TruncateAsync(context, options.MaxTokens).Result,
            CompressionStrategy.Selective => SelectiveCompress(context, options),
            CompressionStrategy.Smart => CompressSmartAsync(context, options.MaxTokens).Result,
            CompressionStrategy.Incremental => IncrementalCompress(context, options),
            _ => context
        };
        
        _logger.LogDebug("Compressed {Original} tokens to {Compressed} tokens using {Strategy}",
            currentTokens, CountTokensAsync(result).Result, options.Strategy);
        
        return Task.FromResult(result);
    }
    
    /// <summary>
    /// 计算Token数（统一实现，支持中文）
    /// </summary>
    public Task<int> CountTokensAsync(string text)
    {
        if (string.IsNullOrEmpty(text))
        {
            return Task.FromResult(0);
        }
        
        var tokens = 0;
        var i = 0;
        
        while (i < text.Length)
        {
            var c = text[i];
            
            // 中文字符 (CJK)
            if (c >= 0x4E00 && c <= 0x9FFF)
            {
                tokens += 1;
                i++;
            }
            // 日文/韩文
            else if ((c >= 0x3040 && c <= 0x309F) || (c >= 0x30A0 && c <= 0x30FF) || (c >= 0xAC00 && c <= 0xD7AF))
            {
                tokens += 1;
                i++;
            }
            // ASCII 单词（合并连续的非空白字符）
            else if (c < 128 && !char.IsWhiteSpace(c))
            {
                tokens += 1;
                while (i < text.Length && text[i] < 128 && !char.IsWhiteSpace(text[i]))
                {
                    i++;
                }
            }
            // 标点和空白
            else
            {
                i++;
            }
        }
        
        return Task.FromResult(tokens);
    }
    
    /// <summary>
    /// 截断到指定Token数（改进版，支持中文）
    /// </summary>
    public Task<string> TruncateAsync(string text, int maxTokens)
    {
        if (string.IsNullOrEmpty(text))
        {
            return Task.FromResult(text);
        }
        
        var tokens = 0;
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
            // ASCII 单词
            else if (c < 128 && !char.IsWhiteSpace(c))
            {
                var wordStart = i;
                while (i < text.Length && text[i] < 128 && !char.IsWhiteSpace(text[i]))
                {
                    i++;
                }
                
                if (tokens < maxTokens)
                {
                    result.Append(text.Substring(wordStart, i - wordStart));
                    tokens += 1;
                }
            }
            // 其他字符（空白、标点）
            else
            {
                result.Append(c);
                i++;
            }
        }
        
        if (i < text.Length)
        {
            result.Append("...");
        }
        
        return Task.FromResult(result.ToString());
    }
    
    /// <summary>
    /// 智能压缩
    /// </summary>
    public async Task<string> CompressSmartAsync(string context, int maxTokens)
    {
        // Smart 策略: 按段落打分 (信息密度 = 关键词密度 + 结构标记 + 数字/代码特征), 贪心保留高分段直至预算。
        // 注意: 不得回调 CompressAsync (会因 Strategy=Smart 无限递归)。
        if (string.IsNullOrWhiteSpace(context)) return string.Empty;

        var budget = await CountTokensAsync(context) <= maxTokens ? int.MaxValue : maxTokens;

        var paragraphs = context.Split(["\n\n"], StringSplitOptions.RemoveEmptyEntries);
        if (paragraphs.Length <= 1)
        {
            // 单段: 退化为截断
            return await TruncateAsync(context, maxTokens);
        }

        var scored = paragraphs.Select((p, idx) =>
        {
            var tokenCount = CountTokensAsync(p).Result;
            double score = 0;
            if (p.TrimStart().StartsWith("#")) score += 2;                 // 标题
            if (p.Contains("```") || p.Contains("    ")) score += 1.5;     // 代码块/缩进
            if (Regex.IsMatch(p, "\\d")) score += 0.5;                      // 数字
            score += Math.Min(2.0, Regex.Matches(p, "[A-Za-z\u4e00-\u9fff]{4,}").Count / 10.0); // 实词密度
            score += idx == 0 ? 1.0 : 0;                                   // 首段加权
            return (Paragraph: p, Score: score, Tokens: tokenCount, Index: idx);
        })
        .OrderByDescending(x => x.Score)
        .ToList();

        var used = 0;
        var kept = new List<(string Text, int Idx)>();
        foreach (var item in scored)
        {
            if (used + item.Tokens > budget) continue;
            kept.Add((item.Paragraph, item.Index));
            used += item.Tokens;
            if (used >= budget) break;
        }

        // 按原始顺序拼接 (保持可读性)
        var result = string.Join("\n\n", kept.OrderBy(k => k.Idx).Select(k => k.Text));
        return await TruncateAsync(result, maxTokens); // 兜底微调
    }
    
    #region Compression Strategies
    
    /// <summary>
    /// 总结摘要：保留开头和结尾
    /// </summary>
    private string Summarize(string context, int maxTokens)
    {
        var words = context.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        
        if (words.Length <= maxTokens)
        {
            return context;
        }
        
        var keepWords = maxTokens / 2;
        var start = string.Join(" ", words.Take(keepWords));
        var end = string.Join(" ", words.Skip(words.Length - keepWords));
        
        return $"{start}... [摘要: {words.Length - maxTokens} 个词已压缩] ...{end}";
    }
    
    /// <summary>
    /// 选择性压缩：保留关键词周围的内容
    /// </summary>
    private string SelectiveCompress(string context, CompressionOptions options)
    {
        var keywords = GetKeywords(context, options);
        var lines = context.Split('\n');
        var importantLines = new List<(int index, string line, int priority)>();
        var currentLength = 0;
        var maxLength = options.MaxTokens * 5; // 粗略估算
        
        foreach (var line in lines)
        {
            var lineKeywords = keywords.Intersect(
                line.Split(' ', StringSplitOptions.RemoveEmptyEntries),
                StringComparer.OrdinalIgnoreCase
            ).Count();
            
            // 计算优先级
            var priority = lineKeywords * 10;
            
            // 标题行优先级更高
            if (line.TrimStart().StartsWith("#"))
            {
                priority += 20;
            }
            
            // 空行优先级最低
            if (string.IsNullOrWhiteSpace(line))
            {
                priority = -1;
            }
            
            if (priority >= 0 && currentLength + line.Length < maxLength)
            {
                importantLines.Add((importantLines.Count, line, priority));
                currentLength += line.Length;
            }
        }
        
        // 按优先级排序，保留最重要的
        var selected = importantLines
            .OrderByDescending(x => x.priority)
            .Take((int)(lines.Length * options.CompressionRatio))
            .OrderBy(x => x.index) // 保持原始顺序
            .Select(x => x.line);
        
        var result = string.Join("\n", selected);
        
        // 如果还是太长，用简单截断
        if (CountTokensAsync(result).Result > options.MaxTokens)
        {
            result = TruncateAsync(result, options.MaxTokens).Result;
        }
        
        return result;
    }
    
    /// <summary>
    /// 增量压缩
    /// </summary>
    private string IncrementalCompress(string context, CompressionOptions options)
    {
        var current = context;
        var targetTokens = options.MaxTokens;
        var step = 0.1; // 每次压缩10%
        
        while (CountTokensAsync(current).Result > targetTokens && step <= 0.5)
        {
            options.CompressionRatio = 1.0 - step;
            current = SelectiveCompress(current, options);
            step += 0.1;
        }
        
        if (CountTokensAsync(current).Result > targetTokens)
        {
            current = TruncateAsync(current, targetTokens).Result;
        }
        
        return current;
    }
    
    #endregion
    
    #region Helper Methods
    
    /// <summary>
    /// 提取关键词
    /// </summary>
    private HashSet<string> GetKeywords(string context, CompressionOptions options)
    {
        var keywords = new HashSet<string>(_defaultKeywords, StringComparer.OrdinalIgnoreCase);
        
        // 添加用户指定的关键词
        if (options.PriorityKeywords != null)
        {
            foreach (var kw in options.PriorityKeywords)
            {
                keywords.Add(kw);
            }
        }
        
        // 从上下文中提取高频词作为关键词
        var words = context
            .Split(' ', StringSplitOptions.RemoveEmptyEntries)
            .Where(w => w.Length > 3)
            .GroupBy(w => w.ToLower())
            .Where(g => g.Count() >= 2)
            .OrderByDescending(g => g.Count())
            .Take(20)
            .Select(g => g.Key);
        
        foreach (var word in words)
        {
            keywords.Add(word);
        }
        
        return keywords;
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
               c == '<' || c == '>' || c == '`' || c == '~';
    }
    
    #endregion
}

/// <summary>
/// Token 计数工具
/// </summary>
public static class TokenCounter
{
    private static bool IsPunctuation(char c)
    {
        return c == '.' || c == ',' || c == ';' || c == ':' || 
               c == '!' || c == '?' || c == '"' || c == '\'' ||
               c == '(' || c == ')' || c == '[' || c == ']' ||
               c == '{' || c == '}' || c == '-' || c == '_' ||
               c == '+' || c == '=' || c == '/' || c == '\\' ||
               c == '|' || c == '@' || c == '#' || c == '$' ||
               c == '%' || c == '^' || c == '&' || c == '*' ||
               c == '<' || c == '>' || c == '`' || c == '~';
    }
}
