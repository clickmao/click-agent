using Microsoft.Extensions.Logging;
using System.Text.RegularExpressions;

namespace agent.keywordannotation;


/// <summary>
/// 关键词标注器
/// </summary>
public interface IKeywordTagger
{
    Task<List<string>> ExtractKeywordsAsync(string text);
    Task<string> TagDocumentAsync(string documentId, string text);
    Task<IEnumerable<string>> SearchByKeywordAsync(string keyword);
}
