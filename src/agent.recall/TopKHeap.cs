namespace agent.recall;


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
