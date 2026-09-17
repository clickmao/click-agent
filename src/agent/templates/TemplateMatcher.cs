using Microsoft.Extensions.Logging;
using System.Text.RegularExpressions;

namespace agent.templates;


/// <summary>
/// 模板匹配器实现
/// </summary>
public class TemplateMatcher : ITemplateMatcher
{
    private readonly ITemplateStore _store;
    private readonly ILogger<TemplateMatcher> _logger;
    
    public TemplateMatcher(ITemplateStore store, ILogger<TemplateMatcher> logger)
    {
        _store = store;
        _logger = logger;
    }
    
    public async Task<TemplateMatchResult?> MatchAsync(string input)
    {
        var candidates = await GetCandidatesAsync(input, 1);
        var first = candidates.FirstOrDefault();
        
        if (first == null)
        {
            return null;
        }
        
        var score = await CalculateSimilarityAsync(input, first.Pattern);
        
        return new TemplateMatchResult
        {
            Template = first,
            Score = score,
            Reason = $"Matched by pattern similarity ({score:P0})"
        };
    }
    
    public async Task<IEnumerable<Template>> GetCandidatesAsync(string input, int topN = 5)
    {
        // 简单的关键词匹配
        var keywords = ExtractKeywords(input);
        
        var templates = await _store.QueryAsync(new TemplateQuery
        {
            IsEnabled = true,
            Take = 100
        });
        
        var scored = templates
            .Select(t => new
            {
                Template = t,
                Score = CalculateMatchScore(input, t, keywords)
            })
            .Where(x => x.Score > 0)
            .OrderByDescending(x => x.Score)
            .Take(topN)
            .Select(x => x.Template);
        
        return scored;
    }
    
    public Task<double> CalculateSimilarityAsync(string input, string templatePattern)
    {
        if (string.IsNullOrEmpty(input) || string.IsNullOrEmpty(templatePattern))
        {
            return Task.FromResult(0.0);
        }
        
        // 简单的相似度计算：交集/并集
        var inputWords = input.Split(' ', StringSplitOptions.RemoveEmptyEntries)
            .Select(w => w.ToLowerInvariant())
            .ToHashSet();
        
        var patternWords = templatePattern.Split(' ', StringSplitOptions.RemoveEmptyEntries)
            .Select(w => w.ToLowerInvariant())
            .ToHashSet();
        
        var intersection = inputWords.Intersect(patternWords).Count();
        var union = inputWords.Union(patternWords).Count();
        
        var similarity = union > 0 ? (double)intersection / union : 0;
        
        return Task.FromResult(similarity);
    }
    
    public async Task<IEnumerable<TemplateMatchResult>> BatchMatchAsync(IEnumerable<string> inputs)
    {
        var results = new List<TemplateMatchResult>();
        
        foreach (var input in inputs)
        {
            var match = await MatchAsync(input);
            if (match != null)
            {
                results.Add(match);
            }
        }
        
        return results;
    }
    
    private List<string> ExtractKeywords(string text)
    {
        // 简单的关键词提取
        var keywords = new List<string>();
        
        // 提取 CamelCase 词
        var camelMatches = Regex.Matches(text, @"[A-Z][a-z]+");
        keywords.AddRange(camelMatches.Select(m => m.Value.ToLowerInvariant()));
        
        // 提取长词（>3字符）
        var wordMatches = Regex.Matches(text, @"\b\w{4,}\b");
        keywords.AddRange(wordMatches.Select(m => m.Value.ToLowerInvariant()));
        
        return keywords.Distinct().ToList();
    }
    
    private double CalculateMatchScore(string input, Template template, List<string> keywords)
    {
        var score = 0.0;
        
        // 标签匹配
        if (template.Tags.Any(tag => keywords.Any(k => tag.Contains(k, StringComparison.OrdinalIgnoreCase))))
        {
            score += 0.3;
        }
        
        // 名称匹配
        if (template.Name.Contains(input, StringComparison.OrdinalIgnoreCase))
        {
            score += 0.4;
        }
        
        // 分类匹配
        if (keywords.Any(k => template.Category.Contains(k, StringComparison.OrdinalIgnoreCase)))
        {
            score += 0.2;
        }
        
        // 模式匹配
        if (template.Pattern.Contains(input, StringComparison.OrdinalIgnoreCase))
        {
            score += 0.3;
        }
        
        // 成功率加成
        score += template.SuccessRate * 0.2;
        
        return Math.Min(score, 1.0);
    }
}
