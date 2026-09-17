// R480: 独立文本召回模块 —— 磁盘格式定义 (单一定义处: 写侧/读侧都从这里取常量)。
namespace agent.recall;

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
