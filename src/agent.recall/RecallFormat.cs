// R480: 独立文本召回模块 —— 磁盘格式定义 (单一定义处: 写侧/读侧都从这里取常量)。
namespace agent.Recall;

internal static class RecallConstants
{
    public const int Version = 1;
    public const int PostingBlockDocs = 128;   // 块 = block-max WAND 的跳过单位
    public const int TermTopStride = 1024;     // 词表二级跳表粒度 (常驻面 O(termCount/stride))
    public const double Bm25K1 = 1.2;
    public const double Bm25B = 0.75;

    public const string SegmentFile = "seg.meta";
    public const string TermsFile = "terms.bin";
    public const string PostingsFile = "postings.bin";
    public const string DocsFile = "docs.bin";
    public const string DocsLenFile = "lens.bin";
    public const string TextFile = "text.bin";
    public const string TombFile = "tomb.bin";
    public const string IndexMetaFile = "index.meta";
    public const string FingerprintFile = "fingerprints.bin";
    public const string SegmentPrefix = "seg_";

    public static ReadOnlySpan<byte> IndexMagic => "ARECIDX1"u8;
    public static ReadOnlySpan<byte> SegmentMagic => "ARECSEG1"u8;
    public static ReadOnlySpan<byte> DocsMagic => "ARECDOC1"u8;
    public static ReadOnlySpan<byte> LensMagic => "ARECLEN1"u8;
    public static ReadOnlySpan<byte> TombMagic => "ARECTOM1"u8;
    public static ReadOnlySpan<byte> FpMagic => "ARECFP01"u8;
    public static ReadOnlySpan<byte> LinksMagic => "ARECLNK1"u8;
    public const string LinksFile = "links.bin";
}

/// <summary>词表二级跳表条目: 常驻内存的只有这些 (每 stride 个 term 一条)。</summary>
public sealed class RecallTermTop
{
    public required long Offset { get; init; }
    public required byte[] Term { get; init; }
}

public sealed class RecallSegmentMeta
{
    public required string Directory { get; init; }
    public required int DocCount { get; init; }
    public required int TermCount { get; init; }
    public required double AvgDocLen { get; init; }
    public required int BlockSize { get; init; }
    public required int TermTopStride { get; init; }
    public required long TermsLength { get; init; }
    public required long PostingsLength { get; init; }
    public required long DocsLength { get; init; }
    public required long TextLength { get; init; }
    public required IReadOnlyList<RecallTermTop> TermTops { get; init; }

    public long ResidentBytes
    {
        get
        {
            long t = 0;
            for (int i = 0; i < TermTops.Count; i++)
            {
                t += 16 + TermTops[i].Term.Length;
            }
            return t;
        }
    }

    private static bool TryVar(ReadOnlySpan<byte> sp, ref int p, out ulong value)
    {
        value = 0;
        if (p >= sp.Length)
        {
            return false;
        }
        int n = VarInt.Read(sp[p..], out value);
        if (n == 0)
        {
            return false;
        }
        p += n;
        return true;
    }

    public static RecallSegmentMeta Read(RecallFile file)
    {
        long length = file.Length;
        if (length < 8 + 4)
        {
            throw new RecallFormatException($"segment meta too small: {file.Path}");
        }
        int headLen = (int)Math.Min(length, 64 * 1024);
        var head = file.ReadBytes(0, headLen);
        var span = head.AsSpan();
        if (!span[..8].SequenceEqual(RecallConstants.SegmentMagic))
        {
            throw new RecallFormatException($"bad segment magic: {file.Path}");
        }
        int p = 8;
        if (VarInt.Read(span[p..], out ulong version) == 0 || version != RecallConstants.Version)
        {
            throw new RecallFormatException($"unsupported segment version in {file.Path}");
        }
        p += VarInt.Size(version);
        if (!TryVar(span, ref p, out ulong docCount) || !TryVar(span, ref p, out ulong termCount) || p + 8 > head.Length)
        {
            throw new RecallFormatException($"truncated segment meta: {file.Path}");
        }
        p += ReadDouble(span[p..], out double avgDocLen);
        if (!TryVar(span, ref p, out ulong blockSize) || !TryVar(span, ref p, out ulong stride) ||
            !TryVar(span, ref p, out ulong termsLen) || !TryVar(span, ref p, out ulong postingsLen) ||
            !TryVar(span, ref p, out ulong docsLen) || !TryVar(span, ref p, out ulong textLen) ||
            !TryVar(span, ref p, out ulong topCount))
        {
            throw new RecallFormatException($"truncated segment meta: {file.Path}");
        }
        if (docCount > int.MaxValue || termCount > int.MaxValue || topCount > 1_000_000)
        {
            throw new RecallFormatException($"corrupt segment meta: {file.Path}");
        }
        if (blockSize == 0 || blockSize > (1UL << 24) || stride == 0 || stride > (1UL << 24) || topCount > termCount + 1)
        {
            throw new RecallFormatException($"corrupt segment meta: {file.Path}");
        }
        var tops = new List<RecallTermTop>((int)topCount);
        for (ulong i = 0; i < topCount; i++)
        {
            if (p + 8 > head.Length)
            {
                throw new RecallFormatException($"truncated term tops in {file.Path}");
            }
            p += ReadInt64(span[p..], out long offset);
            int used = VarInt.Read(span[p..], out ulong tl);
            if (used == 0 || tl > 1024)
            {
                throw new RecallFormatException($"bad term top length in {file.Path}");
            }
            p += used;
            if (p + (int)tl > head.Length)
            {
                throw new RecallFormatException($"term top out of window in {file.Path}");
            }
            tops.Add(new RecallTermTop { Offset = offset, Term = head.AsSpan(p, (int)tl).ToArray() });
            p += (int)tl;
        }
        return new RecallSegmentMeta
        {
            Directory = System.IO.Path.GetDirectoryName(file.Path) ?? string.Empty,
            DocCount = (int)docCount,
            TermCount = (int)termCount,
            AvgDocLen = avgDocLen,
            BlockSize = (int)blockSize,
            TermTopStride = (int)stride,
            TermsLength = (long)termsLen,
            PostingsLength = (long)postingsLen,
            DocsLength = (long)docsLen,
            TextLength = (long)textLen,
            TermTops = tops,
        };
    }

    internal static int ReadInt64(ReadOnlySpan<byte> span, out long value)
    {
        if (span.Length < 8)
        {
            value = 0;
            return 0;
        }
        value = System.Buffers.Binary.BinaryPrimitives.ReadInt64LittleEndian(span);
        return 8;
    }

    internal static int ReadDouble(ReadOnlySpan<byte> span, out double value)
    {
        if (span.Length < 8)
        {
            value = 0;
            return 0;
        }
        value = BitConverter.Int64BitsToDouble(System.Buffers.Binary.BinaryPrimitives.ReadInt64LittleEndian(span));
        return 8;
    }
}

/// <summary>索引级元数据: BM25 参数 + 分词参数(读写必须同参, 否则查询侧切词与索引侧不一致)。</summary>
public sealed class RecallIndexMeta
{
    public required double K1 { get; init; }
    public required double B { get; init; }
    public required RecallTokenizerOptions Tokenizer { get; init; }
    public required IReadOnlyList<RecallSegmentRef> Segments { get; init; }

    public int TotalDocs
    {
        get
        {
            int t = 0;
            for (int i = 0; i < Segments.Count; i++)
            {
                t += Segments[i].DocCount;
            }
            return t;
        }
    }

    public static RecallIndexMeta Read(RecallFile file)
    {
        var head = file.ReadBytes(0, (int)Math.Min(file.Length, 256 * 1024));
        var span = head.AsSpan();
        if (span.Length < 8 || !span[..8].SequenceEqual(RecallConstants.IndexMagic))
        {
            throw new RecallFormatException($"bad index magic: {file.Path}");
        }
        int p = 8;
        int used = VarInt.Read(span[p..], out ulong version);
        if (used == 0 || version != RecallConstants.Version)
        {
            throw new RecallFormatException($"unsupported index version: {file.Path}");
        }
        p += used;
        if (p + 16 > head.Length)
        {
            throw new RecallFormatException("truncated index meta");
        }
        p += RecallSegmentMeta.ReadDouble(span[p..], out double k1);
        p += RecallSegmentMeta.ReadDouble(span[p..], out double b);
        if (!TryVar(span, ref p, out ulong ngram) || p >= head.Length)
        {
            throw new RecallFormatException("truncated index meta");
        }
        bool lower = span[p] != 0;
        p++;
        if (!TryVar(span, ref p, out ulong minTok) || !TryVar(span, ref p, out ulong maxTok) ||
            !TryVar(span, ref p, out ulong maxTokens) || !TryVar(span, ref p, out ulong rangeCount))
        {
            throw new RecallFormatException("truncated index meta");
        }
        // fail-closed: 计数一律先验界, 再分配 (损坏的 meta 必须抛 RecallFormatException, 绝不允许按垃圾计数跑循环)
        if (rangeCount > 4096 || p + (long)rangeCount * 2 > head.Length)
        {
            throw new RecallFormatException("corrupt index meta: range count");
        }
        var ranges = new List<CodepointRange>((int)rangeCount);
        for (ulong i = 0; i < rangeCount; i++)
        {
            if (!TryVar(span, ref p, out ulong rs) || !TryVar(span, ref p, out ulong re) || rs > 0x10FFFF || re > 0x10FFFF)
            {
                throw new RecallFormatException("corrupt index meta: codepoint range");
            }
            ranges.Add(new CodepointRange((int)rs, (int)re));
        }
        if (!TryVar(span, ref p, out ulong segCount) || segCount > 65536)
        {
            throw new RecallFormatException("corrupt index meta: segment count");
        }
        var segs = new List<RecallSegmentRef>((int)segCount);
        for (ulong i = 0; i < segCount; i++)
        {
            if (!TryVar(span, ref p, out ulong nameLen) || nameLen > (ulong)(head.Length - p) || p >= head.Length)
            {
                throw new RecallFormatException("corrupt index meta: segment name");
            }
            string name = System.Text.Encoding.UTF8.GetString(span.Slice(p, (int)nameLen));
            p += (int)nameLen;
            if (!TryVar(span, ref p, out ulong docs) || !TryVar(span, ref p, out ulong tomb) || docs > int.MaxValue)
            {
                throw new RecallFormatException("corrupt index meta: segment stat");
            }
            segs.Add(new RecallSegmentRef { Name = name, DocCount = (int)docs, TombstoneCount = (int)tomb });
        }
        return new RecallIndexMeta
        {
            K1 = k1,
            B = b,
            Tokenizer = new RecallTokenizerOptions
            {
                IdeographicNgram = (int)ngram,
                LowercaseAscii = lower,
                MinTokenBytes = (int)minTok,
                MaxTokenBytes = (int)maxTok,
                MaxTokensPerDoc = (int)maxTokens,
                IdeographicRanges = ranges,
            },
            Segments = segs,
        };
    }

    private static bool TryVar(ReadOnlySpan<byte> sp, ref int p, out ulong value)
    {
        value = 0;
        if (p >= sp.Length)
        {
            return false;
        }
        int n = VarInt.Read(sp[p..], out value);
        if (n == 0)
        {
            return false;
        }
        p += n;
        return true;
    }

    public void Write(Stream s)
    {
        s.Write(RecallConstants.IndexMagic);
        WriteVar(s, (ulong)RecallConstants.Version);
        WriteDouble(s, K1);
        WriteDouble(s, B);
        WriteVar(s, (ulong)Tokenizer.IdeographicNgram);
        s.WriteByte(Tokenizer.LowercaseAscii ? (byte)1 : (byte)0);
        WriteVar(s, (ulong)Tokenizer.MinTokenBytes);
        WriteVar(s, (ulong)Tokenizer.MaxTokenBytes);
        WriteVar(s, (ulong)Tokenizer.MaxTokensPerDoc);
        WriteVar(s, (ulong)Tokenizer.IdeographicRanges.Count);
        for (int i = 0; i < Tokenizer.IdeographicRanges.Count; i++)
        {
            WriteVar(s, (ulong)Tokenizer.IdeographicRanges[i].Start);
            WriteVar(s, (ulong)Tokenizer.IdeographicRanges[i].End);
        }
        WriteVar(s, (ulong)Segments.Count);
        for (int i = 0; i < Segments.Count; i++)
        {
            var bytes = System.Text.Encoding.UTF8.GetBytes(Segments[i].Name);
            WriteVar(s, (ulong)bytes.Length);
            s.Write(bytes);
            WriteVar(s, (ulong)Segments[i].DocCount);
            WriteVar(s, (ulong)Segments[i].TombstoneCount);
        }
    }

    internal static void WriteVar(Stream s, ulong v) => VarInt.WriteTo(s, v);

    internal static void WriteInt64(Stream s, long v)
    {
        Span<byte> tmp = stackalloc byte[8];
        System.Buffers.Binary.BinaryPrimitives.WriteInt64LittleEndian(tmp, v);
        s.Write(tmp);
    }

    internal static void WriteDouble(Stream s, double v)
    {
        Span<byte> tmp = stackalloc byte[8];
        System.Buffers.Binary.BinaryPrimitives.WriteInt64LittleEndian(tmp, BitConverter.DoubleToInt64Bits(v));
        s.Write(tmp);
    }
}

public sealed class RecallSegmentRef
{
    public required string Name { get; init; }
    public required int DocCount { get; init; }
    public int TombstoneCount { get; set; }
}

/// <summary>docs.bin: 头部 i64 偏移表 + 变长文档记录 (记录本体按需 pread, 不常驻)。</summary>
public sealed class RecallDocsReader : IDisposable
{
    private readonly RecallFile _file;
    private readonly RecallFile _lens;
    public int DocCount { get; }

    public RecallDocsReader(string segmentDir, RecallReadStats? stats)
    {
        _file = new RecallFile(System.IO.Path.Combine(segmentDir, RecallConstants.DocsFile), stats);
        _lens = new RecallFile(System.IO.Path.Combine(segmentDir, RecallConstants.DocsLenFile), stats);
        var head = _file.ReadBytes(0, 12);
        if (!head.AsSpan(0, 8).SequenceEqual(RecallConstants.DocsMagic))
        {
            throw new RecallFormatException($"bad docs magic: {segmentDir}");
        }
        DocCount = System.Buffers.Binary.BinaryPrimitives.ReadInt32LittleEndian(head.AsSpan(8, 4));
        var lhead = _lens.ReadBytes(0, 8);
        if (!lhead.AsSpan(0, 8).SequenceEqual(RecallConstants.LensMagic))
        {
            throw new RecallFormatException($"bad lens magic: {segmentDir}");
        }
    }

    public int DocLength(int docId)
    {
        if (docId < 0 || docId >= DocCount)
        {
            throw new RecallCorruptionException($"docId out of range: {docId}/{DocCount}");
        }
        Span<byte> buf = stackalloc byte[4];
        _lens.ReadExactly(12 + docId * 4L, buf);
        return System.Buffers.Binary.BinaryPrimitives.ReadInt32LittleEndian(buf);
    }

    public RecallDocRecord Read(int docId)
    {
        if (docId < 0 || docId >= DocCount)
        {
            throw new RecallCorruptionException($"docId out of range: {docId}/{DocCount}");
        }
        Span<byte> off = stackalloc byte[16];
        _file.ReadExactly(12 + docId * 8L, off);
        long start = System.Buffers.Binary.BinaryPrimitives.ReadInt64LittleEndian(off[..8]);
        long end = System.Buffers.Binary.BinaryPrimitives.ReadInt64LittleEndian(off[8..]);
        if (end <= start || end - start > 1 << 20)
        {
            throw new RecallCorruptionException($"bad doc record bounds: doc={docId} [{start},{end})");
        }
        var rec = _file.ReadBytes(start, (int)(end - start));
        return RecallDocRecord.Decode(rec);
    }

    public void Dispose()
    {
        _file.Dispose();
        _lens.Dispose();
    }
}

public sealed class RecallDocRecord
{
    public required int DocId { get; init; }
    public required string Id { get; init; }
    public required string Path { get; init; }
    public required long TextOffset { get; init; }
    public required int TextLength { get; init; }
    public required int DocLenTokens { get; init; }
    public required long Size { get; init; }
    public required long MtimeTicks { get; init; }
    public required long Inode { get; init; }

    public byte[] Encode()
    {
        var buf = new ByteBuffer(64 + Id.Length + Path.Length);
        var idBytes = System.Text.Encoding.UTF8.GetBytes(Id);
        var pathBytes = System.Text.Encoding.UTF8.GetBytes(Path);
        buf.WriteVarInt((ulong)idBytes.Length);
        buf.Write(idBytes);
        buf.WriteVarInt((ulong)pathBytes.Length);
        buf.Write(pathBytes);
        buf.WriteVarInt((ulong)TextOffset);
        buf.WriteVarInt((ulong)TextLength);
        buf.WriteVarInt((ulong)DocLenTokens);
        buf.WriteVarInt((ulong)Math.Max(0, Size));
        buf.WriteVarInt((ulong)Math.Max(0, MtimeTicks));
        buf.WriteVarInt((ulong)Math.Max(0, Inode));
        return buf.Span.ToArray();
    }

    public static RecallDocRecord Decode(ReadOnlySpan<byte> src)
    {
        int p = 0;
        int used = VarInt.Read(src[p..], out ulong idLen);
        p += used;
        string id = System.Text.Encoding.UTF8.GetString(src.Slice(p, (int)idLen));
        p += (int)idLen;
        used = VarInt.Read(src[p..], out ulong pathLen);
        p += used;
        string path = System.Text.Encoding.UTF8.GetString(src.Slice(p, (int)pathLen));
        p += (int)pathLen;
        p += VarInt.Read(src[p..], out ulong textOffset);
        p += VarInt.Read(src[p..], out ulong textLen);
        p += VarInt.Read(src[p..], out ulong docLen);
        p += VarInt.Read(src[p..], out ulong size);
        p += VarInt.Read(src[p..], out ulong mtime);
        p += VarInt.Read(src[p..], out ulong inode);
        return new RecallDocRecord
        {
            DocId = 0,
            Id = id,
            Path = path,
            TextOffset = (long)textOffset,
            TextLength = (int)textLen,
            DocLenTokens = (int)docLen,
            Size = (long)size,
            MtimeTicks = (long)mtime,
            Inode = (long)inode,
        };
    }
}

/// <summary>tomb.bin: 已删 docId 的有序列表 (段内可见性过滤, 避免为一次删除重写整段)。</summary>
public static class RecallTombstones
{
    public static int[] Read(string segmentDir, RecallReadStats? stats = null)
    {
        string path = System.IO.Path.Combine(segmentDir, RecallConstants.TombFile);
        if (!File.Exists(path))
        {
            return Array.Empty<int>();
        }
        using var f = new RecallFile(path, stats);
        var head = f.ReadBytes(0, 12);
        if (!head.AsSpan(0, 8).SequenceEqual(RecallConstants.TombMagic))
        {
            throw new RecallFormatException($"bad tombstone magic: {path}");
        }
        int count = System.Buffers.Binary.BinaryPrimitives.ReadInt32LittleEndian(head.AsSpan(8, 4));
        var body = f.ReadBytes(12, (int)Math.Max(0, f.Length - 12));
        var ids = new int[count];
        int p = 0;
        for (int i = 0; i < count; i++)
        {
            int used = VarInt.Read(body.AsSpan(p), out ulong v);
            if (used == 0)
            {
                throw new RecallFormatException($"truncated tombstone list: {path}");
            }
            p += used;
            ids[i] = (int)v;
        }
        return ids;
    }

    /// <summary>增量追加删除标记: 读旧表 + 合并 + 排序去重 + 原子替换 (重复调用幂等)。</summary>
    public static int Add(string segmentDir, IEnumerable<int> docIds)
    {
        var set = new SortedSet<int>(Read(segmentDir));
        foreach (int id in docIds)
        {
            set.Add(id);
        }
        var arr = new List<int>(set);
        Write(segmentDir, arr);
        return arr.Count;
    }

    public static void Write(string segmentDir, IReadOnlyList<int> sortedIds)
    {
        string path = System.IO.Path.Combine(segmentDir, RecallConstants.TombFile);
        var buf = new ByteBuffer(64);
        buf.Write(RecallConstants.TombMagic);
        Span<byte> cnt = stackalloc byte[4];
        System.Buffers.Binary.BinaryPrimitives.WriteInt32LittleEndian(cnt, sortedIds.Count);
        buf.Write(cnt);
        for (int i = 0; i < sortedIds.Count; i++)
        {
            buf.WriteVarInt((ulong)sortedIds[i]);
        }
        using var fs = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.None);
        fs.Write(buf.Raw, 0, buf.Length);
    }
}
