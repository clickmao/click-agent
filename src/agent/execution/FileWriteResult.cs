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
