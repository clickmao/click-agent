// R480: 独立文本召回模块 —— 段读取面 (词表二级跳表查找 + postings 块游标 + 文档/正文按需 pread)。
using System.Buffers.Binary;

namespace agent.recall;

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
