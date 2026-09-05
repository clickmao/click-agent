using Microsoft.Extensions.Logging;
using System.Text.RegularExpressions;

namespace agent.templates;

/// <summary>
/// 模板管理器实现
/// </summary>
public class TemplateManager : ITemplateStore
{
    private readonly ILogger<TemplateManager> _logger;
    private readonly Dictionary<string, Template> _templates = new();
    private readonly object _lock = new();
    
    // 示例模式（用于识别）
    private static readonly Dictionary<string, string> CategoryPatterns = new()
    {
        { "DSL", @"^(rule|token|parser)\s" },
        { "Markdown", @"^#{1,6}\s|^\*\*|^```" },
        { "Code", @"^(public|private|class|interface|function)\s" },
        { "API", @"^(GET|POST|PUT|DELETE|PATCH)\s" },
    };
    
    public TemplateManager(ILogger<TemplateManager> logger)
    {
        _logger = logger;
    }
    
    public Task<Template> AddAsync(Template template)
    {
        lock (_lock)
        {
            if (string.IsNullOrEmpty(template.Id))
            {
                template.Id = Guid.NewGuid().ToString();
            }
            
            template.CreatedAt = DateTime.UtcNow;
            template.UpdatedAt = DateTime.UtcNow;
            
            _templates[template.Id] = template;
        }
        
        _logger.LogDebug("Added template {TemplateId}: {TemplateName}", template.Id, template.Name);
        return Task.FromResult(template);
    }
    
    public Task<IEnumerable<Template>> QueryAsync(TemplateQuery query)
    {
        lock (_lock)
        {
            var results = _templates.Values.AsEnumerable();
            
            // 按名称过滤
            if (!string.IsNullOrEmpty(query.Name))
            {
                results = results.Where(t => 
                    t.Name.Contains(query.Name, StringComparison.OrdinalIgnoreCase));
            }
            
            // 按分类过滤
            if (!string.IsNullOrEmpty(query.Category))
            {
                results = results.Where(t => 
                    t.Category.Equals(query.Category, StringComparison.OrdinalIgnoreCase));
            }
            
            // 按模式过滤
            if (!string.IsNullOrEmpty(query.Pattern))
            {
                results = results.Where(t => 
                    t.Pattern.Contains(query.Pattern, StringComparison.OrdinalIgnoreCase));
            }
            
            // 按标签过滤
            if (query.Tags != null && query.Tags.Any())
            {
                results = results.Where(t => 
                    query.Tags.Any(tag => t.Tags.Contains(tag, StringComparer.OrdinalIgnoreCase)));
            }
            
            // 按启用状态过滤
            if (query.IsEnabled.HasValue)
            {
                results = results.Where(t => t.IsEnabled == query.IsEnabled.Value);
            }
            
            // 按成功率过滤
            if (query.MinSuccessRate.HasValue)
            {
                results = results.Where(t => t.SuccessRate >= query.MinSuccessRate.Value);
            }
            
            // 排序
            results = query.SortBy.ToLowerInvariant() switch
            {
                "name" => query.Descending 
                    ? results.OrderByDescending(t => t.Name) 
                    : results.OrderBy(t => t.Name),
                "successrate" => query.Descending 
                    ? results.OrderByDescending(t => t.SuccessRate) 
                    : results.OrderBy(t => t.SuccessRate),
                "usagecount" => query.Descending 
                    ? results.OrderByDescending(t => t.UsageCount) 
                    : results.OrderBy(t => t.UsageCount),
                "createdat" => query.Descending 
                    ? results.OrderByDescending(t => t.CreatedAt) 
                    : results.OrderBy(t => t.CreatedAt),
                _ => results
            };
            
            return Task.FromResult(results.Skip(query.Skip).Take(query.Take));
        }
    }
    
    public Task<Template?> GetByIdAsync(string id)
    {
        lock (_lock)
        {
            _templates.TryGetValue(id, out var template);
            return Task.FromResult(template);
        }
    }
    
    public Task<Template?> GetByNameAsync(string name, string category)
    {
        lock (_lock)
        {
            var template = _templates.Values.FirstOrDefault(t => 
                t.Name.Equals(name, StringComparison.OrdinalIgnoreCase) &&
                t.Category.Equals(category, StringComparison.OrdinalIgnoreCase));
            return Task.FromResult(template);
        }
    }
    
    public Task UpdateAsync(Template template)
    {
        lock (_lock)
        {
            if (_templates.ContainsKey(template.Id))
            {
                template.UpdatedAt = DateTime.UtcNow;
                _templates[template.Id] = template;
                _logger.LogDebug("Updated template {TemplateId}", template.Id);
            }
        }
        
        return Task.CompletedTask;
    }
    
    public Task DeleteAsync(string id)
    {
        lock (_lock)
        {
            if (_templates.Remove(id))
            {
                _logger.LogDebug("Deleted template {TemplateId}", id);
            }
        }
        
        return Task.CompletedTask;
    }
    
    public Task<IEnumerable<Template>> GetByCategoryAsync(string category)
    {
        lock (_lock)
        {
            var templates = _templates.Values
                .Where(t => t.Category.Equals(category, StringComparison.OrdinalIgnoreCase))
                .OrderByDescending(t => t.UsageCount);
            return Task.FromResult<IEnumerable<Template>>(templates.ToList());
        }
    }
    
    public Task<IEnumerable<string>> GetCategoriesAsync()
    {
        lock (_lock)
        {
            var categories = _templates.Values
                .Select(t => t.Category)
                .Distinct()
                .OrderBy(c => c);
            return Task.FromResult<IEnumerable<string>>(categories.ToList());
        }
    }
    
    public Task<string> ApplyTemplateAsync(Template template, ApplyContext context)
    {
        // 简单的模板应用：替换占位符
        var result = template.Pattern;
        
        foreach (var (key, value) in context.Inputs)
        {
            result = result.Replace($"{{{{{key}}}}}", value.ToString() ?? string.Empty);
        }
        
        return Task.FromResult(result);
    }
    
    public Task AddCorrectExampleAsync(string templateId, CorrectExample example)
    {
        lock (_lock)
        {
            if (_templates.TryGetValue(templateId, out var template))
            {
                template.CorrectExamples.Add(example);
                template.UpdatedAt = DateTime.UtcNow;
            }
        }
        
        return Task.CompletedTask;
    }
    
    public Task AddIncorrectExampleAsync(string templateId, IncorrectExample example)
    {
        lock (_lock)
        {
            if (_templates.TryGetValue(templateId, out var template))
            {
                template.IncorrectExamples.Add(example);
                template.UpdatedAt = DateTime.UtcNow;
            }
        }
        
        return Task.CompletedTask;
    }
    
    public Task RecordUsageAsync(string templateId, bool success)
    {
        lock (_lock)
        {
            if (_templates.TryGetValue(templateId, out var template))
            {
                template.UsageCount++;
                if (success)
                {
                    // 更新成功率
                    var totalSuccess = template.CorrectExamples
                        .Sum(e => e.SuccessCount);
                    template.SuccessRate = template.UsageCount > 0 
                        ? (double)totalSuccess / template.UsageCount 
                        : 0;
                }
                template.UpdatedAt = DateTime.UtcNow;
            }
        }
        
        return Task.CompletedTask;
    }
    
    public Task<IEnumerable<Template>> GetPopularAsync(int count)
    {
        lock (_lock)
        {
            var templates = _templates.Values
                .Where(t => t.IsEnabled)
                .OrderByDescending(t => t.UsageCount)
                .Take(count);
            return Task.FromResult(templates);
        }
    }
    
    public Task<IEnumerable<Template>> GetRecommendedAsync(string? category, int count = 5)
    {
        lock (_lock)
        {
            var query = _templates.Values.Where(t => t.IsEnabled);
            
            if (!string.IsNullOrEmpty(category))
            {
                query = query.Where(t => t.Category.Equals(category, StringComparison.OrdinalIgnoreCase));
            }
            
            var templates = query
                .OrderByDescending(t => t.SuccessRate * 0.6 + t.UsageCount * 0.4)
                .Take(count);
            
            return Task.FromResult(templates);
        }
    }
}

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
