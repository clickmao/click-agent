namespace agent.recall;


/// <summary>tomb.bin: 已删 docId 的有序列表 (段内可见性过滤, 避免为一次删除重写整段)。</summary>
public static class RecallTombstones
{
    public static int[] Read(string segmentDir, RecallReadStats? stats = null)
    {
        string path = System.IO.Path.Combine(segmentDir, RecallConstants.TombFile);
        if (!File.Exists(path))
        {
            return Array.Empty<int>();
        }
        using var f = new RecallFile(path, stats);
        var head = f.ReadBytes(0, 12);
        if (!head.AsSpan(0, 8).SequenceEqual(RecallConstants.TombMagic))
        {
            throw new RecallFormatException($"bad tombstone magic: {path}");
        }
        int count = System.Buffers.Binary.BinaryPrimitives.ReadInt32LittleEndian(head.AsSpan(8, 4));
        var body = f.ReadBytes(12, (int)Math.Max(0, f.Length - 12));
        var ids = new int[count];
        int p = 0;
        for (int i = 0; i < count; i++)
        {
            int used = VarInt.Read(body.AsSpan(p), out ulong v);
            if (used == 0)
            {
                throw new RecallFormatException($"truncated tombstone list: {path}");
            }
            p += used;
            ids[i] = (int)v;
        }
        return ids;
    }

    /// <summary>增量追加删除标记: 读旧表 + 合并 + 排序去重 + 原子替换 (重复调用幂等)。</summary>
    public static int Add(string segmentDir, IEnumerable<int> docIds)
    {
        var set = new SortedSet<int>(Read(segmentDir));
        foreach (int id in docIds)
        {
            set.Add(id);
        }
        var arr = new List<int>(set);
        Write(segmentDir, arr);
        return arr.Count;
    }

    public static void Write(string segmentDir, IReadOnlyList<int> sortedIds)
    {
        string path = System.IO.Path.Combine(segmentDir, RecallConstants.TombFile);
        var buf = new ByteBuffer(64);
        buf.Write(RecallConstants.TombMagic);
        Span<byte> cnt = stackalloc byte[4];
        System.Buffers.Binary.BinaryPrimitives.WriteInt32LittleEndian(cnt, sortedIds.Count);
        buf.Write(cnt);
        for (int i = 0; i < sortedIds.Count; i++)
        {
            buf.WriteVarInt((ulong)sortedIds[i]);
        }
        using var fs = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.None);
        fs.Write(buf.Raw, 0, buf.Length);
    }
}
