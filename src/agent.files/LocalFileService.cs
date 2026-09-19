using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace agent.files;

/// <summary>
/// 本地文件服务（RF0003 默认实现）— 单路径互斥 + 乐观并发 + 写前必备份 + 原子替换 + TOCTOU 二次核对。
/// 任一失败路径都保证盘上原文件零改动（除写盘成功那一刻）。
/// </summary>
public sealed class LocalFileService : IFileService
{
    private readonly FileServiceOptions _options;
    private readonly FileBackupStore _backups;
    private readonly ConcurrentDictionary<string, SemaphoreSlim> _locks = new(StringComparer.Ordinal);

    public LocalFileService(FileServiceOptions options)
    {
        _options = options ?? new FileServiceOptions();
        Root = Path.GetFullPath(_options.WorkspaceRoot ?? Directory.GetCurrentDirectory());
        _backups = new FileBackupStore(Path.GetFullPath(_options.BackupRoot ?? Path.Combine(Root, ".filedb")));
    }

    public string Root { get; }

    /// <summary>备份库（供审计/恢复）。</summary>
    public FileBackupStore Backups => _backups;

    public Task<FileSnapshot> SnapshotAsync(string path, CancellationToken ct = default)
        => Task.Run(() => TakeSnapshot(Resolve(path)), ct);

    public Task<string?> ReadTextAsync(string path, CancellationToken ct = default)
        => Task.Run(() =>
        {
            var full = Resolve(path);
            if (!File.Exists(full))
            {
                return null;
            }
            return TextCodec.TryDecode(File.ReadAllBytes(full), out var text) ? text : null;
        }, ct);

    public async Task<FileEditResult> ApplyAsync(FileEditRequest request, CancellationToken ct = default)
    {
        var full = Resolve(request.Path);
        var gate = _locks.GetOrAdd(full, _ => new SemaphoreSlim(1, 1));
        await gate.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            return await Task.Run(() => ApplyCore(full, request), ct).ConfigureAwait(false);
        }
        finally
        {
            gate.Release();
        }
    }

    public IReadOnlyList<FileBackupRecord> ListBackups(string path) => _backups.List(Resolve(path));

    public FileEditResult Restore(FileBackupRecord record)
    {
        var full = Resolve(record.OriginalPath);
        var result = new FileEditResult { Path = full, Snapshot = TakeSnapshot(full) };
        var gate = _locks.GetOrAdd(full, _ => new SemaphoreSlim(1, 1));
        gate.Wait();
        try
        {
            if (File.Exists(full))
            {
                var current = File.ReadAllBytes(full);
                var backup = _backups.Ensure(full, current, "restore");
                if (backup is null && _options.RequireBackup)
                {
                    result.Outcome = FileEditOutcome.Rejected;
                    result.Note = "还原前备份失败 ⇒ 拒绝还原（fail-closed）";
                    return result;
                }
                if (backup is not null)
                {
                    result.BackupPath = backup.BlobPath;
                    result.BackupSha256 = backup.Sha256;
                }
            }
            if (!_backups.Restore(record, full))
            {
                result.Outcome = FileEditOutcome.Rejected;
                result.Note = "备份 blob 缺失或不可写，还原失败";
                return result;
            }
            _backups.Prune(full, _options.KeepPerFile);
            result.Outcome = FileEditOutcome.Applied;
            result.Note = "已按备份还原";
            result.Snapshot = TakeSnapshot(full);
            return result;
        }
        finally
        {
            gate.Release();
        }
    }

    private FileEditResult ApplyCore(string full, FileEditRequest request)
    {
        var result = new FileEditResult { Path = full };
        if (!InRoot(full))
        {
            result.Outcome = FileEditOutcome.Rejected;
            result.Note = "路径越界（超出工作区根），拒绝访问";
            return result;
        }

        var exists = File.Exists(full);
        var currentBytes = exists ? File.ReadAllBytes(full) : Array.Empty<byte>();
        string currentText = string.Empty;
        if (exists && !TextCodec.TryDecode(currentBytes, out currentText))
        {
            result.Outcome = FileEditOutcome.Rejected;
            result.Note = "现盘非 UTF-8 文本，拒绝改写（可备份后人工处理）";
            result.Snapshot = TakeSnapshot(full);
            return result;
        }

        var currentSha = exists ? ContentHash.OfBytes(currentBytes) : string.Empty;
        var fast = exists
            ? request.ExpectedSha256.Length == 0 || string.Equals(currentSha, request.ExpectedSha256, StringComparison.OrdinalIgnoreCase)
            : request.ExpectedSha256.Length == 0;
        if (fast)
        {
            return WriteFile(full, currentSha, request.NewText, request.Source, result, "fast-path");
        }

        if (!exists)
        {
            result.Outcome = FileEditOutcome.StaleBase;
            result.Note = "期望版本存在但现盘已无该文件（被删/被移）⇒ 拒绝写入";
            result.Snapshot = FileSnapshot.Missing(full);
            return result;
        }

        if (!_options.AllowMerge)
        {
            result.Outcome = FileEditOutcome.StaleBase;
            result.Note = "现盘已变更且合并没有打开 ⇒ 拒绝写入，要求重读";
            result.Snapshot = TakeSnapshot(full);
            return result;
        }

        var baseText = request.BaseText;
        if (baseText is null && request.ExpectedSha256.Length > 0 && _backups.TryReadText(request.ExpectedSha256, out var fromBackup))
        {
            baseText = fromBackup;
        }
        if (baseText is null)
        {
            result.Outcome = FileEditOutcome.StaleBase;
            result.Note = "缺 base（未给 BaseText 且备份库无该版本）⇒ 拒绝写入，要求重读";
            result.Snapshot = TakeSnapshot(full);
            return result;
        }

        var outcome = ThreeWayLineMerge.Merge(
            SplitLines(baseText),
            SplitLines(currentText),
            SplitLines(request.NewText),
            _options.MaxMergeLines);
        if (outcome is null)
        {
            result.Outcome = FileEditOutcome.Rejected;
            result.Note = "超出合并行数上限 ⇒ 拒绝自动合并，交人工";
            result.Snapshot = TakeSnapshot(full);
            return result;
        }
        if (!outcome.Clean)
        {
            result.Outcome = FileEditOutcome.Conflict;
            result.Conflicts = outcome.Conflicts;
            result.MergedText = RenderConflicts(currentText, request.NewText, outcome);
            result.Note = "两侧改动重叠 ⇒ 未写盘，交人裁定";
            result.Snapshot = TakeSnapshot(full);
            return result;
        }

        var newline = DetectNewline(currentText);
        var mergedText = JoinLines(outcome.MergedLines, newline, currentText.EndsWith(newline, StringComparison.Ordinal));
        result.MergedText = mergedText;
        var merged = WriteFile(full, currentSha, mergedText, request.Source, result, "merged");
        if (merged.Wrote)
        {
            merged.Outcome = FileEditOutcome.MergedAuto;
        }
        return merged;
    }

    private FileEditResult WriteFile(
        string full,
        string basedOnSha,
        string text,
        string source,
        FileEditResult result,
        string note)
    {
        var nowExists = File.Exists(full);
        var nowSha = nowExists ? ContentHash.OfBytes(File.ReadAllBytes(full)) : string.Empty;
        if (!string.Equals(nowSha, basedOnSha, StringComparison.OrdinalIgnoreCase))
        {
            result.Outcome = FileEditOutcome.StaleBase;
            result.Note = "写前二次核对发现现盘再变（TOCTOU）⇒ 拒绝写入";
            result.Snapshot = TakeSnapshot(full);
            return result;
        }

        if (nowExists)
        {
            var backup = _backups.Ensure(full, File.ReadAllBytes(full), source);
            if (backup is null && _options.RequireBackup)
            {
                result.Outcome = FileEditOutcome.Rejected;
                result.Note = "备份失败 ⇒ 拒绝写入（fail-closed）";
                result.Snapshot = TakeSnapshot(full);
                return result;
            }
            if (backup is not null)
            {
                result.BackupPath = backup.BlobPath;
                result.BackupSha256 = backup.Sha256;
                _backups.Prune(full, _options.KeepPerFile);
            }
        }

        var dir = Path.GetDirectoryName(full);
        if (!string.IsNullOrEmpty(dir))
        {
            Directory.CreateDirectory(dir);
        }
        var tmp = full + "." + Guid.NewGuid().ToString("N")[..8] + ".tmp";
        File.WriteAllBytes(tmp, TextCodec.Encode(text));
        File.Move(tmp, full, true);
        result.Outcome = FileEditOutcome.Applied;
        result.Note = note;
        result.Snapshot = TakeSnapshot(full);
        return result;
    }

    private string Resolve(string path)
        => Path.GetFullPath(Path.IsPathRooted(path) ? path : Path.Combine(Root, path));

    private bool InRoot(string full)
        => string.Equals(full, Root, StringComparison.Ordinal)
           || full.StartsWith(Root + Path.DirectorySeparatorChar, StringComparison.Ordinal);

    private static FileSnapshot TakeSnapshot(string full)
    {
        if (!File.Exists(full))
        {
            return FileSnapshot.Missing(full);
        }
        var bytes = File.ReadAllBytes(full);
        return new FileSnapshot
        {
            Path = full,
            Exists = true,
            Sha256 = ContentHash.OfBytes(bytes),
            Bytes = bytes.LongLength,
            LastWriteUtcTicks = File.GetLastWriteTimeUtc(full).Ticks,
        };
    }

    private static string DetectNewline(string text)
        => text.Contains("\r\n", StringComparison.Ordinal) ? "\r\n" : "\n";

    private static List<string> SplitLines(string text)
    {
        var res = new List<string>();
        if (text.Length == 0)
        {
            return res;
        }
        var parts = text.Split('\n');
        var last = parts.Length - 1;
        for (var i = 0; i < parts.Length; i++)
        {
            if (i == last && parts[i].Length == 0)
            {
                break;
            }
            var line = parts[i];
            if (line.Length > 0 && line[^1] == '\r')
            {
                line = line[..^1];
            }
            res.Add(line);
        }
        return res;
    }

    private static string JoinLines(List<string> lines, string newline, bool trailingNewline)
    {
        var sb = new StringBuilder();
        for (var i = 0; i < lines.Count; i++)
        {
            sb.Append(lines[i]);
            if (i < lines.Count - 1 || trailingNewline)
            {
                sb.Append(newline);
            }
        }
        return sb.ToString();
    }

    private static string RenderConflicts(string ours, string theirs, MergeOutcome outcome)
    {
        var sb = new StringBuilder();
        sb.Append("<<<<<<< ours(现盘)\n").Append(ours);
        if (!ours.EndsWith('\n'))
        {
            sb.Append('\n');
        }
        sb.Append("=======\n").Append(theirs);
        if (!theirs.EndsWith('\n'))
        {
            sb.Append('\n');
        }
        sb.Append(">>>>>>> theirs(本次)\n");
        sb.Append("-- 冲突块 ").Append(outcome.Conflicts.Count).Append(" 处\n");
        return sb.ToString();
    }
}
