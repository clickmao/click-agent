// R480: 独立文本召回模块 —— 判脏 (增量) 与索引保鲜。
// 判据: 未变动的目录整块跳过 (目录 mtime 剪枝), 指纹表以「流式归并」读写 ⇒ 常驻内存与语料文件数脱钩。
// R481-D9 交替核验: 目录 mtime 对「纯内容改写」不可见 (改写不更新父目录 mtime) ⇒ 若**上轮发生过剪枝**,
//   本轮强制全量核验 (readdir + stat, 不读内容), 最多滞后 1 轮捕获; 未剪枝轮仍按目录 mtime 剪枝。
//   标注: 该策略对「上轮剪过的目录」是**严格超集** (全量核验 ⊇ 剪过的那些目录) —— 精确到目录的剪枝集合
//   不落盘 (常驻内存与文件数脱钩), 故以全量核验实现; 语义代价 = 剪枝收益隔轮折半。
// 诚实边界: 指纹只取 (相对路径, size, mtime), 不取 inode; 同 size 同 mtime 的替换需要哈希校验档 (待实现)。
namespace agent.recall;

public static class RecallDirtyScan
{
    /// <summary>
    /// 扫描根目录产出脏集并原子重写指纹表。
    /// 规范顺序 = 「目录优先、子项按 Ordinal 名排序」的深度优先遍历; 指纹表按同一顺序落盘 ⇒ 单趟流式归并。
    /// </summary>
    public static RecallScanResult Scan(string root, string storePath, RecallScanOptions options)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var result = new RecallScanResult();
        if (!Directory.Exists(root))
        {
            throw new RecallFormatException($"scan root not found: {root}");
        }

        long lastScanTicks = 0;
        bool prevScanPruned = false;
        RecallSequentialReader? store = null;
        if (File.Exists(storePath))
        {
            store = new RecallSequentialReader(storePath);
            var magic = new byte[8];
            for (int i = 0; i < 8; i++)
            {
                if (!store.TryReadByte(out magic[i]))
                {
                    throw new RecallFormatException($"truncated fingerprint store: {storePath}");
                }
            }
            if (!magic.AsSpan().SequenceEqual(RecallConstants.FpMagic))
            {
                throw new RecallFormatException($"bad fingerprint magic: {storePath}");
            }
            if (!store.TryReadVarInt(out ulong ticks) || !store.TryReadVarInt(out ulong storeCount))
            {
                throw new RecallFormatException($"truncated fingerprint header: {storePath}");
            }
            // stamp 编码 = (stampTicks << 1) | 上轮剪枝标志。
            // 兼容性推理: 旧格式 (未左移) 被读成 (旧值 >> 1) = 更早的 stamp ⇒ 只会多核验、不会误剪;
            // 该推理的前提 = LEB128 字节数不变 (ticks 量级 ≥ 2^56 ⇒ 左移前后同为 9 B, 恒成立)。
            // 旧格式 store 的实读行为**未实测** (模块未发布 / 索引目录可重建) ⇒ 记 §待确认, 不冒充实测。
            lastScanTicks = (long)(ticks >> 1);
            prevScanPruned = (ticks & 1UL) != 0UL;
            result.StoreEntries = (int)storeCount;
        }

        result.PrevScanPruned = prevScanPruned;
        // 交替核验: 上轮剪过 ⇒ 本轮抑制剪枝 (= 全量 readdir + stat)。首个扫描 (无 store) 本就无剪枝。
        bool pruneEnabled = options.PruneUnchangedDirs && store is not null && !prevScanPruned;
        result.VerifiedAllDirs = options.PruneUnchangedDirs && store is not null && prevScanPruned;

        long maxMtime = 0;
        long entriesWritten = 0;
        RecallFileEntry? pending = store is null ? null : ReadNext(store);
        Directory.CreateDirectory(Path.GetDirectoryName(storePath)!);
        string tmpPath = storePath + ".tmp";
        using (var writer = new FileStream(tmpPath, FileMode.Create, FileAccess.Write, FileShare.None))
        {
            writer.Write(RecallConstants.FpMagic);
            VarInt.WriteTo(writer, 0);              // lastScanTicks: 收尾回填
            long ticksPos = writer.Position - 1;
            VarInt.WriteTo(writer, 0);              // entryCount: 收尾回填
            long countPos = writer.Position - 1;

            Walk(root, string.Empty, lastScanTicks);

            while (pending is not null)
            {
                result.Deleted.Add(pending);
                pending = ReadNext(store!);
            }

            long stampBase = Math.Max(options.NowTicks, maxMtime);
            // stamp = (base << 1) | 本轮是否剪枝 —— 低位供**下一轮**决定是否强制核验 (§D9)
            ulong stamp = ((ulong)stampBase << 1) | (result.DirsPruned > 0 ? 1UL : 0UL);
            writer.Flush();
            long endPos = writer.Position;
            writer.Seek(0, SeekOrigin.End);

            void Walk(string dir, string relativePrefix, long currentStamp)
            {
                result.DirsVisited++;
                string[] items;
                try
                {
                    items = Directory.GetFileSystemEntries(dir);
                }
                catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
                {
                    return;
                }
                Array.Sort(items, StringComparer.Ordinal);

                bool pruned = false;
                if (pruneEnabled && relativePrefix.Length > 0
                    && Directory.GetLastWriteTimeUtc(dir).Ticks <= currentStamp)
                {
                    pruned = true;
                }
                if (pruned)
                {
                    result.DirsPruned++;
                    string prefix = relativePrefix + "/";
                    while (pending is not null && pending.RelativePath.StartsWith(prefix, StringComparison.Ordinal))
                    {
                        WriteEntry(pending);
                        pending = ReadNext(store!);
                    }
                    return;
                }

                foreach (string full in items)
                {
                    string name = Path.GetFileName(full);
                    string rel = relativePrefix.Length == 0 ? name : relativePrefix + "/" + name;
                    if (Directory.Exists(full))
                    {
                        bool skip = false;
                        for (int i = 0; i < options.SkipDirectoryNames.Length; i++)
                        {
                            if (string.Equals(options.SkipDirectoryNames[i], name, StringComparison.Ordinal))
                            {
                                skip = true;
                                break;
                            }
                        }
                        if (!skip)
                        {
                            Walk(full, rel, currentStamp);
                        }
                        continue;
                    }
                    if (options.IncludeFileNameSuffixes.Length > 0)
                    {
                        bool ok = false;
                        for (int i = 0; i < options.IncludeFileNameSuffixes.Length; i++)
                        {
                            if (rel.EndsWith(options.IncludeFileNameSuffixes[i], StringComparison.Ordinal))
                            {
                                ok = true;
                                break;
                            }
                        }
                        if (!ok)
                        {
                            continue;
                        }
                    }

                    var info = new FileInfo(full);
                    var entry = new RecallFileEntry
                    {
                        RelativePath = rel,
                        Size = info.Length,
                        MtimeTicks = info.LastWriteTimeUtc.Ticks,
                    };
                    if (entry.MtimeTicks > maxMtime)
                    {
                        maxMtime = entry.MtimeTicks;
                    }
                    result.FilesSeen++;

                    while (pending is not null && string.CompareOrdinal(pending.RelativePath, rel) < 0)
                    {
                        result.Deleted.Add(pending);
                        pending = ReadNext(store!);
                    }
                    if (pending is not null && string.Equals(pending.RelativePath, rel, StringComparison.Ordinal))
                    {
                        if (pending.Size != entry.Size || pending.MtimeTicks != entry.MtimeTicks)
                        {
                            result.Modified.Add(entry);
                        }
                        pending = ReadNext(store!);
                    }
                    else
                    {
                        result.Added.Add(entry);
                    }
                    WriteEntry(entry);
                }
            }

            void WriteEntry(RecallFileEntry entry)
            {
                var pathBytes = System.Text.Encoding.UTF8.GetBytes(entry.RelativePath);
                VarInt.WriteTo(writer, (ulong)pathBytes.Length);
                writer.Write(pathBytes);
                VarInt.WriteTo(writer, (ulong)entry.Size);
                VarInt.WriteTo(writer, (ulong)entry.MtimeTicks);
                entriesWritten++;
            }

            // 尾部写完后回填两个头的 varint (变长 ⇒ 追加式重写, 保证自描述且无空洞)
            writer.Flush();
            writer.Dispose();
            BackfillHeader(tmpPath, ticksPos, countPos, endPos, stamp, entriesWritten);
        }

        store?.Dispose();
        File.Move(tmpPath, storePath, true);
        sw.Stop();
        result.ElapsedMs = sw.ElapsedMilliseconds;
        return result;
    }

    /// <summary>把头部两个占位 varint 用最终值重写: 尾部整体后移/前移, 结果仍为合法自描述格式。</summary>
    private static void BackfillHeader(string path, long ticksPos, long countPos, long endPos, ulong stamp, long count)
    {
        var ticksBytes = new ByteBuffer(16);
        ticksBytes.WriteVarInt(stamp);
        var countBytes = new ByteBuffer(16);
        countBytes.WriteVarInt((ulong)count);
        int oldBytes = (int)(endPos - (countPos + 1));
        using var fs = new FileStream(path, FileMode.Open, FileAccess.ReadWrite, FileShare.None);
        var tail = new byte[oldBytes];
        fs.Seek(countPos + 1, SeekOrigin.Begin);
        ReadFull(fs, tail);
        fs.Seek(ticksPos, SeekOrigin.Begin);
        fs.Write(ticksBytes.Span);
        fs.Write(countBytes.Span);
        fs.Write(tail);
        fs.SetLength(ticksPos + ticksBytes.Length + countBytes.Length + tail.Length);
    }

    private static void ReadFull(Stream s, byte[] dst)
    {
        int done = 0;
        while (done < dst.Length)
        {
            int n = s.Read(dst, done, dst.Length - done);
            if (n <= 0)
            {
                throw new RecallFormatException("short read while rewriting fingerprint header");
            }
            done += n;
        }
    }

    private static RecallFileEntry? ReadNext(RecallSequentialReader store)
    {
        if (!store.TryReadVarInt(out ulong pathLen))
        {
            return null;
        }
        if (!store.TryReadBytes((int)pathLen, out var pathBytes))
        {
            throw new RecallFormatException("truncated fingerprint entry (path)");
        }
        if (!store.TryReadVarInt(out ulong size) || !store.TryReadVarInt(out ulong ticks))
        {
            throw new RecallFormatException("truncated fingerprint entry (stat)");
        }
        return new RecallFileEntry
        {
            RelativePath = System.Text.Encoding.UTF8.GetString(pathBytes),
            Size = (long)size,
            MtimeTicks = (long)ticks,
        };
    }
}
