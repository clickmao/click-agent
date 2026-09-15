// R480: 独立文本召回模块 —— 产出物自带地址 (链接面)。
// 用户令: 「跨文件跨url相当于不需要主动分类, 但自己就包含了链接指向…唯一的问题就是需要内容中自带链接地址或文件地址」
// 因此本文件只做一件事: 把正文里**已经存在**的地址抽出来随文档落盘 ⇒ 召回不需要分类, 只需要沿地址走。
// 语言无关: 链接语法全部来自 RecallLinkOptions(可配置), 不做任何文件后缀判断。
using System.Buffers.Binary;
using System.Text;

namespace agent.Recall;

public sealed class RecallLinkOptions
{
    public bool MarkdownTargets { get; init; } = true;
    public bool BareUrls { get; init; } = true;
    public bool RelativeAddresses { get; init; } = true;
    public int MaxLinksPerDoc { get; init; } = 64;
    public int MaxLinkChars { get; init; } = 512;
    public string[] Schemes { get; init; } = { "http://", "https://" };

    public static RecallLinkOptions Default { get; } = new();
}

public static class RecallLinkExtractor
{
    /// <summary>抽取正文中已有的地址 (markdown 目标 / 裸 URL / 相对地址), 去重保序, 受上限约束。</summary>
    public static int Extract(ReadOnlySpan<char> text, RecallLinkOptions options, List<string> sink)
    {
        sink.Clear();
        if (text.IsEmpty || options.MaxLinksPerDoc <= 0)
        {
            return 0;
        }
        var seen = new HashSet<string>(StringComparer.Ordinal);
        var buf = new StringBuilder(256);
        for (int i = 0; i < text.Length && sink.Count < options.MaxLinksPerDoc; i++)
        {
            char c = text[i];
            if (options.MarkdownTargets && c == ']' && i + 1 < text.Length && text[i + 1] == '(')
            {
                if (TryReadUntil(text, i + 2, ')', buf, options.MaxLinkChars) && Accept(buf.ToString(), options, out string md))
                {
                    AddIfNew(sink, seen, md, options);
                }
                continue;
            }
            if (options.BareUrls && IsSchemeStart(text, i, options.Schemes))
            {
                if (TryReadRun(text, i, buf, options.MaxLinkChars))
                {
                    string raw = TrimTrailingPunctuation(buf.ToString());
                    if (Accept(raw, options, out string url))
                    {
                        AddIfNew(sink, seen, url, options);
                    }
                }
                continue;
            }
        }
        if (options.RelativeAddresses)
        {
            ExtractRelative(text, options, sink, seen);
        }
        return sink.Count;
    }

    private static void ExtractRelative(ReadOnlySpan<char> text, RecallLinkOptions options, List<string> sink, HashSet<string> seen)
    {
        int i = 0;
        while (i < text.Length && sink.Count < options.MaxLinksPerDoc)
        {
            if (!IsAddressChar(text[i]))
            {
                i++;
                continue;
            }
            int start = i;
            while (i < text.Length && IsAddressChar(text[i]))
            {
                i++;
            }
            int len = i - start;
            if (len < 3 || len > options.MaxLinkChars)
            {
                continue;
            }
            var slice = text.Slice(start, len);
            if (slice.IndexOf('/') < 0)
            {
                continue;
            }
            string candidate = TrimTrailingPunctuation(slice.ToString());
            if (Accept(candidate, options, out string rel))
            {
                AddIfNew(sink, seen, rel, options);
            }
        }
    }

    private static bool IsAddressChar(char c) =>
        char.IsLetterOrDigit(c) || c == '/' || c == '.' || c == '-' || c == '_' || c == '~' || c == '#' || c == ':' || c == '@' || c == '%' || c == '+' || c == '=' || c == '&' || c == '?' || c == '!';

    private static bool IsSchemeStart(ReadOnlySpan<char> text, int i, string[] schemes)
    {
        foreach (string s in schemes)
        {
            if (i + s.Length <= text.Length && text.Slice(i, s.Length).SequenceEqual(s.AsSpan()))
            {
                return true;
            }
        }
        return false;
    }

    private static bool TryReadUntil(ReadOnlySpan<char> text, int start, char terminator, StringBuilder buf, int max)
    {
        buf.Clear();
        for (int i = start; i < text.Length && buf.Length < max; i++)
        {
            if (text[i] == terminator)
            {
                return buf.Length > 0;
            }
            buf.Append(text[i]);
        }
        return false;
    }

    private static bool TryReadRun(ReadOnlySpan<char> text, int start, StringBuilder buf, int max)
    {
        buf.Clear();
        int i = start;
        while (i < text.Length && buf.Length < max && (IsAddressChar(text[i]) || text[i] == '%'))
        {
            buf.Append(text[i]);
            i++;
        }
        return buf.Length > 0;
    }

    private static string TrimTrailingPunctuation(string s)
    {
        int end = s.Length;
        while (end > 0)
        {
            char c = s[end - 1];
            if (c == '.' || c == ',' || c == ';' || c == ':' || c == ')' || c == '"' || c == '\'' || c == ']')
            {
                end--;
            }
            else
            {
                break;
            }
        }
        return end == s.Length ? s : s[..end];
    }

    private static bool Accept(string candidate, RecallLinkOptions options, out string normalized)
    {
        normalized = candidate.Trim();
        if (normalized.Length == 0 || normalized.Length > options.MaxLinkChars)
        {
            return false;
        }
        foreach (string s in options.Schemes)
        {
            if (normalized.StartsWith(s, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }
        // 相对地址: 必须含 '/' 且不含空白 (结构性判据, 与后缀无关)
        if (normalized.Contains('/') && !normalized.Any(char.IsWhiteSpace))
        {
            return true;
        }
        return false;
    }

    private static void AddIfNew(List<string> sink, HashSet<string> seen, string value, RecallLinkOptions options)
    {
        if (sink.Count >= options.MaxLinksPerDoc)
        {
            return;
        }
        if (seen.Add(value))
        {
            sink.Add(value);
        }
    }
}

/// <summary>段内链接表 (按 docId 定址, pread 按需读; 常驻只有偏移表长度信息, 不载入链接内容)。</summary>
public static class RecallLinksFile
{
    public static void Write(string segmentDir, IReadOnlyList<List<string>> perDoc)
    {
        string path = Path.Combine(segmentDir, RecallConstants.LinksFile);
        using var fs = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.None);
        fs.Write(RecallConstants.LinksMagic);
        Span<byte> tmp = stackalloc byte[8];
        BinaryPrimitives.WriteInt32LittleEndian(tmp, perDoc.Count);
        fs.Write(tmp[..4]);
        long headerEnd = 8 + 4 + (long)(perDoc.Count + 1) * 8;
        var offsets = new long[perDoc.Count + 1];
        long cursor = headerEnd;
        for (int i = 0; i < perDoc.Count; i++)
        {
            offsets[i] = cursor;
            cursor += Measure(perDoc[i]);
        }
        offsets[perDoc.Count] = cursor;
        for (int i = 0; i < offsets.Length; i++)
        {
            BinaryPrimitives.WriteInt64LittleEndian(tmp, offsets[i]);
            fs.Write(tmp);
        }
        for (int i = 0; i < perDoc.Count; i++)
        {
            var buf = new ByteBuffer(64);
            buf.WriteVarInt((ulong)perDoc[i].Count);
            fs.Write(buf.Span);
            foreach (string link in perDoc[i])
            {
                byte[] bytes = Encoding.UTF8.GetBytes(link);
                var lb = new ByteBuffer(16);
                lb.WriteVarInt((ulong)bytes.Length);
                fs.Write(lb.Span);
                fs.Write(bytes);
            }
        }
    }

    private static long Measure(List<string> links)
    {
        long n = VarInt.Size((ulong)links.Count);
        foreach (string link in links)
        {
            int len = Encoding.UTF8.GetByteCount(link);
            n += VarInt.Size((ulong)len) + len;
        }
        return n;
    }

    public static bool Exists(string segmentDir) => File.Exists(Path.Combine(segmentDir, RecallConstants.LinksFile));

    /// <summary>读取单篇文档的地址列表 (一次 pread 取偏移 + 一次 pread 取记录)。</summary>
    public static List<string> Read(string segmentDir, RecallFile file, int docId, int docCount, RecallReadStats? stats)
    {
        var result = new List<string>();
        if (docId < 0 || docId >= docCount)
        {
            return result;
        }
        Span<byte> span = stackalloc byte[8];
        file.ReadExactly(12 + (long)docId * 8, span);
        long start = BinaryPrimitives.ReadInt64LittleEndian(span);
        file.ReadExactly(12 + (long)(docId + 1) * 8, span);
        long end = BinaryPrimitives.ReadInt64LittleEndian(span);
        if (end <= start || end - start > 1_000_000)
        {
            return result;
        }
        byte[] payload = file.ReadBytes(start, (int)(end - start));
        int p = 0;
        int used = VarInt.Read(payload.AsSpan(), out ulong linkCount);
        if (used == 0)
        {
            throw new RecallCorruptionException($"links record header truncated at doc {docId} in {segmentDir}");
        }
        p += used;
        for (ulong i = 0; i < linkCount && p < payload.Length; i++)
        {
            p += VarInt.Read(payload.AsSpan(p), out ulong len);
            if (p + (int)len > payload.Length)
            {
                throw new RecallCorruptionException($"links record truncated at doc {docId} in {segmentDir}");
            }
            result.Add(Encoding.UTF8.GetString(payload, p, (int)len));
            p += (int)len;
        }
        stats?.CountRead(payload.Length);
        return result;
    }
}
