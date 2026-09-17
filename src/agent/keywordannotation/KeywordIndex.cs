using Microsoft.Extensions.Logging;
using System.Text.RegularExpressions;

namespace agent.keywordannotation;

/// <summary>
/// 关键词索引
/// </summary>
public class KeywordIndex
{
    private readonly Dictionary<string, HashSet<string>> _index = new();
    
    public void Add(string keyword, string documentId)
    {
        var key = keyword.ToLowerInvariant();
        if (!_index.ContainsKey(key))
        {
            _index[key] = new HashSet<string>();
        }
        _index[key].Add(documentId);
    }
    
    public IEnumerable<string> Search(string keyword)
    {
        var key = keyword.ToLowerInvariant();
        return _index.TryGetValue(key, out var docIds) ? docIds : Enumerable.Empty<string>();
    }
    
    public IEnumerable<string> SearchMultiple(IEnumerable<string> keywords)
    {
        var keywordSet = keywords.Select(k => k.ToLowerInvariant()).ToHashSet();
        var result = new HashSet<string>();
        
        foreach (var keyword in keywordSet)
        {
            if (_index.TryGetValue(keyword, out var docIds))
            {
                result.UnionWith(docIds);
            }
        }
        
        return result;
    }
}
