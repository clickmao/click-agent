// R480: 独立文本召回模块 —— 增量保鲜编排 (判脏 → 只重建脏文档 → 段追加 + tombstone)。
// 语言无关: 是否「文本」由内容探测 (NUL/控制字节比例) 判定, 不看文件后缀。
using System.Text;

namespace agent.recall;

public static class RecallIndexUpdater
{
    /// <summary>一次保鲜调用: 判脏 (未变则零写入) → 只重建脏文档。</summary>
    public static RecallUpdateReport Update(string root, string indexPath, RecallUpdateOptions options)
    {
        var report = new RecallUpdateReport { Root = root, IndexDirectory = indexPath };
        string storePath = Path.Combine(indexPath, RecallConstants.FingerprintFile);
        var scan = RecallDirtyScan.Scan(root, storePath, options.Scan);
        report.ScanMs = scan.ElapsedMs;
        report.FilesSeen = scan.FilesSeen;
        report.DirsVisited = scan.DirsVisited;
        report.DirsPruned = scan.DirsPruned;
        report.VerifiedAllDirs = scan.VerifiedAllDirs;
        report.PrevScanPruned = scan.PrevScanPruned;
        report.Added = scan.Added.Count;
        report.Modified = scan.Modified.Count;
        report.Deleted = scan.Deleted.Count;
        if (!scan.Dirty)
        {
            return report;
        }

        var sw = System.Diagnostics.Stopwatch.StartNew();
        // 文档键 = 相对「索引目录的父目录」的路径 (索引在 <base>/index, 扫描根可为 base 下任意子树)。
        string baseDir = Path.GetDirectoryName(Path.GetFullPath(indexPath)) ?? indexPath;
        string scanDir = Path.GetFullPath(root);
        string prefix = Path.GetRelativePath(baseDir, scanDir).Replace('\\', '/');
        if (prefix == ".")
        {
            prefix = string.Empty;
        }
        else if (prefix.Length > 0 && !prefix.EndsWith('/'))
        {
            prefix += "/";
        }

        string KeyOf(string rel) => prefix.Length == 0 ? rel : prefix + rel;

        using var builder = File.Exists(Path.Combine(indexPath, RecallConstants.IndexMetaFile))
            ? RecallIndexBuilder.Open(indexPath)
            : RecallIndexBuilder.Create(indexPath);
        foreach (var entry in scan.Deleted)
        {
            report.DocsRemoved += builder.DeleteByKey(KeyOf(entry.RelativePath));
        }
        foreach (var entry in scan.Modified.Concat(scan.Added))
        {
            string full = Path.Combine(root, entry.RelativePath.Replace('/', Path.DirectorySeparatorChar));
            byte[] bytes;
            try
            {
                var info = new FileInfo(full);
                if (info.Length > options.MaxFileBytes)
                {
                    continue;
                }
                bytes = File.ReadAllBytes(full);
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
            {
                continue;
            }
            if (RecallTextProbe.LooksBinary(bytes, options.BinaryNulRatio))
            {
                continue;
            }
            builder.DeleteByKey(KeyOf(entry.RelativePath));
            string text = Encoding.UTF8.GetString(bytes);
            var chunks = RecallChunker.Split(text, options.ChunkChars);
            var docs = new List<RecallSourceDoc>(chunks.Count);
            for (int i = 0; i < chunks.Count; i++)
            {
                string key = KeyOf(entry.RelativePath);
                docs.Add(new RecallSourceDoc
                {
                    Id = chunks.Count == 1 ? key : key + "#" + i,
                    Path = key,
                    Text = chunks[i],
                    Size = bytes.Length,
                    MtimeTicks = entry.MtimeTicks,
                    Inode = 0,
                });
            }
            builder.Add(docs);
            report.DocsIndexed += docs.Count;
        }
        report.IndexMs = sw.ElapsedMilliseconds;
        report.WroteIndex = true;
        return report;
    }
}
