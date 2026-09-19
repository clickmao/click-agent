using System.Globalization;

namespace agent.nlp;

/// <summary>
/// 文本信号门面 — 「词表命中」类判定的替代依据: 语言标签 (模型输出) + 分词 (多语言 BPE)。
/// 约定: 任何需要「判断这是什么语言 / 抽关键词 / 比较两段文本」的地方, 一律走本类, 不得再写字符集或标记表。
/// </summary>
public static class TextSignal
{
    /// <summary>语言标签 (fastText lid.176 模型输出)。</summary>
    public static string Language(string text) => LanguageIdentifier.Detect(text);

    /// <summary>是否同一语言 (跨语言指代/修正的第一道前提)。</summary>
    public static bool SameLanguage(string a, string b) => LanguageIdentifier.SameLanguage(a, b);

    /// <summary>
    /// 关键词 token: 分词 → 去纯标点/空白 token → 保序去重 → 截断。
    /// 替代 TaskRelevanceChecker.ExtractEntities (原实现只认 ASCII 字母数字 + CJK 码点区间)。
    /// </summary>
    public static IReadOnlyList<string> KeyTokens(string text, int max = 32)
    {
        if (string.IsNullOrWhiteSpace(text) || max <= 0)
        {
            return Array.Empty<string>();
        }

        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var result = new List<string>();
        foreach (var token in TextTokens.Split(text))
        {
            if (!HasLetterOrDigit(token))
            {
                continue;
            }

            if (seen.Add(token))
            {
                result.Add(token);
                if (result.Count >= max)
                {
                    break;
                }
            }
        }

        return result;
    }

    /// <summary>token 数 (成本口径)。</summary>
    public static int TokenCount(string text) => TextTokens.Count(text);

    private static bool HasLetterOrDigit(string token)
    {
        foreach (var ch in token)
        {
            if (char.IsLetterOrDigit(ch))
            {
                return true;
            }
        }

        return false;
    }

    /// <summary>调试用: 返回 "lang:tokens" 摘要 (无副作用, 供遥测打点)。</summary>
    public static string Describe(string text) =>
        string.Create(CultureInfo.InvariantCulture, $"{Language(text)}:{TokenCount(text)}");
}
