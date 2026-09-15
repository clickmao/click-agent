// R480: 独立文本召回模块 —— 段读取面 (词表二级跳表查找 + postings 块游标 + 文档/正文按需 pread)。
using System.Buffers.Binary;

namespace agent.Recall;

public sealed class RecallTermRecord
{
    public required bool Found { get; init; }
    public required int DocFreq { get; init; }
    public required long PostingsOffset { get; init; }
    public required int PostingsLength { get; init; }
}

/// <summary>postings 块游标: 只前进, 支持 block-max 跳块 (跳过时不解码 payload)。</summary>
public sealed class RecallPostingCursor
{
    private readonly RecallFile _file;
    private readonly RecallReadStats? _stats;
    private readonly long _regionEnd;
    private readonly int _totalBlocks;
    private readonly byte[] _payload = new byte[1 << 12];
    private readonly long[] _docs = new long[256];
    private readonly int[] _tfs = new int[256];

    private long _pos;
    private int _blocksRead;
    private int _count;
    private int _idx;
    private long _lastDocAbs = -1;

    public int DocFreq { get; }
    public int MaxTf { get; }
    public long CurrentDoc { get; private set; } = -1;
    public int CurrentTf { get; private set; }
    public long BlockLastDoc { get; private set; } = -1;
    public bool Exhausted { get; private set; }

    public RecallPostingCursor(RecallFile postings, long offset, int length, RecallReadStats? stats)
    {
        _file = postings;
        _stats = stats;
        _pos = offset;
        _regionEnd = offset + length;
        Span<byte> head = stackalloc byte[32];
        int avail = _file.ReadUpTo(offset, head);
        if (avail <= 0)
        {
            throw new RecallCorruptionException("empty postings region");
        }
        int used = VarInt.Read(head[..avail], out ulong df);
        if (used == 0)
        {
            throw new RecallCorruptionException("truncated postings head (docFreq)");
        }
        DocFreq = (int)df;
        _pos += used;
        int used2 = VarInt.Read(head[used..avail], out ulong maxTf);
        if (used2 == 0)
        {
            throw new RecallCorruptionException("truncated postings head (maxTf)");
        }
        MaxTf = (int)maxTf;
        _pos += used2;
        int used3 = VarInt.Read(head[(used + used2)..avail], out ulong numBlocks);
        if (used3 == 0)
        {
            throw new RecallCorruptionException("truncated postings head (numBlocks)");
        }
        _totalBlocks = (int)numBlocks;
        _pos += used3;
        if (DocFreq == 0)
        {
            Exhausted = true;
        }
    }

    /// <summary>推进到下一个文档; 返回 false 表示耗尽。</summary>
    public bool MoveNext()
    {
        while (true)
        {
            if (_idx < _count)
            {
                CurrentDoc = _docs[_idx];
                CurrentTf = _tfs[_idx];
                _idx++;
                return true;
            }
            if (!LoadNextBlock(skipIfLastDocBelow: -1))
            {
                Exhausted = true;
                CurrentDoc = -1;
                return false;
            }
        }
    }

    /// <summary>跳到 ≥ target 的文档; 整块 lastDoc &lt; target 时只读块头, 直接跳过 payload (block-max 裁剪)。</summary>
    public void SkipTo(long target)
    {
        if (Exhausted)
        {
            return;
        }
        while (CurrentDoc < target)
        {
            while (_idx < _count && _docs[_idx] < target)
            {
                CurrentDoc = _docs[_idx];
                CurrentTf = _tfs[_idx];
                _idx++;
            }
            if (_idx < _count)
            {
                CurrentDoc = _docs[_idx];
                CurrentTf = _tfs[_idx];
                _idx++;
                return;
            }
            if (!LoadNextBlock(skipIfLastDocBelow: target))
            {
                Exhausted = true;
                CurrentDoc = -1;
                return;
            }
        }
    }

    /// <summary>读下一块; 若块头 lastDoc &lt; skipIfLastDocBelow 则只推进偏移 (不解码 payload)。</summary>
    private bool LoadNextBlock(long skipIfLastDocBelow)
    {
        if (_blocksRead >= _totalBlocks)
        {
            return false;
        }
        Span<byte> head = stackalloc byte[32];
        int avail = _file.ReadUpTo(_pos, head);
        if (avail <= 0)
        {
            return false;
        }
        int used = VarInt.Read(head[..avail], out ulong lastDoc);
        used += VarInt.Read(head[used..avail], out _);
        used += VarInt.Read(head[used..avail], out ulong nDocs);
        used += VarInt.Read(head[used..avail], out ulong payloadLen);
        if (used == 0 || payloadLen > (ulong)_payload.Length || nDocs > (ulong)_docs.Length || nDocs == 0)
        {
            throw new RecallCorruptionException($"bad posting block header: n={nDocs} len={payloadLen}");
        }
        _pos += used;
        BlockLastDoc = (long)lastDoc;

        if (skipIfLastDocBelow >= 0 && BlockLastDoc < skipIfLastDocBelow)
        {
            _pos += (long)payloadLen;
            _blocksRead++;
            _count = 0;
            _idx = 0;
            if (_stats is not null)
            {
                _stats.BlocksSkipped++;
            }
            return true;
        }

        _file.ReadExactly(_pos, _payload.AsSpan(0, (int)payloadLen));
        _pos += (long)payloadLen;
        _blocksRead++;
        if (_stats is not null)
        {
            _stats.BlocksScanned++;
        }

        int n = 0;
        int p = 0;
        bool firstInBlock = true;
        var span = _payload.AsSpan(0, (int)payloadLen);
        while (p < span.Length && n < (int)nDocs)
        {
            int u = VarInt.Read(span[p..], out ulong delta);
            if (u == 0)
            {
                throw new RecallCorruptionException("truncated posting payload (delta)");
            }
            p += u;
            // 每块 delta 链重置: 块内首条的 delta 基数为 0 ⇒ 绝对值。
            // 这样跳块(不读 payload)后仍能正确解出后续块的 docId。
            _lastDocAbs = firstInBlock ? (long)delta : _lastDocAbs + (long)delta;
            firstInBlock = false;
            u = VarInt.Read(span[p..], out ulong tf);
            if (u == 0)
            {
                throw new RecallCorruptionException("truncated posting payload (tf)");
            }
            p += u;
            _docs[n] = _lastDocAbs;
            _tfs[n] = (int)tf;
            n++;
        }
        if (n != (int)nDocs)
        {
            throw new RecallCorruptionException($"posting block decode mismatch: got {n} want {nDocs}");
        }
        _count = n;
        _idx = 0;
        if (_stats is not null)
        {
            _stats.PostingsVisited += n;
        }
        return n > 0;
    }
}

public sealed class RecallSegmentReader : IDisposable
{
    private readonly RecallFile _terms;
    private readonly RecallFile _postings;
    private readonly RecallFile _text;
    private RecallFile? _links;
    private readonly RecallDocsReader _docs;
    private readonly int[] _tombstones;
    private readonly RecallReadStats? _stats;

    public RecallSegmentMeta Meta { get; }
    public string DirectoryPath { get; }
    public int LiveDocCount { get; }

    public RecallSegmentReader(string segmentDir, RecallReadStats? stats = null)
    {
        DirectoryPath = segmentDir;
        _stats = stats;
        using (var metaFile = new RecallFile(Path.Combine(segmentDir, RecallConstants.SegmentFile), stats))
        {
            Meta = RecallSegmentMeta.Read(metaFile);
        }
        _terms = new RecallFile(Path.Combine(segmentDir, RecallConstants.TermsFile), stats);
        _postings = new RecallFile(Path.Combine(segmentDir, RecallConstants.PostingsFile), stats);
        _text = new RecallFile(Path.Combine(segmentDir, RecallConstants.TextFile), stats);
        _docs = new RecallDocsReader(segmentDir, stats);
        _tombstones = RecallTombstones.Read(segmentDir, stats);
        LiveDocCount = Meta.DocCount - _tombstones.Length;
    }

    public long ResidentBytes => Meta.ResidentBytes + 32L * _tombstones.Length;

    public bool IsDeleted(int docId)
    {
        if (_tombstones.Length == 0)
        {
            return false;
        }
        int lo = 0;
        int hi = _tombstones.Length - 1;
        while (lo <= hi)
        {
            int mid = (lo + hi) >> 1;
            int v = _tombstones[mid];
            if (v == docId)
            {
                return true;
            }
            if (v < docId)
            {
                lo = mid + 1;
            }
            else
            {
                hi = mid - 1;
            }
        }
        return false;
    }

    public RecallTermRecord FindTerm(ReadOnlySpan<byte> term)
    {
        if (_stats is not null)
        {
            _stats.TermLookups++;
        }
        var tops = Meta.TermTops;
        if (tops.Count == 0)
        {
            return new RecallTermRecord { Found = false, DocFreq = 0, PostingsOffset = 0, PostingsLength = 0 };
        }
        int lo = 0;
        int hi = tops.Count - 1;
        int group = 0;
        while (lo <= hi)
        {
            int mid = (lo + hi) >> 1;
            int cmp = term.SequenceCompareTo(tops[mid].Term);
            if (cmp < 0)
            {
                hi = mid - 1;
            }
            else
            {
                group = mid;
                lo = mid + 1;
            }
        }
        long start = tops[group].Offset;
        long end = group + 1 < tops.Count ? tops[group + 1].Offset : Meta.TermsLength;
        if (end <= start)
        {
            return new RecallTermRecord { Found = false, DocFreq = 0, PostingsOffset = 0, PostingsLength = 0 };
        }

        var window = _terms.ReadBytes(start, (int)Math.Min(end - start, 1 << 20));
        int p = 0;
        while (p < window.Length)
        {
            int u = VarInt.Read(window.AsSpan(p), out ulong termLen);
            if (u == 0)
            {
                throw new RecallCorruptionException($"truncated term record in {DirectoryPath}");
            }
            p += u;
            if (p + (int)termLen > window.Length)
            {
                throw new RecallCorruptionException($"term window too small in {DirectoryPath}; regroup needed");
            }
            int cmp = term.SequenceCompareTo(window.AsSpan(p, (int)termLen));
            if (cmp < 0)
            {
                return new RecallTermRecord { Found = false, DocFreq = 0, PostingsOffset = 0, PostingsLength = 0 };
            }
            bool hit = cmp == 0;
            p += (int)termLen;
            u = VarInt.Read(window.AsSpan(p), out ulong df);
            p += u;
            u = VarInt.Read(window.AsSpan(p), out ulong poff);
            p += u;
            u = VarInt.Read(window.AsSpan(p), out ulong plen);
            p += u;
            if (hit)
            {
                return new RecallTermRecord
                {
                    Found = true,
                    DocFreq = (int)df,
                    PostingsOffset = (long)poff,
                    PostingsLength = (int)plen,
                };
            }
        }
        return new RecallTermRecord { Found = false, DocFreq = 0, PostingsOffset = 0, PostingsLength = 0 };
    }

    public RecallPostingCursor OpenPostings(RecallTermRecord record)
        => new(_postings, record.PostingsOffset, record.PostingsLength, _stats);

    public int DocLength(int docId) => _docs.DocLength(docId);

    /// <summary>产出物自带地址: 读取该文档写入时携带的链接/文件地址 (没有 links.bin 的旧段返回空表)。</summary>
    public List<string> ReadLinks(int docId)
    {
        if (!RecallLinksFile.Exists(DirectoryPath))
        {
            return new List<string>();
        }
        _links ??= new RecallFile(Path.Combine(DirectoryPath, RecallConstants.LinksFile), _stats);
        return RecallLinksFile.Read(DirectoryPath, _links, docId, Meta.DocCount, _stats);
    }

    public RecallDocRecord GetDoc(int docId)
    {
        var rec = _docs.Read(docId);
        return new RecallDocRecord
        {
            DocId = docId,
            Id = rec.Id,
            Path = rec.Path,
            TextOffset = rec.TextOffset,
            TextLength = rec.TextLength,
            DocLenTokens = rec.DocLenTokens,
            Size = rec.Size,
            MtimeTicks = rec.MtimeTicks,
            Inode = rec.Inode,
        };
    }

    public string ReadText(RecallDocRecord rec)
    {
        var bytes = _text.ReadBytes(rec.TextOffset, rec.TextLength);
        return System.Text.Encoding.UTF8.GetString(bytes);
    }

    public void Dispose()
    {
        _terms.Dispose();
        _postings.Dispose();
        _text.Dispose();
        _docs.Dispose();
    }

    internal RecallFile PostingsFileForTest => _postings;
    internal RecallFile TermsFileForTest => _terms;
    internal RecallFile TextFileForTest => _text;
}
