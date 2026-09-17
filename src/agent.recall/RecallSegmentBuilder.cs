// R480: 独立文本召回模块 —— 段写入 + 索引构建/追加。
// 主键命名空间: 文本 token 首字节 ≥ 0x21 或 ≥ 0xC2(UTF-8 多字节), 因此 0x01/0x02 前缀
// 只可能来自本模块自己写入的「文档键」, 不会与正文 token 冲突 (单一定义处, 读侧同一函数)。
using System.Text;

namespace agent.recall;

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
