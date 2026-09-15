// R480: 独立文本召回模块 —— BM25 + WAND(含块级跳过) 召回核心。
// 判据: 与「全候选暴力打分」在同一语料上 top-k 完全一致 (测试侧独立实现公式, 不走本文件代码)。
namespace agent.Recall;

public sealed class RecallScoredDoc
{
    public int DocId { get; init; }
    public double Score { get; init; }
}

internal sealed class TopKHeap
{
    private readonly int _k;
    private readonly double[] _scores;
    private readonly int[] _docs;
    private int _count;

    public TopKHeap(int k)
    {
        _k = k < 1 ? 1 : k;
        _scores = new double[_k];
        _docs = new int[_k];
    }

    public int Count => _count;
    public bool Full => _count >= _k;

    public double Min => _count >= _k ? _scores[0] : 0.0;

    public void Push(double score, int doc)
    {
        if (_count < _k)
        {
            _scores[_count] = score;
            _docs[_count] = doc;
            _count++;
            SiftUp(_count - 1);
            return;
        }
        if (score <= _scores[0])
        {
            return;
        }
        _scores[0] = score;
        _docs[0] = doc;
        SiftDown(0);
    }

    public List<RecallScoredDoc> DrainDescending()
    {
        var list = new List<RecallScoredDoc>(_count);
        for (int i = 0; i < _count; i++)
        {
            list.Add(new RecallScoredDoc { DocId = _docs[i], Score = _scores[i] });
        }
        list.Sort((a, b) =>
        {
            int c = b.Score.CompareTo(a.Score);
            return c != 0 ? c : a.DocId.CompareTo(b.DocId);
        });
        return list;
    }

    private void SiftUp(int i)
    {
        while (i > 0)
        {
            int p = (i - 1) >> 1;
            if (_scores[p] <= _scores[i])
            {
                break;
            }
            Swap(p, i);
            i = p;
        }
    }

    private void SiftDown(int i)
    {
        while (true)
        {
            int l = 2 * i + 1;
            int r = l + 1;
            int m = i;
            if (l < _count && _scores[l] < _scores[m])
            {
                m = l;
            }
            if (r < _count && _scores[r] < _scores[m])
            {
                m = r;
            }
            if (m == i)
            {
                break;
            }
            Swap(m, i);
            i = m;
        }
    }

    private void Swap(int a, int b)
    {
        (_scores[a], _scores[b]) = (_scores[b], _scores[a]);
        (_docs[a], _docs[b]) = (_docs[b], _docs[a]);
    }
}

/// <summary>BM25 参数 + 打分口径。</summary>
public sealed class RecallScoringOptions
{
    public double K1 { get; init; } = 1.2;
    public double B { get; init; } = 0.75;
    public double DocFreqIdf(int docCount, int docFreq)
        => Math.Log(1.0 + (docCount - docFreq + 0.5) / (docFreq + 0.5));

    public double Score(double idf, int tf, int docLen, double avgDocLen)
    {
        double dl = docLen < 1 ? 1 : docLen;
        double norm = 1.0 - B + B * (dl / Math.Max(1.0, avgDocLen));
        return idf * tf * (K1 + 1.0) / (tf + K1 * norm);
    }

    public double UpperBound(double idf, int maxTf, double avgDocLen)
    {
        double norm = 1.0 - B + B * (1.0 / Math.Max(1.0, avgDocLen));
        return idf * maxTf * (K1 + 1.0) / (maxTf + K1 * norm);
    }
}

internal sealed class RecallCursorSlot
{
    public required RecallPostingCursor Cursor { get; init; }
    public required double UpperBound { get; init; }
    public required double Idf { get; init; }
    public required int QueryTf { get; init; }
}

public sealed class RecallSegmentSearcher
{
    private readonly RecallSegmentReader _reader;
    private readonly RecallScoringOptions _scoring;
    private readonly int _indexDocCount;

    public RecallSegmentSearcher(RecallSegmentReader reader, RecallScoringOptions scoring, int indexDocCount)
    {
        _reader = reader;
        _scoring = scoring;
        _indexDocCount = indexDocCount;
    }

    /// <summary>WAND: 以词上界剪枝 + 块级跳过, 不做全候选扫描。</summary>
    public List<RecallScoredDoc> Search(ReadOnlySpan<char> query, RecallTokenizerOptions tokenizer, int k, RecallReadStats? stats)
    {
        var queryTerms = CollectQueryTerms(query, tokenizer);
        if (queryTerms.Count == 0)
        {
            return new List<RecallScoredDoc>();
        }

        var slots = new List<RecallCursorSlot>();
        long totalPostings = 0;
        foreach (var (term, qtf) in queryTerms)
        {
            var record = _reader.FindTerm(term);
            if (!record.Found)
            {
                continue;
            }
            var cursor = _reader.OpenPostings(record);
            if (cursor.Exhausted)
            {
                continue;
            }
            double idf = _scoring.DocFreqIdf(_indexDocCount, record.DocFreq);
            slots.Add(new RecallCursorSlot
            {
                Cursor = cursor,
                UpperBound = qtf * _scoring.UpperBound(idf, cursor.MaxTf, _reader.Meta.AvgDocLen),
                Idf = idf,
                QueryTf = qtf,
            });
            totalPostings += cursor.DocFreq;
            cursor.MoveNext();
        }
        if (slots.Count == 0)
        {
            return new List<RecallScoredDoc>();
        }

        var heap = new TopKHeap(k);
        double theta = 0.0;
        long guard = 4L * totalPostings + 64L;

        while (true)
        {
            if (--guard <= 0)
            {
                throw new RecallCorruptionException("wand iteration guard tripped (possible posting order violation)");
            }

            slots.Sort(static (a, b) =>
            {
                long da = a.Cursor.CurrentDoc < 0 ? long.MaxValue : a.Cursor.CurrentDoc;
                long db = b.Cursor.CurrentDoc < 0 ? long.MaxValue : b.Cursor.CurrentDoc;
                return da.CompareTo(db);
            });
            while (slots.Count > 0 && slots[0].Cursor.CurrentDoc < 0)
            {
                slots.RemoveAt(0);
            }
            if (slots.Count == 0)
            {
                break;
            }

            double acc = 0.0;
            int pivot = -1;
            for (int i = 0; i < slots.Count; i++)
            {
                if (slots[i].Cursor.CurrentDoc < 0)
                {
                    break;
                }
                acc += slots[i].UpperBound;
                if (acc > theta)
                {
                    pivot = i;
                    break;
                }
            }
            if (pivot < 0)
            {
                break;
            }

            long pivotDoc = slots[pivot].Cursor.CurrentDoc;
            bool aligned = true;
            for (int i = 0; i < pivot; i++)
            {
                var c = slots[i].Cursor;
                if (c.CurrentDoc != pivotDoc)
                {
                    c.SkipTo(pivotDoc);
                    if (stats is not null)
                    {
                        stats.PostingsVisited++;
                    }
                    if (c.CurrentDoc != pivotDoc)
                    {
                        aligned = false;
                    }
                }
            }
            if (!aligned)
            {
                continue;
            }

            if (!_reader.IsDeleted((int)pivotDoc))
            {
                double score = 0.0;
                for (int i = 0; i < slots.Count; i++)
                {
                    var c = slots[i].Cursor;
                    if (c.CurrentDoc == pivotDoc)
                    {
                        score += slots[i].QueryTf * _scoring.Score(
                            slots[i].Idf, c.CurrentTf, _reader.DocLength((int)pivotDoc), _reader.Meta.AvgDocLen);
                    }
                }
                if (score > 0)
                {
                    heap.Push(score, (int)pivotDoc);
                    if (stats is not null)
                    {
                        stats.DocsScored++;
                    }
                    theta = heap.Min;
                }
            }

            for (int i = 0; i < slots.Count; i++)
            {
                var c = slots[i].Cursor;
                if (c.CurrentDoc == pivotDoc)
                {
                    c.MoveNext();
                    if (stats is not null)
                    {
                        stats.PostingsVisited++;
                    }
                }
            }
        }

        return heap.DrainDescending();
    }

    private static List<(byte[] Term, int Qtf)> CollectQueryTerms(ReadOnlySpan<char> query, RecallTokenizerOptions tokenizer)
    {
        var sink = new QueryTermSink();
        RecallTokenizer.Tokenize(query, tokenizer, sink);
        return sink.Terms;
    }

    private sealed class QueryTermSink : ITokenSink
    {
        private readonly Dictionary<ulong, int> _index = new();
        public List<(byte[] Term, int Qtf)> Terms { get; } = new();

        public void AddToken(ReadOnlySpan<byte> token)
        {
            ulong h = RecallTokenizer.Hash(token);
            if (_index.TryGetValue(h, out int at))
            {
                var existing = Terms[at];
                Terms[at] = (existing.Term, existing.Qtf + 1);
                return;
            }
            _index[h] = Terms.Count;
            Terms.Add((token.ToArray(), 1));
        }
    }
}
