// R480: 独立文本召回模块 —— 段写入 + 索引构建/追加。
// 主键命名空间: 文本 token 首字节 ≥ 0x21 或 ≥ 0xC2(UTF-8 多字节), 因此 0x01/0x02 前缀
// 只可能来自本模块自己写入的「文档键」, 不会与正文 token 冲突 (单一定义处, 读侧同一函数)。
using System.Text;

namespace agent.Recall;

public static class RecallKeys
{
    public const byte IdPrefix = 0x01;
    public const byte PathPrefix = 0x02;

    public static byte[] IdKey(string id) => Prefix(IdPrefix, id);
    public static byte[] PathKey(string path) => Prefix(PathPrefix, path);

    private static byte[] Prefix(byte prefix, string value)
    {
        var body = Encoding.UTF8.GetBytes(value);
        var buf = new byte[body.Length + 1];
        buf[0] = prefix;
        body.CopyTo(buf, 1);
        return buf;
    }
}

public sealed class RecallSegmentWriteResult
{
    public required string Name { get; init; }
    public required string Directory { get; init; }
    public required int DocCount { get; init; }
    public required int TermCount { get; init; }
    public required double AvgDocLen { get; init; }
    public required long TermTopsResidentBytes { get; init; }
    public required long IndexBytes { get; init; }
}

internal sealed class RecallSegmentBuilder
{
    private readonly RecallWriteOptions _options;
    private readonly string _dir;
    private readonly List<(RecallSourceDoc Doc, long TextOffset, int TextBytes, int DocLen)> _docs = new();
    private readonly List<List<string>> _links = new();
    private readonly List<string> _linkScratch = new();
    private readonly RecallPostingAccumulator _postings = new();
    private readonly FileStream _text;

    public RecallSegmentBuilder(string dir, RecallWriteOptions options)
    {
        _dir = dir;
        _options = options;
        Directory.CreateDirectory(dir);
        _text = new FileStream(Path.Combine(dir, RecallConstants.TextFile), FileMode.Create, FileAccess.Write, FileShare.None, 1 << 16);
    }

    public int DocCount => _docs.Count;
    public long BufferedPostingsBytes => _postings.BufferedBytes;
    public long TextBytes => _text.Length;

    public void Add(RecallSourceDoc doc)
    {
        int docId = _docs.Count;
        var textBytes = Encoding.UTF8.GetBytes(doc.Text ?? string.Empty);
        long textOffset = _text.Position;
        _text.Write(textBytes);
        int tokens = _postings.AddTokens(doc.Text ?? string.Empty, _options.Tokenizer, docId);
        // 文档键: 让「按 id / 按 path 定位与删除」也能走倒排 (不额外常驻 id→doc 映射表)。
        _postings.AddPosting(RecallKeys.IdKey(doc.Id), docId, 1);
        _postings.AddPosting(RecallKeys.PathKey(doc.Path), docId, 1);
        // 产出物自带地址: 正文里已有的链接/文件地址随文档落盘 (召回不需要分类, 沿地址走)。
        int linkCount = RecallLinkExtractor.Extract((doc.Text ?? string.Empty).AsSpan(), _options.Links, _linkScratch, doc.Path);
        _links.Add(new List<string>(_linkScratch.Take(linkCount)));
        _docs.Add((doc, textOffset, textBytes.Length, tokens));
    }

    public RecallSegmentWriteResult Flush(string name)
    {
        _text.Flush();
        long textLength = _text.Length;
        _text.Dispose();

        long termsLen;
        long postingsLen;
        int termCount;
        List<RecallTermTop> tops;
        using (var terms = new FileStream(Path.Combine(_dir, RecallConstants.TermsFile), FileMode.Create, FileAccess.Write, FileShare.None, 1 << 16))
        using (var postings = new FileStream(Path.Combine(_dir, RecallConstants.PostingsFile), FileMode.Create, FileAccess.Write, FileShare.None, 1 << 16))
        {
            (termCount, tops, termsLen, postingsLen) = _postings.Flush(terms, postings);
        }

        WriteDocs();
        RecallLinksFile.Write(_dir, _links);
        WriteLens();

        long totalTokens = 0;
        for (int i = 0; i < _docs.Count; i++)
        {
            totalTokens += _docs[i].DocLen;
        }
        double avgDocLen = _docs.Count == 0 ? 0 : (double)totalTokens / _docs.Count;

        var metaBytes = BuildMetaBytes(name, termCount, avgDocLen, termsLen, postingsLen, tops);
        File.WriteAllBytes(Path.Combine(_dir, RecallConstants.SegmentFile), metaBytes);

        long indexBytes = 0;
        foreach (var f in new[] { RecallConstants.SegmentFile, RecallConstants.TermsFile, RecallConstants.PostingsFile, RecallConstants.DocsFile, RecallConstants.DocsLenFile, RecallConstants.TextFile })
        {
            var fi = new FileInfo(Path.Combine(_dir, f));
            if (fi.Exists)
            {
                indexBytes += fi.Length;
            }
        }
        var topsBytes = new RecallSegmentMeta
        {
            Directory = _dir,
            DocCount = _docs.Count,
            TermCount = termCount,
            AvgDocLen = avgDocLen,
            BlockSize = RecallConstants.PostingBlockDocs,
            TermTopStride = RecallConstants.TermTopStride,
            TermsLength = termsLen,
            PostingsLength = postingsLen,
            DocsLength = 0,
            TextLength = textLength,
            TermTops = tops,
        }.ResidentBytes;

        return new RecallSegmentWriteResult
        {
            Name = name,
            Directory = _dir,
            DocCount = _docs.Count,
            TermCount = termCount,
            AvgDocLen = avgDocLen,
            TermTopsResidentBytes = topsBytes,
            IndexBytes = indexBytes,
        };
    }

    private void WriteDocs()
    {
        using var fs = new FileStream(Path.Combine(_dir, RecallConstants.DocsFile), FileMode.Create, FileAccess.Write, FileShare.None, 1 << 16);
        var header = new byte[12 + 8 * (_docs.Count + 1)];
        RecallConstants.DocsMagic.CopyTo(header.AsSpan(0, 8));
        System.Buffers.Binary.BinaryPrimitives.WriteInt32LittleEndian(header.AsSpan(8, 4), _docs.Count);
        long pos = header.Length;
        for (int i = 0; i < _docs.Count; i++)
        {
            System.Buffers.Binary.BinaryPrimitives.WriteInt64LittleEndian(header.AsSpan(12 + i * 8, 8), pos);
            var rec = _docs[i];
            var encoded = new RecallDocRecord
            {
                DocId = i,
                Id = rec.Doc.Id,
                Path = rec.Doc.Path,
                TextOffset = rec.TextOffset,
                TextLength = rec.TextBytes,
                DocLenTokens = rec.DocLen,
                Size = rec.Doc.Size,
                MtimeTicks = rec.Doc.MtimeTicks,
                Inode = rec.Doc.Inode,
            }.Encode();
            pos += encoded.Length;
        }
        System.Buffers.Binary.BinaryPrimitives.WriteInt64LittleEndian(header.AsSpan(12 + _docs.Count * 8, 8), pos);
        fs.Write(header);
        for (int i = 0; i < _docs.Count; i++)
        {
            var rec = _docs[i];
            var encoded = new RecallDocRecord
            {
                DocId = i,
                Id = rec.Doc.Id,
                Path = rec.Doc.Path,
                TextOffset = rec.TextOffset,
                TextLength = rec.TextBytes,
                DocLenTokens = rec.DocLen,
                Size = rec.Doc.Size,
                MtimeTicks = rec.Doc.MtimeTicks,
                Inode = rec.Doc.Inode,
            }.Encode();
            fs.Write(encoded);
        }
    }

    private void WriteLens()
    {
        using var fs = new FileStream(Path.Combine(_dir, RecallConstants.DocsLenFile), FileMode.Create, FileAccess.Write, FileShare.None, 1 << 16);
        var head = new byte[12];
        RecallConstants.LensMagic.CopyTo(head.AsSpan(0, 8));
        System.Buffers.Binary.BinaryPrimitives.WriteInt32LittleEndian(head.AsSpan(8, 4), _docs.Count);
        fs.Write(head);
        var buf = new byte[4 * Math.Max(1, _docs.Count)];
        for (int i = 0; i < _docs.Count; i++)
        {
            System.Buffers.Binary.BinaryPrimitives.WriteInt32LittleEndian(buf.AsSpan(i * 4, 4), _docs[i].DocLen);
        }
        fs.Write(buf, 0, 4 * _docs.Count);
    }

    private byte[] BuildMetaBytes(string name, int termCount, double avgDocLen, long termsLen, long postingsLen, List<RecallTermTop> tops)
    {
        using var ms = new MemoryStream();
        ms.Write(RecallConstants.SegmentMagic);
        RecallIndexMeta.WriteVar(ms, (ulong)RecallConstants.Version);
        RecallIndexMeta.WriteVar(ms, (ulong)_docs.Count);
        RecallIndexMeta.WriteVar(ms, (ulong)termCount);
        RecallIndexMeta.WriteDouble(ms, avgDocLen);
        RecallIndexMeta.WriteVar(ms, RecallConstants.PostingBlockDocs);
        RecallIndexMeta.WriteVar(ms, RecallConstants.TermTopStride);
        RecallIndexMeta.WriteVar(ms, (ulong)termsLen);
        RecallIndexMeta.WriteVar(ms, (ulong)postingsLen);
        RecallIndexMeta.WriteVar(ms, (ulong)new FileInfo(Path.Combine(_dir, RecallConstants.DocsFile)).Length);
        RecallIndexMeta.WriteVar(ms, (ulong)new FileInfo(Path.Combine(_dir, RecallConstants.TextFile)).Length);
        RecallIndexMeta.WriteVar(ms, (ulong)tops.Count);
        for (int i = 0; i < tops.Count; i++)
        {
            RecallIndexMeta.WriteInt64(ms, tops[i].Offset);
            RecallIndexMeta.WriteVar(ms, (ulong)tops[i].Term.Length);
            ms.Write(tops[i].Term);
        }
        return ms.ToArray();
    }
}

public sealed class RecallIndexBuilder : IDisposable
{
    private readonly string _dir;
    private readonly RecallWriteOptions _options;
    private readonly List<RecallSegmentRef> _segments = new();
    private RecallSegmentBuilder? _current;
    private int _nextSegmentIndex;
    private int _added;

    private RecallIndexBuilder(string dir, RecallWriteOptions options, IReadOnlyList<RecallSegmentRef> existing)
    {
        _dir = dir;
        _options = options;
        _segments.AddRange(existing);
        _nextSegmentIndex = existing.Count;
        Directory.CreateDirectory(dir);
    }

    public static RecallIndexBuilder Create(string dir, RecallWriteOptions? options = null)
    {
        options ??= new RecallWriteOptions();
        Directory.CreateDirectory(dir);
        var b = new RecallIndexBuilder(dir, options, Array.Empty<RecallSegmentRef>());
        b._nextSegmentIndex = 0;
        b.WriteIndexMeta();
        return b;
    }

    public static RecallIndexBuilder Open(string dir, RecallWriteOptions? options = null)
    {
        string metaPath = Path.Combine(dir, RecallConstants.IndexMetaFile);
        if (!File.Exists(metaPath))
        {
            throw new RecallFormatException($"index.meta not found: {dir}");
        }
        using var f = new RecallFile(metaPath);
        var meta = RecallIndexMeta.Read(f);
        var opt = options ?? new RecallWriteOptions { K1 = meta.K1, B = meta.B, Tokenizer = meta.Tokenizer };
        var b = new RecallIndexBuilder(dir, opt, meta.Segments);
        b._nextSegmentIndex = meta.Segments.Count;
        return b;
    }

    public RecallWriteOptions Options => _options;
    public int AddedCount => _added;

    public void Add(IEnumerable<RecallSourceDoc> docs)
    {
        foreach (var doc in docs)
        {
            EnsureSegment();
            _current!.Add(doc);
            _added++;
            if (_current.DocCount >= _options.MaxDocsPerSegment || _current.BufferedPostingsBytes >= _options.MaxPostingsBytesPerSegment)
            {
                FlushCurrent();
            }
        }
    }

    public void AddOne(RecallSourceDoc doc) => Add(new[] { doc });

    /// <summary>按文档键删除: 查键 → 命中 docId → 追加 tombstone。返回删除的 doc 数。</summary>
    public int DeleteByKey(string key)
    {
        FlushCurrent();   // 保证已落盘段与内存段不交叉 (删除只作用于落盘段)
        int removed = 0;
        foreach (var seg in _segments)
        {
            string segDir = Path.Combine(_dir, seg.Name);
            using var reader = new RecallSegmentReader(segDir);
            var record = reader.FindTerm(RecallKeys.PathKey(key));
            if (!record.Found)
            {
                continue;
            }
            var cursor = reader.OpenPostings(record);
            var ids = new List<int>();
            cursor.MoveNext();
            while (cursor.CurrentDoc >= 0)
            {
                if (!reader.IsDeleted((int)cursor.CurrentDoc))
                {
                    ids.Add((int)cursor.CurrentDoc);
                }
                cursor.MoveNext();
            }
            if (ids.Count > 0)
            {
                seg.TombstoneCount = RecallTombstones.Add(segDir, ids);
                removed += ids.Count;
            }
        }
        if (removed > 0)
        {
            WriteIndexMeta();
        }
        return removed;
    }

    public int DeleteBySegmentDocId(string segmentDir, IEnumerable<int> docIds)
    {
        int count = RecallTombstones.Add(segmentDir, docIds);
        var seg = _segments.FirstOrDefault(s => Path.Combine(_dir, s.Name) == segmentDir);
        if (seg is not null)
        {
            seg.TombstoneCount = count;
            WriteIndexMeta();
        }
        return count;
    }

    private void EnsureSegment()
    {
        if (_current is null)
        {
            string name = RecallConstants.SegmentPrefix + _nextSegmentIndex.ToString("D6");
            _current = new RecallSegmentBuilder(Path.Combine(_dir, name), _options);
        }
    }

    public RecallSegmentWriteResult? FlushCurrent()
    {
        if (_current is null || _current.DocCount == 0)
        {
            _current = null;
            return null;
        }
        string name = RecallConstants.SegmentPrefix + _nextSegmentIndex.ToString("D6");
        var result = _current.Flush(name);
        _current = null;
        _nextSegmentIndex++;
        _segments.Add(new RecallSegmentRef { Name = name, DocCount = result.DocCount, TombstoneCount = 0 });
        WriteIndexMeta();
        return result;
    }

    public void WriteIndexMeta()
    {
        string metaPath = Path.Combine(_dir, RecallConstants.IndexMetaFile);
        var meta = new RecallIndexMeta
        {
            K1 = _options.K1,
            B = _options.B,
            Tokenizer = _options.Tokenizer,
            Segments = _segments.ToArray(),
        };
        using var ms = new MemoryStream();
        meta.Write(ms);
        var bytes = ms.ToArray();
        string tmp = metaPath + ".tmp";
        File.WriteAllBytes(tmp, bytes);
        File.Move(tmp, metaPath, true);
    }

    public void Dispose()
    {
        FlushCurrent();
        WriteIndexMeta();
    }
}
