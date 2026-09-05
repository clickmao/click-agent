using Microsoft.Extensions.Logging;
using System.Text.RegularExpressions;

namespace agent.memory;

/// <summary>
/// 摘要器实现
/// </summary>
public class Summarizer : ISummarizer
{
    private readonly ILogger<Summarizer> _logger;
    
    // 关键事实模式
    private static readonly Regex[] KeyFactPatterns = new[]
    {
        new Regex(@"(?:注意|important|关键|关键点|key point)[:：]\s*(.+)", RegexOptions.IgnoreCase),
        new Regex(@"(?:实现了?|创建了?|developed|created)[:：]\s*(.+)", RegexOptions.IgnoreCase),
        new Regex(@"(?:使用了?|using|应用了?)[:：]\s*(.+)", RegexOptions.IgnoreCase),
    };
    
    // 决策模式
    private static readonly Regex[] DecisionPatterns = new[]
    {
        new Regex(@"(?:决定|decision|选择了?|chose|selected)[:：]\s*(.+)", RegexOptions.IgnoreCase),
        new Regex(@"(?:采用|adopted|采纳)[:：]\s*(.+)", RegexOptions.IgnoreCase),
        new Regex(@"(?:使用|use|utilize)\s+(\w+)\s+(?:作为|as)\s+(.+)", RegexOptions.IgnoreCase),
    };
    
    public Summarizer(ILogger<Summarizer> logger)
    {
        _logger = logger;
    }
    
    public async Task<string> SummarizeAsync(string content, SummarizeOptions? options = null)
    {
        options ??= new SummarizeOptions();
        
        try
        {
            // 提取关键事实
            var keyFacts = await ExtractKeyFactsAsync(content);
            
            // 提取决策
            var decisions = await ExtractDecisionsAsync(content);
            
            // 构建摘要
            var summaryParts = new List<string>();
            
            if (keyFacts.Any())
            {
                summaryParts.Add("## 关键事实");
                summaryParts.AddRange(keyFacts.Take(5));
            }
            
            if (decisions.Any())
            {
                if (summaryParts.Any())
                {
                    summaryParts.Add("");
                }
                summaryParts.Add("## 决策");
                summaryParts.AddRange(decisions.Take(5));
            }
            
            // 如果没有提取到内容，返回压缩版本
            if (!summaryParts.Any())
            {
                return await CompressContentAsync(content, options.CompressionRatio);
            }
            
            return string.Join(Environment.NewLine, summaryParts);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error summarizing content");
            return content.Length > 500 ? content[..500] + "..." : content;
        }
    }
    
    public Task<IEnumerable<string>> ExtractKeyFactsAsync(string content)
    {
        var facts = new List<string>();
        
        foreach (var pattern in KeyFactPatterns)
        {
            var matches = pattern.Matches(content);
            foreach (Match match in matches)
            {
                if (match.Groups.Count > 1)
                {
                    facts.Add(match.Groups[1].Value.Trim());
                }
            }
        }
        
        return Task.FromResult<IEnumerable<string>>(facts.Distinct());
    }
    
    public Task<IEnumerable<string>> ExtractDecisionsAsync(string content)
    {
        var decisions = new List<string>();
        
        foreach (var pattern in DecisionPatterns)
        {
            var matches = pattern.Matches(content);
            foreach (Match match in matches)
            {
                if (match.Groups.Count > 1)
                {
                    decisions.Add(match.Groups[1].Value.Trim());
                }
            }
        }
        
        return Task.FromResult<IEnumerable<string>>(decisions.Distinct());
    }
    
    private Task<string> CompressContentAsync(string content, double ratio)
    {
        // 简单的压缩：保留前N个字符
        var targetLength = (int)(content.Length * ratio);
        var compressed = content.Length > targetLength 
            ? content[..targetLength] + "..." 
            : content;
        
        return Task.FromResult(compressed);
    }
}
