// R480: 独立文本召回模块 —— 段写入 + 索引构建/追加。
// 主键命名空间: 文本 token 首字节 ≥ 0x21 或 ≥ 0xC2(UTF-8 多字节), 因此 0x01/0x02 前缀
// 只可能来自本模块自己写入的「文档键」, 不会与正文 token 冲突 (单一定义处, 读侧同一函数)。
using System.Text;

namespace agent.recall;


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
