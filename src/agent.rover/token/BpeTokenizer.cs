using System.Security.Cryptography;
using System.Text;

namespace agent.rover.token;

/// <summary>
/// 字节级 BPE 分词器 (与 HF tokenizers 的 BPE 模型逐语义等价)。
/// 词表/合并表来源 = GGUF 内嵌 tokenizer.ggml.{tokens,token_type,merges} (权威源, 见 R400 计划 §2)。
/// 纯 BCL / 零反射 / 无 NuGet —— 与 CLI 同源编译 (agent.csproj Compile Include)。
/// 语义要点 (实测, 非文档推断):
///   ① 切分集 = added_tokens 全体 (18), 与 special 标志无关; 匹配 = 最左最长;
///   ② 合并选择 = 最小 rank 的相邻对, 一次通过合并该对全部出现 (GPT-2/HF 语义);
///   ③ 整片命中词表时直接取其 id (HF 快路径);
///   ④ 解码 = 逐 token 字符→字节, 全序列拼接后一次性 UTF-8 lossy 解码 (跨 token 多字节可复原)。
/// </summary>
public sealed class BpeTokenizer
{
    private readonly string[] _tokens;
    private readonly int[] _types;
    private readonly Dictionary<string, int> _vocab;
    private readonly Dictionary<long, Merge> _merges;
    private readonly int[] _splitIds;
    private readonly string[] _splitStrings;
    private readonly Dictionary<char, List<int>> _splitByFirst;
    private readonly HashSet<int> _specialIds;
    private readonly Dictionary<string, int[]> _pieceCache = new(StringComparer.Ordinal);
    private readonly string _mergesDigest;
    private readonly string _tokensDigest;

    public BpeTokenizer(
        IReadOnlyList<string> tokens,
        IReadOnlyList<int> types,
        IReadOnlyList<string> merges,
        IReadOnlyList<string>? splitTokens = null,
        IReadOnlyList<string>? specialTokens = null)
    {
        if (tokens.Count != types.Count)
        {
            throw new ArgumentException($"词表/类型长度不符: {tokens.Count} vs {types.Count}");
        }

        _tokens = [.. tokens];
        _types = [.. types];
        _vocab = new Dictionary<string, int>(_tokens.Length, StringComparer.Ordinal);
        for (int i = 0; i < _tokens.Length; i++)
        {
            _vocab[_tokens[i]] = i;
        }

        _merges = new Dictionary<long, Merge>(merges.Count);
        for (int rank = 0; rank < merges.Count; rank++)
        {
            string m = merges[rank];
            int sp = m.IndexOf(' ');
            if (sp <= 0 || sp == m.Length - 1)
            {
                throw new ArgumentException($"合并项格式非法 (rank {rank}): {m}");
            }

            string a = m[..sp];
            string b = m[(sp + 1)..];
            if (!_vocab.TryGetValue(a + b, out int mergedId))
            {
                throw new ArgumentException($"合并项结果不在词表: {m}");
            }

            if (!_vocab.TryGetValue(a, out int ia) || !_vocab.TryGetValue(b, out int ib))
            {
                throw new ArgumentException($"合并项操作数不在词表: {m}");
            }

            _merges[Key(ia, ib)] = new Merge(rank, mergedId);
        }

        splitTokens ??= TokenizerAssets.SplitTokens;
        specialTokens ??= TokenizerAssets.SpecialTokens;
        _splitStrings = [.. splitTokens];
        _splitIds = new int[splitTokens.Count];
        _splitByFirst = new Dictionary<char, List<int>>();
        for (int i = 0; i < splitTokens.Count; i++)
        {
            string t = splitTokens[i];
            if (t.Length == 0)
            {
                throw new ArgumentException("切分符号为空串");
            }

            if (!_vocab.TryGetValue(t, out int id))
            {
                throw new ArgumentException($"切分符号不在词表: {t}");
            }

            _splitIds[i] = id;
            if (!_splitByFirst.TryGetValue(t[0], out List<int>? lst))
            {
                lst = [];
                _splitByFirst[t[0]] = lst;
            }

            lst.Add(i);
        }

        _specialIds = [];
        foreach (string s in specialTokens)
        {
            if (_vocab.TryGetValue(s, out int id))
            {
                _specialIds.Add(id);
            }
        }

        _tokensDigest = DigestLines(_tokens);
        _mergesDigest = DigestLines(merges);

        SplitTokenCount = splitTokens.Count;
        SpecialTokenCount = specialTokens.Count;
    }

    /// <summary>切分符号个数 (随模型走, 见 TryDeriveFromTypes)。</summary>
    public int SplitCount => _splitStrings.Length;

    /// <summary>特殊符号个数 (解码时跳过)。</summary>
    public int SpecialCount => _specialIds.Count;

    /// <summary>逐行摘要: sha256(join("\n", lines)) — 与 oracle/登记表同构 (无尾随换行)。</summary>
    public static string DigestLines(IReadOnlyList<string> lines)
    {
        using IncrementalHash h = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        for (int i = 0; i < lines.Count; i++)
        {
            if (i > 0)
            {
                h.AppendData([0x0A]);
            }

            h.AppendData(System.Text.Encoding.UTF8.GetBytes(lines[i]));
        }

        return Convert.ToHexStringLower(h.GetHashAndReset());
    }

    /// <summary>词表大小 (GGUF 内嵌 = 102400)。</summary>
    public int VocabSize => _tokens.Length;

    /// <summary>合并条数 (GGUF 内嵌 = 99757)。</summary>
    public int MergeCount => _merges.Count;

    /// <summary>切分符号数 (18) / 解码跳过符号数 (3)。</summary>
    public int SplitTokenCount { get; }

    public int SpecialTokenCount { get; }

    public string TokenString(int id)
        => id >= 0 && id < _tokens.Length ? _tokens[id] : throw new ArgumentOutOfRangeException(nameof(id), id, "id 越界");

    public int TokenType(int id)
        => id >= 0 && id < _types.Length ? _types[id] : throw new ArgumentOutOfRangeException(nameof(id), id, "id 越界");

    /// <summary>合并表摘要 (UTF-8 逐行 "\n" join 后 sha256; 与 GGUF/oracle 登记对账用)。</summary>
    public string MergesSha256 => _mergesDigest;

    /// <summary>词表摘要 (UTF-8 逐行 "\n" join 后 sha256)。</summary>
    public string TokensSha256 => _tokensDigest;

    /// <summary>编码: 文本 → id 序列 (切分符号优先, 其余走 预分词 → BPE)。</summary>
    public List<int> Encode(string text)
    {
        List<int> ids = new(Math.Max(8, text.Length / 2));
        Encode(text, ids);
        return ids;
    }

    public void Encode(string text, List<int> dst)
    {
        if (string.IsNullOrEmpty(text))
        {
            return;
        }

        int i = 0;
        int last = 0;
        while (i < text.Length)
        {
            int hit = MatchSplitToken(text, i);
            if (hit < 0)
            {
                i += Pretokenizer.RuneLen(text, i);
                continue;
            }

            if (i > last)
            {
                EncodeSegment(text[last..i], dst);
            }

            dst.Add(_splitIds[hit]);
            i += _splitStrings[hit].Length;
            last = i;
        }

        if (last < text.Length)
        {
            EncodeSegment(text[last..], dst);
        }
    }

    /// <summary>解码: id 序列 → 文本 (跨 token 的多字节字符可复原)。</summary>
    public string Decode(IReadOnlyList<int> ids, bool skipSpecialTokens = true)
    {
        List<byte> bytes = new(ids.Count * 2);
        foreach (int id in ids)
        {
            if (id < 0 || id >= _tokens.Length)
            {
                throw new ArgumentOutOfRangeException(nameof(ids), id, "id 越界");
            }

            if (skipSpecialTokens && _specialIds.Contains(id))
            {
                continue;
            }

            ByteUnicode.AppendBytes(_tokens[id], bytes);
        }

        return System.Text.Encoding.UTF8.GetString(bytes.ToArray());
    }

    /// <summary>诊断: 文本 → 预分词片段 (字节级) 列表。</summary>
    public List<string> Pieces(string text) => Pretokenizer.Split(text);

    private void EncodeSegment(string segment, List<int> dst)
    {
        foreach (string piece in Pretokenizer.Split(segment))
        {
            if (_pieceCache.TryGetValue(piece, out int[]? cached))
            {
                dst.AddRange(cached);
                continue;
            }

            int[] ids = BpeEncode(piece);
            _pieceCache[piece] = ids;
            dst.AddRange(ids);
        }
    }

    private int[] BpeEncode(string piece)
    {
        if (_vocab.TryGetValue(piece, out int whole))
        {
            return [whole];
        }

        int n = piece.Length;
        int[] syms = new int[n];
        for (int i = 0; i < n; i++)
        {
            string s = piece[i].ToString();
            if (!_vocab.TryGetValue(s, out int id))
            {
                throw new InvalidOperationException($"字符不在词表: U+{(int)piece[i]:X4} (词表缺口)");
            }

            syms[i] = id;
        }

        while (syms.Length >= 2)
        {
            int bestRank = int.MaxValue;
            int bestA = -1;
            int bestB = -1;
            for (int i = 0; i + 1 < syms.Length; i++)
            {
                if (_merges.TryGetValue(Key(syms[i], syms[i + 1]), out Merge m) && m.Rank < bestRank)
                {
                    bestRank = m.Rank;
                    bestA = syms[i];
                    bestB = syms[i + 1];
                }
            }

            if (bestA < 0)
            {
                break;
            }

            int mergedId = _merges[Key(bestA, bestB)].Id;
            int[] next = new int[syms.Length];
            int w = 0;
            int r = 0;
            while (r < syms.Length)
            {
                if (r + 1 < syms.Length && syms[r] == bestA && syms[r + 1] == bestB)
                {
                    next[w++] = mergedId;
                    r += 2;
                }
                else
                {
                    next[w++] = syms[r];
                    r++;
                }
            }

            if (w == syms.Length)
            {
                break;
            }

            syms = next[..w];
        }

        return syms;
    }

    private int MatchSplitToken(string text, int i)
    {
        if (!_splitByFirst.TryGetValue(text[i], out List<int>? cands))
        {
            return -1;
        }

        int best = -1;
        int bestLen = 0;
        foreach (int idx in cands)
        {
            string t = _splitStrings[idx];
            if (t.Length > bestLen && i + t.Length <= text.Length && string.CompareOrdinal(text, i, t, 0, t.Length) == 0)
            {
                best = idx;
                bestLen = t.Length;
            }
        }

        return best;
    }

    /// <summary>
    /// 从 GGUF token_type 派生切分/特殊符号表 —— 换模型的机械口径。
    /// 规则与 R400 生成器同源: 切分集 = added_tokens 全体 ↔ 类型 {CONTROL(3), USER_DEFINED(4)};
    /// 特殊集 = special 标志 ↔ {CONTROL(3)}。
    /// 返回 false = 该模型无类型信息; 此时调用方必须用**空表**, 不得回退编译期 DeepSeek 表
    /// (那些符号不在别的词表内, 回退会直接抛 "切分符号不在词表")。
    /// </summary>
    public static bool TryDeriveFromTypes(
        IReadOnlyList<string> tokens,
        IReadOnlyList<int> types,
        out List<string> split,
        out List<string> special)
    {
        split = [];
        special = [];
        if (tokens.Count == 0 || types.Count != tokens.Count)
        {
            return false;
        }

        bool any = false;
        for (int i = 0; i < tokens.Count; i++)
        {
            int t = types[i];
            if (t is 3 or 4)
            {
                split.Add(tokens[i]);
                any = true;
                if (t == 3)
                {
                    special.Add(tokens[i]);
                }
            }
        }

        return any;
    }

    private static long Key(int a, int b) => ((long)a << 32) | (uint)b;

    private readonly struct Merge(int rank, int id)
    {
        public int Rank { get; } = rank;

        public int Id { get; } = id;
    }
}
