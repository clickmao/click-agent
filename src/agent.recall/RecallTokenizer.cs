// R480: 独立文本召回模块 —— 分词面。
// 【语言无关令】这里没有任何文件后缀/语言标签分支: 字符类 → 切分规则全部来自
// RecallTokenizerOptions(可配置数据), 默认值只是一组「常见表意文字区间」。
using System.Text;

namespace agent.recall;

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
