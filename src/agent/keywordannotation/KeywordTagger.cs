using Microsoft.Extensions.Logging;
using System.Text.RegularExpressions;

namespace agent.keywordannotation;


/// <summary>
/// 关键词标注器实现（线程安全）
/// </summary>
public class KeywordTagger : IKeywordTagger
{
    private readonly KeywordIndex _index = new();
    private readonly ILogger<KeywordTagger> _logger;
    private readonly object _lock = new();
    
    // 停用词
    private static readonly HashSet<string> StopWords = new(StringComparer.OrdinalIgnoreCase)
    {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "shall", "can", "this", "that",
        "these", "those", "i", "you", "he", "she", "it", "we", "they", "我", "你", "他", "她", "它"
    };
    
    // 重要模式
    private static readonly Regex[] ImportantPatterns = new[]
    {
        new Regex(@"[A-Z][a-z]+(?=[A-Z][a-z]+)"), // CamelCase
        new Regex(@"\b\w+ing\b"),                  // 动名词
        new Regex(@"\b\w+tion\b"),                 // 名词化
        new Regex(@"\b\w+ness\b"),                  // 名词化
        new Regex(@"\b\w+able\b"),                 // 形容词
        new Regex(@"\b\d+\.\d+\.\d+\b"),           // 版本号
        new Regex(@"#\w+"),                        // 标签
    };
    
    public KeywordTagger(ILogger<KeywordTagger> logger)
    {
        _logger = logger;
    }
    
    public Task<List<string>> ExtractKeywordsAsync(string text)
    {
        var keywords = new List<string>();
        
        // 提取CamelCase词
        foreach (Match match in ImportantPatterns[0].Matches(text))
        {
            keywords.Add(match.Value);
        }
        
        // 提取英文单词（长度>=4）
        var words = Regex.Matches(text, @"\b[a-zA-Z]{4,}\b")
            .Cast<Match>()
            .Select(m => m.Value.ToLowerInvariant())
            .Where(w => !StopWords.Contains(w))
            .Distinct();
        
        keywords.AddRange(words);
        
        // 提取中文词（长度>=2）
        var chineseWords = Regex.Matches(text, @"[\u4e00-\u9fa5]{2,}")
            .Cast<Match>()
            .Select(m => m.Value)
            .Distinct();
        
        keywords.AddRange(chineseWords);
        
        // TF-IDF简化版：词频统计
        var wordCounts = keywords
            .GroupBy(k => k.ToLowerInvariant())
            .Where(g => g.Count() >= 2)
            .Select(g => g.Key)
            .ToList();
        
        keywords.AddRange(wordCounts);
        
        return Task.FromResult(keywords.Distinct().ToList());
    }
    
    public Task<string> TagDocumentAsync(string documentId, string text)
    {
        var keywords = ExtractKeywordsAsync(text).Result;
        
        foreach (var keyword in keywords)
        {
            _index.Add(keyword, documentId);
        }
        
        _logger.LogDebug("Tagged document {DocId} with {Count} keywords", documentId, keywords.Count);
        
        return Task.FromResult(string.Join(", ", keywords.Take(10)));
    }
    
    public Task<IEnumerable<string>> SearchByKeywordAsync(string keyword)
    {
        return Task.FromResult(_index.Search(keyword));
    }
}
