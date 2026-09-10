using System.Text;

namespace agent.embedcpu;

/// <summary>
/// v0.20.5 R353: BERT WordPiece tokenizer 最小实现 (词表来自 GGUF tokenizer.ggml.tokens)。
/// 贪心最长匹配 (词表已按长度排序索引); 中文按字切; [CLS]/[SEP] 包装; 512 截断。
/// 词表含 "▁" 前缀变体 (llama.cpp gguf 转 BERT 格式惯例: 空格并入前缀)。
/// </summary>
public sealed class WordPieceTokenizer
{
    // 精确匹配表 + 小写匹配表 (bge-small-zh 词表本身含小写形态)
    private readonly Dictionary<string, int> _vocab = new(StringComparer.Ordinal);
    private readonly Dictionary<string, int> _lowerVocab = new(StringComparer.Ordinal);
    private const int ClsId = 101, SepId = 102, UnkId = 100;
    public int VocabSize => _vocab.Count;

    public WordPieceTokenizer(IReadOnlyList<string> tokens)
    {
        for (var i = 0; i < tokens.Count; i++)
        {
            var t = tokens[i];
            _vocab.TryAdd(t, i);
            var lower = t.ToLowerInvariant();
            _lowerVocab.TryAdd(lower, i);
        }
        // 特殊 token id 以 GGUF kv 为准的兜底 (若词表顺序不同)
        if (!_vocab.ContainsValue(ClsId)) _vocab["[CLS]"] = ClsId;
    }

    /// <summary>文本 → token ids ([CLS] ... [SEP]), 最长 510 内容 token (512 上限)。</summary>
    public int[] Encode(string text)
    {
        var pieces = Tokenize(text);
        var ids = new List<int>(pieces.Count + 2) { ClsId };
        foreach (var p in pieces)
        {
            if (_vocab.TryGetValue(p, out var id) || _lowerVocab.TryGetValue(p.ToLowerInvariant(), out id))
                ids.Add(id);
            else
            {
                // sub-word 后备: 按 100 字符切分贪心 (WordPiece ## 前缀)
                var sub = GreedySubword(p);
                ids.AddRange(sub);
            }
            if (ids.Count >= 511) break;
        }
        ids.Add(SepId);
        return ids.ToArray();
    }

    private List<string> Tokenize(string text)
    {
        var result = new List<string>();
        text = text.Normalize(NormalizationForm.FormKC);
        var sb = new StringBuilder();
        void Flush()
        {
            if (sb.Length == 0) return;
            result.Add(sb.ToString()); // BERT WordPiece: 词无 ▁ 前缀 (sentencepiece 风格已纠正 R356)
            sb.Clear();
        }
        foreach (var ch in text)
        {
            if (char.IsWhiteSpace(ch)) { Flush(); continue; }
            if (IsCjk(ch) || IsPunct(ch)) { Flush(); result.Add(ch.ToString()); continue; }
            sb.Append(ch);
        }
        Flush();
        return result;
    }

    private List<int> GreedySubword(string word)
    {
        var ids = new List<int>();
        var start = 0;
        while (start < word.Length && ids.Count < 64)
        {
            var end = word.Length;
            int found = -1;
            string piece;
            while (end > start)
            {
                piece = (start == 0 ? "" : "##") + word[start..end];
                if (_vocab.TryGetValue(piece, out found) || _lowerVocab.TryGetValue(piece.ToLowerInvariant(), out found))
                    break;
                end--;
            }
            if (end <= start) { ids.Add(UnkId); break; }
            piece = (start == 0 ? "" : "##") + word[start..end];
            ids.Add(_vocab.TryGetValue(piece, out var a) ? a : _lowerVocab[piece.ToLowerInvariant()]);
            start = end;
        }
        return ids;
    }

    internal static bool IsCjk(char c)
        => c is >= (char)0x4E00 and <= (char)0x9FFF
            or >= (char)0x3400 and <= (char)0x4DBF
            or >= (char)0xF900 and <= (char)0xFAFF;

    internal static bool IsPunct(char c)
        => "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~　、。，！？；：（）《》「」『』【】·…—".Contains(c);
}
