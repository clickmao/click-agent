// R480: 独立文本召回模块 —— 段写入面 (postings 在线 delta 编码 + 每 128 文档一块 block-max 元数据)。
// 内存有界: 段粒度同时受「文档数」与「缓冲 postings 字节」两个上限约束 ⇒ 索引规模与常驻内存脱钩。
namespace agent.recall;

/// <summary>块式 postings 累积器: 每个 term 一块接一块地写出 (块内 delta-varint)。</summary>
internal sealed class RecallPostingAccumulator
{
    private readonly Dictionary<ulong, RecallTermState> _terms = new();
    public long BufferedBytes { get; private set; }
    public int TermCount => _terms.Count;
    public int DocCount { get; private set; }
    public long TotalTokens { get; private set; }

    public void AddPosting(ReadOnlySpan<byte> token, int docId, int tf)
    {
        ulong h = RecallTokenizer.Hash(token);
        if (!_terms.TryGetValue(h, out var st))
        {
            st = new RecallTermState { Term = token.ToArray() };
            _terms[h] = st;
            BufferedBytes += 16 + st.Term.Length;
        }
        else if (!st.Term.AsSpan().SequenceEqual(token))
        {
            // 64 位哈希碰撞: 段内增量构建不做链式冲突表, fail-closed 暴露 (不静默并词)。
            throw new RecallFormatException("token hash collision inside segment build");
        }

        if (st.LastDocId == docId)
        {
            return; // tf 已在调用方按文档聚合, 重复调用没有意义
        }
        int delta = st.LastDocId < 0 ? docId : docId - st.LastDocId;
        st.Payload.WriteVarInt((ulong)delta);
        st.Payload.WriteVarInt((ulong)tf);
        BufferedBytes += 2;
        st.TotalDocs++;
        st.BlockDocs++;
        st.BlockLastDocId = docId;
        if (tf > st.BlockMaxTf)
        {
            st.BlockMaxTf = tf;
        }
        if (tf > st.MaxTf)
        {
            st.MaxTf = tf;
        }
        st.LastDocId = docId;

        if (st.BlockDocs >= RecallConstants.PostingBlockDocs)
        {
            CloseBlock(st);
        }
    }

    private void CloseBlock(RecallTermState st)
    {
        if (st.BlockDocs == 0)
        {
            return;
        }
        var hdr = new ByteBuffer(24);
        hdr.WriteVarInt((ulong)st.BlockLastDocId);
        hdr.WriteVarInt((ulong)st.BlockMaxTf);
        hdr.WriteVarInt((ulong)st.BlockDocs);
        hdr.WriteVarInt((ulong)st.Payload.Length);
        st.Blocks.Write(hdr.Span);
        st.Blocks.Write(st.Payload.Span);
        BufferedBytes += st.Payload.Length + hdr.Length;
        st.Payload.Clear();
        st.BlockDocs = 0;
        st.BlockMaxTf = 0;
        st.NumBlocks++;
        // 块边界重置 delta 链: 下一块首条 delta 基数为 0 (绝对值) ⇒ 读侧可安全跳块。
        st.LastDocId = 0;
    }

    public void BeginDoc() => DocCount++;

    public void EndDoc() { }

    public int AddTokens(string text, RecallTokenizerOptions options, int docId)
    {
        var counts = new Dictionary<ulong, (byte[] Token, int Tf)>();
        var collector = new CountingSink(counts);
        RecallTokenizer.Tokenize(text, options, collector);
        TotalTokens += collector.TokenCount;
        // 稳定顺序: 按 token 字节序, 保证同一输入在不同运行下产出同一 postings 顺序。
        var list = new List<(byte[] Token, int Tf)>(counts.Count);
        foreach (var kv in counts.Values)
        {
            list.Add(kv);
        }
        list.Sort(static (a, b) => a.Token.AsSpan().SequenceCompareTo(b.Token));
        for (int i = 0; i < list.Count; i++)
        {
            AddPosting(list[i].Token, docId, list[i].Tf);
        }
        return collector.TokenCount;
    }

    private sealed class CountingSink : ITokenSink
    {
        private readonly Dictionary<ulong, (byte[] Token, int Tf)> _counts;
        public int TokenCount { get; private set; }

        public CountingSink(Dictionary<ulong, (byte[] Token, int Tf)> counts) => _counts = counts;

        public void AddToken(ReadOnlySpan<byte> utf8)
        {
            TokenCount++;
            ulong h = RecallTokenizer.Hash(utf8);
            if (_counts.TryGetValue(h, out var e))
            {
                _counts[h] = (e.Token, e.Tf + 1);
            }
            else
            {
                _counts[h] = (utf8.ToArray(), 1);
            }
        }
    }

    /// <summary>段收尾: 写 terms.bin / postings.bin, 返回 (termCount, termTops, termsLen, postingsLen)。</summary>
    public (int TermCount, List<RecallTermTop> Tops, long TermsLen, long PostingsLen) Flush(Stream terms, Stream postings)
    {
        var keys = new List<(ulong Hash, RecallTermState State)>(_terms.Count);
        foreach (var kv in _terms)
        {
            keys.Add((kv.Key, kv.Value));
        }
        keys.Sort(static (a, b) => a.State.Term.AsSpan().SequenceCompareTo(b.State.Term));

        var tops = new List<RecallTermTop>();
        long postingsLen = 0;
        for (int i = 0; i < keys.Count; i++)
        {
            var st = keys[i].State;
            CloseBlock(st);
            var bytes = st.Blocks.Span;
            var head = new ByteBuffer(32);
            head.WriteVarInt((ulong)st.TotalDocs);
            head.WriteVarInt((ulong)st.MaxTf);
            head.WriteVarInt((ulong)st.NumBlocks);
            long termOffset = terms.Position;
            if (i % RecallConstants.TermTopStride == 0)
            {
                tops.Add(new RecallTermTop { Offset = termOffset, Term = st.Term });
            }
            VarInt.WriteTo(terms, (ulong)st.Term.Length);
            terms.Write(st.Term);
            VarInt.WriteTo(terms, (ulong)st.TotalDocs);
            long postingsOffset = postings.Position;
            VarInt.WriteTo(terms, (ulong)postingsOffset);
            VarInt.WriteTo(terms, (ulong)(head.Length + bytes.Length));
            postings.Write(head.Raw, 0, head.Length);
            postings.Write(bytes);
            postingsLen += head.Length + bytes.Length;
        }
        return (keys.Count, tops, terms.Position, postingsLen);
    }
}
