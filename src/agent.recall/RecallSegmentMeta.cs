namespace agent.recall;


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
