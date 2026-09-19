using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.Json;

namespace agent.files;

/// <summary>
/// 备份库（RF0003 Q1–Q3）— 内容寻址 blob + append-only 索引 + 保留策略 + 恢复。
/// 硬保证: 写盘前必经 <see cref="Ensure"/>；返回 null 时调用方必须拒写（fail-closed）。
/// </summary>
public sealed class FileBackupStore
{
    private readonly object _gate = new();
    private readonly string _blobDir;
    private readonly string _indexPath;

    public FileBackupStore(string root)
    {
        Root = root;
        _blobDir = Path.Combine(root, "backups");
        _indexPath = Path.Combine(root, "backup-index.jsonl");
    }

    /// <summary>备份库根目录。</summary>
    public string Root { get; }

    /// <summary>索引文件路径（append-only jsonl，可审计）。</summary>
    public string IndexPath => _indexPath;

    /// <summary>落一份备份（内容寻址；同内容复用 blob）。失败返回 null。</summary>
    public FileBackupRecord? Ensure(string path, byte[] content, string source)
    {
        try
        {
            lock (_gate)
            {
                Directory.CreateDirectory(_blobDir);
                var sha = ContentHash.OfBytes(content);
                var blob = Path.Combine(_blobDir, ContentHash.Short(sha, 16));
                var needWrite = true;
                if (File.Exists(blob))
                {
                    needWrite = new FileInfo(blob).Length != content.LongLength;
                }
                if (needWrite)
                {
                    var tmp = blob + ".tmp";
                    File.WriteAllBytes(tmp, content);
                    File.Move(tmp, blob, true);
                }
                var rec = new FileBackupRecord
                {
                    Sha256 = sha,
                    Bytes = content.LongLength,
                    OriginalPath = path,
                    TakenUtcTicks = DateTime.UtcNow.Ticks,
                    BlobPath = blob,
                    Source = source,
                };
                File.AppendAllText(
                    _indexPath,
                    JsonSerializer.Serialize(rec, FileServiceJsonContext.Default.FileBackupRecord) + "\n",
                    new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
                return rec;
            }
        }
        catch (IOException)
        {
            return null;
        }
        catch (UnauthorizedAccessException)
        {
            return null;
        }
        catch (NotSupportedException)
        {
            return null;
        }
    }

    /// <summary>某原文件的备份记录（时间升序；同刻按索引先后 = 稳定序）。</summary>
    public IReadOnlyList<FileBackupRecord> List(string path)
    {
        var res = new List<FileBackupRecord>();
        foreach (var r in ReadIndex())
        {
            if (string.Equals(r.OriginalPath, path, StringComparison.Ordinal))
            {
                res.Add(r);
            }
        }
        return SortStable(res);
    }

    /// <summary>取最近一条（skipNewest = 0 最新）。</summary>
    public FileBackupRecord? Latest(string path, int skipNewest = 0)
    {
        var list = List(path);
        var idx = list.Count - 1 - skipNewest;
        return idx >= 0 && idx < list.Count ? list[idx] : null;
    }

    /// <summary>按内容 sha 找该文件的某一版备份（三方合并的 base 来源之一）。</summary>
    public FileBackupRecord? BySha(string path, string sha256)
    {
        foreach (var r in List(path))
        {
            if (string.Equals(r.Sha256, sha256, StringComparison.OrdinalIgnoreCase))
            {
                return r;
            }
        }
        return null;
    }

    /// <summary>读回某版备份文本（严格 UTF-8）。</summary>
    public bool TryReadText(string sha256, out string text)
    {
        text = string.Empty;
        try
        {
            var blob = Path.Combine(_blobDir, ContentHash.Short(sha256, 16));
            if (!File.Exists(blob))
            {
                return false;
            }
            return TextCodec.TryDecode(File.ReadAllBytes(blob), out text);
        }
        catch (IOException)
        {
            return false;
        }
    }

    /// <summary>保留策略: 每文件留最近 keep 条索引；无引用 blob 删除。返回删除条数。</summary>
    public int Prune(string path, int keep)
    {
        if (keep < 1)
        {
            keep = 1;
        }
        var all = ReadIndex();
        var mine = new List<FileBackupRecord>();
        foreach (var r in all)
        {
            if (string.Equals(r.OriginalPath, path, StringComparison.Ordinal))
            {
                mine.Add(r);
            }
        }
        mine = SortStable(mine);
        var dropCount = mine.Count - keep;
        if (dropCount <= 0)
        {
            return 0;
        }
        var dropped = new HashSet<string>(StringComparer.Ordinal);
        for (var i = 0; i < dropCount; i++)
        {
            dropped.Add(mine[i].Sha256);
        }
        lock (_gate)
        {
            var kept = new List<FileBackupRecord>();
            foreach (var r in all)
            {
                var isMine = string.Equals(r.OriginalPath, path, StringComparison.Ordinal);
                if (isMine && dropped.Contains(r.Sha256))
                {
                    continue;
                }
                kept.Add(r);
            }
            RewriteIndex(kept);
            foreach (var sha in dropped)
            {
                var referenced = false;
                foreach (var r in kept)
                {
                    if (string.Equals(r.Sha256, sha, StringComparison.Ordinal))
                    {
                        referenced = true;
                        break;
                    }
                }
                if (referenced)
                {
                    continue;
                }
                try
                {
                    var blob = Path.Combine(_blobDir, ContentHash.Short(sha, 16));
                    if (File.Exists(blob))
                    {
                        File.Delete(blob);
                    }
                }
                catch (IOException)
                {
                }
            }
        }
        return dropped.Count;
    }

    /// <summary>按备份记录还原目标文件（逐位还原 blob）。</summary>
    public bool Restore(FileBackupRecord record, string destPath)
    {
        try
        {
            if (!File.Exists(record.BlobPath))
            {
                return false;
            }
            var bytes = File.ReadAllBytes(record.BlobPath);
            var dir = Path.GetDirectoryName(destPath);
            if (!string.IsNullOrEmpty(dir))
            {
                Directory.CreateDirectory(dir);
            }
            var tmp = destPath + "." + Guid.NewGuid().ToString("N")[..8] + ".tmp";
            File.WriteAllBytes(tmp, bytes);
            File.Move(tmp, destPath, true);
            return true;
        }
        catch (IOException)
        {
            return false;
        }
        catch (UnauthorizedAccessException)
        {
            return false;
        }
    }

    private static List<FileBackupRecord> SortStable(List<FileBackupRecord> rows)
    {
        var order = new int[rows.Count];
        for (var i = 0; i < rows.Count; i++)
        {
            order[i] = i;
        }
        for (var i = 1; i < rows.Count; i++)
        {
            var cur = order[i];
            var j = i - 1;
            while (j >= 0 && rows[order[j]].TakenUtcTicks > rows[cur].TakenUtcTicks)
            {
                order[j + 1] = order[j];
                j--;
            }
            order[j + 1] = cur;
        }
        var res = new List<FileBackupRecord>(rows.Count);
        foreach (var idx in order)
        {
            res.Add(rows[idx]);
        }
        return res;
    }

    private List<FileBackupRecord> ReadIndex()
    {
        var res = new List<FileBackupRecord>();
        try
        {
            if (!File.Exists(_indexPath))
            {
                return res;
            }
            foreach (var line in File.ReadAllLines(_indexPath))
            {
                if (line.Length == 0)
                {
                    continue;
                }
                var rec = JsonSerializer.Deserialize(line, FileServiceJsonContext.Default.FileBackupRecord);
                if (rec is not null)
                {
                    res.Add(rec);
                }
            }
        }
        catch (IOException)
        {
        }
        catch (JsonException)
        {
        }
        return res;
    }

    private void RewriteIndex(List<FileBackupRecord> rows)
    {
        var sb = new StringBuilder();
        foreach (var r in rows)
        {
            sb.Append(JsonSerializer.Serialize(r, FileServiceJsonContext.Default.FileBackupRecord)).Append('\n');
        }
        var tmp = _indexPath + ".tmp";
        File.WriteAllText(tmp, sb.ToString(), new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
        File.Move(tmp, _indexPath, true);
    }
}
