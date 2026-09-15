// R480: 独立文本召回模块 —— 增量保鲜编排 (判脏 → 只重建脏文档 → 段追加 + tombstone)。
// 语言无关: 是否「文本」由内容探测 (NUL/控制字节比例) 判定, 不看文件后缀。
using System.Text;

namespace agent.Recall;

public sealed class RecallUpdateOptions
{
    public RecallWriteOptions Write { get; init; } = new();
    public RecallScanOptions Scan { get; init; } = new();
    public int ChunkChars { get; init; } = 512;
    public long MaxFileBytes { get; init; } = 2_000_000;
    public double BinaryNulRatio { get; init; } = 0.02;
}

public sealed class RecallUpdateReport
{
    public required string Root { get; init; }
    public required string IndexDirectory { get; init; }
    public long ScanMs { get; set; }
    public long IndexMs { get; set; }
    public int FilesSeen { get; set; }
    public int DirsVisited { get; set; }
    public int DirsPruned { get; set; }
    /// <summary>本轮为「全量核验轮」(因上轮剪枝而抑制剪枝) ⇒ 该轮 DirsPruned 恒为 0 (§D9)。</summary>
    public bool VerifiedAllDirs { get; set; }
    /// <summary>上轮扫描是否发生过剪枝 (决定本轮是否必须核验)。</summary>
    public bool PrevScanPruned { get; set; }
    public int Added { get; set; }
    public int Modified { get; set; }
    public int Deleted { get; set; }
    public int DocsIndexed { get; set; }
    public int DocsRemoved { get; set; }
    public bool WroteIndex { get; set; }

    /// <summary>本次是否有脏 (判脏快速路径: 无脏则索引面零写入)。</summary>
    public bool Dirty => Added + Modified + Deleted > 0;
    public long TotalMs => ScanMs + IndexMs;
}

public static class RecallTextProbe
{
    /// <summary>通用二进制探测: NUL 字节占比超阈值即视为非文本 (与后缀无关)。</summary>
    public static bool LooksBinary(ReadOnlySpan<byte> bytes, double nulRatio)
    {
        if (bytes.Length == 0)
        {
            return false;
        }
        int nul = 0;
        for (int i = 0; i < bytes.Length; i++)
        {
            if (bytes[i] == 0)
            {
                nul++;
            }
        }
        return nul > 0 && (double)nul / bytes.Length > nulRatio;
    }
}

public static class RecallChunker
{
    /// <summary>按段落边界切块, 单块不超过 chunkChars (超长段落硬切), 保留原文, 无重叠。</summary>
    public static List<string> Split(string text, int chunkChars)
    {
        if (chunkChars < 64)
        {
            chunkChars = 64;
        }
        var parts = new List<string>();
        var cur = new StringBuilder();
        int i = 0;
        while (i < text.Length)
        {
            int nl = text.IndexOf('\n', i);
            if (nl < 0)
            {
                nl = text.Length;
            }
            int len = nl - i + (nl < text.Length ? 1 : 0);
            if (cur.Length > 0 && cur.Length + len > chunkChars)
            {
                parts.Add(cur.ToString());
                cur.Clear();
            }
            if (len > chunkChars)
            {
                for (int p = i; p < nl; p += chunkChars)
                {
                    int take = Math.Min(chunkChars, nl - p);
                    if (cur.Length > 0)
                    {
                        parts.Add(cur.ToString());
                        cur.Clear();
                    }
                    parts.Add(text.Substring(p, take));
                }
            }
            else
            {
                cur.Append(text, i, len);
            }
            i = nl + (nl < text.Length ? 1 : 0);
        }
        if (cur.Length > 0)
        {
            parts.Add(cur.ToString());
        }
        return parts;
    }
}

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
