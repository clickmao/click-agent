namespace agent.recall;


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
