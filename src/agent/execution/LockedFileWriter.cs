using System;
using System.IO;

namespace agent.execution;

/// <summary>v0.17.0 T1: 加锁文件写结果 (结构化失败原因 — 供 ExecutorLessonMemory 记录与调用方决策)。</summary>
public sealed class FileWriteResult
{
    public bool Success { get; init; }
    public string Path { get; init; } = "";
    public string? Occupant { get; init; }        // T2 占用者描述 ("PID 123 (agenthost)")
    public long WaitMs { get; init; }
    public string? ErrorKind { get; init; }        // lock-timeout / io / merged / overwritten
    public string? ErrorDetail { get; init; }
    public bool Merged { get; init; }              // 发生差异合并
    public static FileWriteResult Ok(string path, bool merged = false, long waitMs = 0)
        => new() { Success = true, Path = path, Merged = merged, WaitMs = waitMs, ErrorKind = merged ? "merged" : null };
    public static FileWriteResult Fail(string path, string kind, string detail, string? occupant = null, long waitMs = 0)
        => new() { Success = false, Path = path, ErrorKind = kind, ErrorDetail = detail, Occupant = occupant, WaitMs = waitMs };
}

/// <summary>冲突合并策略 (LockedFileWriter.Write)。</summary>
public enum ConflictStrategy
{
    /// <summary>直接覆盖 (最后写者胜) — 适合幂等全量快照。</summary>
    Overwrite,
    /// <summary>目标已存在且内容不同 → 不覆盖 (先写者胜), 返回 merged=true 表示让位。防双写互踩。</summary>
    KeepExisting,
}

/// <summary>
/// v0.17.0 T1/T2 (R334, 用户钦定场景): 跨进程加锁写 — 拿 FileLock (失败 → 结构化原因含 T2 占用者
/// "PID x (comm)" + 退避观察重试至 timeout) → 按 ConflictStrategy 差异处理 → AtomicFileWriter 写回。
/// 用户例: "2 个 agent 同时写入 1 个文件 → 文件被占用 → 提示占用者是谁 → 持续等待观察 → 比较差异继续任务"。
/// </summary>
public static class LockedFileWriter
{
    public static FileWriteResult Write(string path, string content, ConflictStrategy strategy,
        TimeSpan acquireTimeout, Action<string>? occupantLogger = null)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        using var fileLock = new FileLock(path);
        if (!fileLock.TryAcquire(acquireTimeout))
        {
            var occupant = OccupantDetector.Describe(path);
            occupantLogger?.Invoke($"⚠ 文件 {path} 被占用: {occupant} (等待 {acquireTimeout.TotalSeconds:0}s 后放弃)");
            return FileWriteResult.Fail(path, "lock-timeout", $"acquire timeout {acquireTimeout.TotalSeconds:0}s", occupant, sw.ElapsedMilliseconds);
        }
        try
        {
            if (strategy == ConflictStrategy.KeepExisting && File.Exists(path))
            {
                var existing = File.ReadAllText(path);
                if (existing.Length > 0 && existing != content)
                {
                    occupantLogger?.Invoke($"ℹ 文件 {path} 已有其他写入者内容, KeepExisting 让位 (不覆盖, 防双写互踩)");
                    return FileWriteResult.Ok(path, merged: true, sw.ElapsedMilliseconds);
                }
            }
            AtomicFileWriter.WriteAllText(path, content);
            return FileWriteResult.Ok(path, waitMs: sw.ElapsedMilliseconds);
        }
        catch (Exception ex)
        {
            return FileWriteResult.Fail(path, "io", ex.Message, OccupantDetector.Describe(path), sw.ElapsedMilliseconds);
        }
    }

    /// <summary>v0.17.0 T4: 锁内条件覆盖 — allowOverwrite(现有内容) 为 true 才覆盖 (如"同 Id 状态推进"),
    /// false 让位 (merged) 防异主互踩。判定与写入同锁原子, 无 TOCTOU 窗口。</summary>
    public static FileWriteResult WriteIf(string path, string content, Func<string?, bool> allowOverwrite,
        TimeSpan acquireTimeout, Action<string>? occupantLogger = null)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        using var fileLock = new FileLock(path);
        if (!fileLock.TryAcquire(acquireTimeout))
        {
            var occupant = OccupantDetector.Describe(path);
            occupantLogger?.Invoke($"⚠ 文件 {path} 被占用: {occupant} (等待 {acquireTimeout.TotalSeconds:0}s 后放弃)");
            return FileWriteResult.Fail(path, "lock-timeout", $"acquire timeout {acquireTimeout.TotalSeconds:0}s", occupant, sw.ElapsedMilliseconds);
        }
        try
        {
            string? existing = null;
            if (File.Exists(path))
            {
                existing = File.ReadAllText(path);
                if (existing.Length > 0 && !allowOverwrite(existing))
                {
                    occupantLogger?.Invoke($"ℹ 文件 {path} 已存在且 allowOverwrite=false → 让位 (不覆盖)");
                    return FileWriteResult.Ok(path, merged: true, sw.ElapsedMilliseconds);
                }
            }
            AtomicFileWriter.WriteAllText(path, content);
            return FileWriteResult.Ok(path, waitMs: sw.ElapsedMilliseconds);
        }
        catch (Exception ex)
        {
            return FileWriteResult.Fail(path, "io", ex.Message, OccupantDetector.Describe(path), sw.ElapsedMilliseconds);
        }
    }
}
