using System;
using System.IO;
using System.Threading;

namespace agent.execution;

/// <summary>
/// v0.17.3 T1 (R340, 用户钦定时序撞车检测): 执行/读取前产物稳定性检测 — 连续两次采样 (间隔稳定窗/2)
/// 的 (size, mtime) 相同 → stable (可安全执行/读取); 不同 → settling (另一进程正在原子替换 —
/// AtomicFileWriter tmp→Move / dotnet publish 覆盖输出)。事故实证: AOT publish 覆盖 agenthost 时被并发
/// 执行 → 跑了旧版二进制 → /git 落 LLM 幻觉 (表象), 真因=写-读撞车无检测。
/// 语义: 检测+警告+重试 (IsSettling→Sleep→复查), 不升级为锁 (读方加共享锁会阻塞 AtomicFileWriter)。
/// </summary>
public static class CollisionDetector
{
    public static bool IsSettling(string path, int minStableMs = 500, Func<int>? sleepMs = null)
    {
        try
        {
            if (!File.Exists(path)) return false; // 不存在无从撞 (创建中由调用方语义处理)
            var fi1 = new FileInfo(path);
            fi1.Refresh();
            var s1 = (fi1.Length, fi1.LastWriteTimeUtc.Ticks);
            Thread.Sleep(Math.Max(20, minStableMs / 2));
            var fi2 = new FileInfo(path);
            fi2.Refresh();
            var s2 = (fi2.Length, fi2.LastWriteTimeUtc.Ticks);
            return s1 != s2; // 两次采样不同 → 仍在写入
        }
        catch (IOException) { return true; } // 读取竞争 (独占写中) → 视为 settling
        catch (UnauthorizedAccessException) { return true; }
    }

    /// <summary>执行前守卫: 若产物 settling, 等待至稳定 (最多 waitMs), 返回是否已稳定可执行。
    /// 仍不稳定 → false (调用方决定拒绝执行或带警告执行 — 默认拒绝, 防跑旧版/半程)。</summary>
    public static bool WaitUntilStable(string path, int waitMs = 2000, int minStableMs = 500)
    {
        var deadline = DateTime.UtcNow.AddMilliseconds(waitMs);
        while (IsSettling(path, minStableMs))
        {
            if (DateTime.UtcNow >= deadline)
            {
                AgentLessonRecord.Record($"artifact-collision:{Path.GetFileName(path)}",
                    $"产物 {path} 持续被并发写入 (>{waitMs}ms) — 拒绝执行防旧版/半程",
                    "等待写入完成 (AtomicFileWriter rename 原子) 后重试; 或检查另一发布/写进程");
                return false;
            }
            Thread.Sleep(150);
        }
        return true;
    }
}

/// <summary>教训记录轻桥 (避免 CollisionDetector 直接依赖具体 lesson 存储 — 用默认单例)。</summary>
internal static class AgentLessonRecord
{
    public static void Record(string pattern, string summary, string solution)
        => agent.execution.ExecutorLessonMemory.Default.Record(pattern, summary, solution, "CollisionDetector 时序撞车");
}
