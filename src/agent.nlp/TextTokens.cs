using Microsoft.ML.Tokenizers;

namespace agent.nlp;

/// <summary>
/// 分词 — Microsoft.ML.Tokenizers 2.0.0 (o200k_base 多语言 BPE, 200k 词表, 覆盖 CJK/西里尔/阿拉伯/天城文等)。
/// 取代「字符集切分 + 停用词表 + 4-gram 重叠」这一整族自研词面逻辑。
/// AOT: 官方已修 AOT (dotnet/machinelearning #7272); env -i 下 NativeAOT 实测可用 (含离线词表数据包, 无运行期下载)。
/// </summary>
public static class TextTokens
{
    private static readonly Lazy<Tokenizer> LazyTokenizer =
        new(() => TiktokenTokenizer.CreateForEncoding("o200k_base"));

    public static Tokenizer Tokenizer => LazyTokenizer.Value;

    /// <summary>token 数 (成本口径, 替代「字符数」估算)。</summary>
    public static int Count(string text) =>
        string.IsNullOrEmpty(text) ? 0 : Tokenizer.CountTokens(text);

    /// <summary>切成 token 字符串 (保留原始片段, 不做语言假设)。</summary>
    public static IReadOnlyList<string> Split(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
        {
            return Array.Empty<string>();
        }

        var encoded = Tokenizer.EncodeToTokens(text, out _, false, false);
        var list = new List<string>(encoded.Count);
        foreach (var token in encoded)
        {
            if (!string.IsNullOrEmpty(token.Value))
            {
                list.Add(token.Value);
            }
        }

        return list;
    }
}
