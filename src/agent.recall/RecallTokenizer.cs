// R480: 独立文本召回模块 —— 分词面。
// 【语言无关令】这里没有任何文件后缀/语言标签分支: 字符类 → 切分规则全部来自
// RecallTokenizerOptions(可配置数据), 默认值只是一组「常见表意文字区间」。
using System.Text;

namespace agent.Recall;

/// <summary>半开区间 [Start, End) 的码点范围。</summary>
public readonly record struct CodepointRange(int Start, int End)
{
    public bool Contains(int cp) => cp >= Start && cp < End;
}

public sealed class RecallTokenizerOptions
{
    /// <summary>表意文字(逐字无空格分隔)区间: 命中后按 n-gram 切分。</summary>
    public IReadOnlyList<CodepointRange> IdeographicRanges { get; init; } = DefaultIdeographicRanges;

    /// <summary>表意文字的 n-gram 阶数(默认 2 = bigram)。1 表示逐字。</summary>
    public int IdeographicNgram { get; init; } = 2;

    /// <summary>是否把 ASCII 字母折成小写(仅影响 ASCII 段, 表意文字不受影响)。</summary>
    public bool LowercaseAscii { get; init; } = true;

    public int MinTokenBytes { get; init; } = 1;
    public int MaxTokenBytes { get; init; } = 96;
    public int MaxTokensPerDoc { get; init; } = 8192;

    /// <summary>算作词内字符的符号。点号被排除: R481-B 统计判定 (n=300 真实查询, hit@5 差异 +0.67pt / p=0.856 不显著,
    /// 而查询词数 -16.05%、postings -0.254% 更低) ⇒ 质量无显著差异时取成本更低者。语言无关: 该集合是配置数据, 不含任何后缀语义。</summary>
    public string WordSymbols { get; init; } = "_/+#";

    /// <summary>n-gram 环形缓冲的最大阶数(超过的阶数一律按此上限截断)。</summary>
    internal const int MaxNgramOrder = 4;

    public static readonly IReadOnlyList<CodepointRange> DefaultIdeographicRanges = new[]
    {
        new CodepointRange(0x3040, 0x30FF),   // 假名
        new CodepointRange(0x3400, 0x4DBF),   // 扩展 A
        new CodepointRange(0x4E00, 0x9FFF),   // 基本区
        new CodepointRange(0xAC00, 0xD7AF),   // 谚文音节
        new CodepointRange(0xF900, 0xFAFF),   // 兼容表意
        new CodepointRange(0x20000, 0x2FA1F), // 扩展 B..F (代理对)
    };

    public static RecallTokenizerOptions Default { get; } = new();

    internal bool IsIdeographic(int cp)
    {
        for (int i = 0; i < IdeographicRanges.Count; i++)
        {
            if (IdeographicRanges[i].Contains(cp))
            {
                return true;
            }
        }
        return false;
    }

    internal bool IsWordSymbol(char c)
    {
        for (int i = 0; i < WordSymbols.Length; i++)
        {
            if (WordSymbols[i] == c)
            {
                return true;
            }
        }
        return false;
    }
}

public interface ITokenSink
{
    void AddToken(ReadOnlySpan<byte> utf8);
}

/// <summary>确定性分词器: 同一输入 + 同一 options ⇒ 逐字节相同的 token 序列 (无随机化/无区域设置依赖)。</summary>
public static class RecallTokenizer
{
    public static void Tokenize(string text, RecallTokenizerOptions options, ITokenSink sink)
        => Tokenize(text.AsSpan(), options, sink);

    public static void Tokenize(ReadOnlySpan<char> text, RecallTokenizerOptions options, ITokenSink sink)
    {
        ArgumentNullException.ThrowIfNull(options);
        ArgumentNullException.ThrowIfNull(sink);

        int ngram = options.IdeographicNgram;
        if (ngram < 1)
        {
            ngram = 1;
        }
        if (ngram > RecallTokenizerOptions.MaxNgramOrder)
        {
            ngram = RecallTokenizerOptions.MaxNgramOrder;
        }

        Span<byte> utf8 = stackalloc byte[8];
        Span<byte> ring = stackalloc byte[RecallTokenizerOptions.MaxNgramOrder * 8];
        Span<int> ringOff = stackalloc int[RecallTokenizerOptions.MaxNgramOrder];
        Span<int> ringLen = stackalloc int[RecallTokenizerOptions.MaxNgramOrder];
        Span<byte> token = stackalloc byte[RecallTokenizerOptions.MaxNgramOrder * 8];
        int ringCount = 0;
        int runLen = 0;
        int emitted = 0;

        void FlushShortRun(ReadOnlySpan<byte> ringBuf, Span<int> offBuf, Span<int> lenBuf, Span<byte> tok)
        {
            if (runLen > 0 && runLen < ngram)
            {
                int total = 0;
                int first = ringCount - runLen;
                for (int k = 0; k < runLen; k++)
                {
                    int s = (first + k) % RecallTokenizerOptions.MaxNgramOrder;
                    ringBuf.Slice(offBuf[s], lenBuf[s]).CopyTo(tok.Slice(total));
                    total += lenBuf[s];
                }
                if (total >= options.MinTokenBytes && total <= options.MaxTokenBytes && emitted < options.MaxTokensPerDoc)
                {
                    sink.AddToken(tok.Slice(0, total));
                    emitted++;
                }
            }
            runLen = 0;
            ringCount = 0;
        }

        int i = 0;
        while (i < text.Length)
        {
            char c = text[i];

            if (c >= 0x80)
            {
                int cp;
                int charLen;
                if (char.IsHighSurrogate(c) && i + 1 < text.Length && char.IsLowSurrogate(text[i + 1]))
                {
                    cp = char.ConvertToUtf32(c, text[i + 1]);
                    charLen = 2;
                }
                else if (char.IsSurrogate(c))
                {
                    cp = -1; // 落单代理: 一律当分隔符, 不产生 token
                    charLen = 1;
                }
                else
                {
                    cp = c;
                    charLen = 1;
                }

                if (cp >= 0 && options.IsIdeographic(cp))
                {
                    int n = Encoding.UTF8.GetBytes(text.Slice(i, charLen), utf8);
                    int slot = ringCount % RecallTokenizerOptions.MaxNgramOrder;
                    ringOff[slot] = slot * 8;
                    ringLen[slot] = n;
                    utf8.Slice(0, n).CopyTo(ring.Slice(slot * 8));
                    ringCount++;
                    runLen++;

                    if (ringCount >= ngram)
                    {
                        int total = 0;
                        int start = ringCount - ngram;
                        for (int k = 0; k < ngram; k++)
                        {
                            int s = (start + k) % RecallTokenizerOptions.MaxNgramOrder;
                            ring.Slice(ringOff[s], ringLen[s]).CopyTo(token.Slice(total));
                            total += ringLen[s];
                        }
                        if (total >= options.MinTokenBytes && total <= options.MaxTokenBytes)
                        {
                            sink.AddToken(token.Slice(0, total));
                            emitted++;
                            if (emitted >= options.MaxTokensPerDoc)
                            {
                                return;
                            }
                        }
                    }
                    i += charLen;
                    continue;
                }

                FlushShortRun(ring, ringOff, ringLen, token);
                i += charLen;
                continue;
            }

            if (IsAsciiWordChar(c, options))
            {
                FlushShortRun(ring, ringOff, ringLen, token);
                int start = i;
                while (i < text.Length && text[i] < 0x80 && IsAsciiWordChar(text[i], options))
                {
                    i++;
                }
                var run = text.Slice(start, i - start);
                int len = run.Length > 256 ? 256 : run.Length;
                for (int k = 0; k < len; k++)
                {
                    char ch = run[k];
                    token[k] = options.LowercaseAscii && ch >= 'A' && ch <= 'Z' ? (byte)(ch + 32) : (byte)ch;
                }
                if (len >= options.MinTokenBytes && len <= options.MaxTokenBytes)
                {
                    sink.AddToken(token.Slice(0, len));
                    emitted++;
                    if (emitted >= options.MaxTokensPerDoc)
                    {
                        return;
                    }
                }
                continue;
            }

            FlushShortRun(ring, ringOff, ringLen, token);
            i++;
        }

        FlushShortRun(ring, ringOff, ringLen, token);
    }

    private static bool IsAsciiWordChar(char c, RecallTokenizerOptions options)
        => (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || options.IsWordSymbol(c);

    /// <summary>确定性 token 哈希 (FNV-1a 64): term → 64 位键, 跨进程/跨运行稳定。</summary>
    public static ulong Hash(ReadOnlySpan<byte> utf8)
    {
        ulong h = 14695981039346656037UL;
        for (int i = 0; i < utf8.Length; i++)
        {
            h ^= utf8[i];
            h *= 1099511628211UL;
        }
        return h;
    }
}
