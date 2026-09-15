// R480: 独立文本召回模块 —— 索引门面 (多段召回 + 常驻内存账本 + 增量写入入口)。
namespace agent.Recall;

public sealed class RecallHit
{
    public required int DocId { get; init; }
    public required string Segment { get; init; }
    public required double Score { get; init; }
    public required string Id { get; init; }
    public required string Path { get; init; }
    public required string Text { get; init; }

    /// <summary>产出物自带地址: 该文档正文里已存在的链接/文件地址 (召回沿地址走, 不靠分类)。</summary>
    public IReadOnlyList<string> Links { get; init; } = Array.Empty<string>();
}

public sealed class RecallIndex : IDisposable
{
    private readonly List<RecallSegmentReader> _readers = new();
    private readonly List<RecallSegmentSearcher> _searchers = new();
    private readonly RecallReadStats? _stats;
    private readonly string _dir;

    public RecallIndexMeta Meta { get; }
    public RecallScoringOptions Scoring { get; }
    public RecallTokenizerOptions Tokenizer => Meta.Tokenizer;
    public int DocCount { get; }
    public int SegmentCount => _readers.Count;

    private RecallIndex(string dir, RecallIndexMeta meta, RecallReadStats? stats)
    {
        _dir = dir;
        Meta = meta;
        _stats = stats;
        Scoring = new RecallScoringOptions { K1 = meta.K1, B = meta.B };
        int total = 0;
        foreach (var seg in meta.Segments)
        {
            var reader = new RecallSegmentReader(Path.Combine(dir, seg.Name), stats);
            _readers.Add(reader);
            total += reader.Meta.DocCount;
        }
        DocCount = total;
        foreach (var reader in _readers)
        {
            _searchers.Add(new RecallSegmentSearcher(reader, Scoring, total));
        }
    }

    public static RecallIndex Open(string dir, RecallReadStats? stats = null)
    {
        string metaPath = Path.Combine(dir, RecallConstants.IndexMetaFile);
        if (!File.Exists(metaPath))
        {
            throw new RecallFormatException($"index.meta not found: {dir}");
        }
        using var f = new RecallFile(metaPath, stats);
        var meta = RecallIndexMeta.Read(f);
        return new RecallIndex(dir, meta, stats);
    }

    /// <summary>建索引: 目录必须为空或不存在 (防误覆盖; 覆盖请显式删目录)。</summary>
    public static RecallIndex Build(string dir, IEnumerable<RecallSourceDoc> docs, RecallWriteOptions? options = null, RecallReadStats? stats = null)
    {
        options ??= new RecallWriteOptions();
        if (Directory.Exists(dir) && Directory.EnumerateFileSystemEntries(dir).Any())
        {
            throw new RecallFormatException($"index directory not empty: {dir}");
        }
        using (var builder = RecallIndexBuilder.Create(dir, options))
        {
            foreach (var doc in docs)
            {
                builder.AddOne(doc);
            }
        }
        return Open(dir, stats);
    }

    /// <summary>跨段召回: 每段独立 WAND top-k, 再按分数归并; 同一文档键只保留最高分一次。</summary>
    public List<RecallHit> Search(string query, int k = 10, RecallReadStats? stats = null)
    {
        if (k < 1)
        {
            k = 1;
        }
        var readStats = stats ?? _stats;
        var merged = new List<(int Segment, RecallScoredDoc Doc)>();
        for (int s = 0; s < _searchers.Count; s++)
        {
            var part = _searchers[s].Search(query, Tokenizer, k, readStats);
            for (int i = 0; i < part.Count; i++)
            {
                merged.Add((s, part[i]));
            }
        }
        merged.Sort(static (a, b) =>
        {
            int c = b.Doc.Score.CompareTo(a.Doc.Score);
            if (c != 0)
            {
                return c;
            }
            int sc = a.Segment.CompareTo(b.Segment);
            return sc != 0 ? sc : a.Doc.DocId.CompareTo(b.Doc.DocId);
        });

        var hits = new List<RecallHit>(k);
        var seen = new HashSet<string>(StringComparer.Ordinal);
        for (int i = 0; i < merged.Count && hits.Count < k; i++)
        {
            var (seg, doc) = merged[i];
            var reader = _readers[seg];
            var record = reader.GetDoc(doc.DocId);
            if (!seen.Add(record.Id))
            {
                continue;
            }
            hits.Add(new RecallHit
            {
                DocId = doc.DocId,
                Segment = reader.DirectoryPath,
                Score = doc.Score,
                Id = record.Id,
                Path = record.Path,
                Text = reader.ReadText(record),
                Links = reader.ReadLinks(doc.DocId),
            });
        }
        return hits;
    }

    /// <summary>常驻内存账本: 只统计本模块结构 (不含内核页缓存, 也不含宿主 GC 堆噪声)。</summary>
    public RecallMemoryReport MemoryReport()
    {
        var report = new RecallMemoryReport();
        for (int i = 0; i < _readers.Count; i++)
        {
            var r = _readers[i];
            report.Add($"seg{i}.term_tops", r.Meta.ResidentBytes);
            report.Add($"seg{i}.tombstones", 32L * (r.Meta.DocCount - r.LiveDocCount));
            report.Add($"seg{i}.cursor_buffers", 0);
        }
        report.Add("index.meta", 256L * _readers.Count);
        return report;
    }

    public void Dispose()
    {
        for (int i = 0; i < _readers.Count; i++)
        {
            _readers[i].Dispose();
        }
        _readers.Clear();
        _searchers.Clear();
    }

    public string DirectoryPath => _dir;
}
