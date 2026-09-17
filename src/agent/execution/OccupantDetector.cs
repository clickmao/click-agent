using System;
using System.IO;
using System.Text;
using System.Threading;

namespace agent.execution;

/// <summary>T2: 占用者检测。锁文件内容 = 持有 pid (最快路径); 无 pid 时读 /proc/locks (Linux)。
/// stale 判定: /proc/&lt;pid&gt; 不存在 → 持有者已死 → 清除锁文件让 TryAcquire 接管。</summary>
public static class OccupantDetector
{
    /// <summary>T2: 占用者检测。快路径: 锁文件 pid 可读 (FileShare 允许读的平台); 主路径: /proc/locks
    /// (Linux, 持有者崩溃自动放锁后由 flock 保证, 此路径用于活持有者报告)。
    /// stale 判定: /proc/&lt;pid&gt; 不存在 → 持有者已死 → 清除锁文件让 TryAcquire 接管。</summary>
    public static string Describe(string targetPath)
    {
        var lockPath = targetPath + ".lock";
        // 主路径: /proc/locks 里的**活持有者** (锁加了 inode, 与文件是否可读无关)
        var byLocks = ScanProcLocks(lockPath);
        if (!string.IsNullOrEmpty(byLocks)) return byLocks;
        // 次路径: 锁文件内容 = 最后持有者 pid (文件长期保留 ⇒ 须判活, 否则会把已退出的持有者报成占用者)
        try
        {
            if (File.Exists(lockPath))
            {
                var pid = File.ReadAllText(lockPath).Trim();
                if (int.TryParse(pid, out var p) && p > 0)
                {
                    return Directory.Exists($"/proc/{p}")
                        ? $"PID {p} ({ReadComm(p)}) 持有锁 {Path.GetFileName(lockPath)}"
                        : $"无持有者 (锁文件保留; 上次持有者 PID {p} 已退出)";
                }
            }
        }
        catch { /* 读被拒 → 未知 */ }
        return "未知占用者 (平台无 /proc/locks 或锁未记录)";
    }

    private static string ReadComm(int pid)
    {
        try
        {
            var comm = File.ReadAllText($"/proc/{pid}/comm").Trim();
            return string.IsNullOrEmpty(comm) ? "unknown" : comm;
        }
        catch { return "unknown"; }
    }

    /// <summary>解析 /proc/locks: 找持有 lockPath inode 的 FLOCK/POSIX 记录 → "PID x (comm)"。
    /// 行格式实证 (Linux 6.8): "1: FLOCK ADVISORY WRITE 2570875 fd:02:50855 0 EOF" —
    /// pid 是含 inode 段 (…:50855) 的**前一项**, 不能用固定 index (跨内核版本 parts 数不同)。</summary>
    private static string ScanProcLocks(string lockPath)
    {
        try
        {
            if (!File.Exists("/proc/locks")) return "";
            var inode = GetInode(lockPath);
            if (inode <= 0) return "";
            var needle = ":" + inode;
            foreach (var line in File.ReadAllLines("/proc/locks"))
            {
                var parts = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                if (parts.Length < 3) continue;
                for (var k = 1; k < parts.Length; k++)
                {
                    if (parts[k].EndsWith(needle, StringComparison.Ordinal)
                        && int.TryParse(parts[k - 1], out var pid) && pid > 0)
                        return $"PID {pid} ({ReadComm(pid)})";
                }
            }
            return "";
        }
        catch { return ""; }
    }

    private static long GetInode(string path)
    {
        try
        {
            var fi = new FileInfo(path);
            if (!fi.Exists) return -1;
            // FileInfo 不暴露 inode — 用 stat 命令 (Linux) 或返回 -1 (降级)
            var psi = new System.Diagnostics.ProcessStartInfo("stat", $"-c %i \"{path}\"")
            {
                RedirectStandardOutput = true, UseShellExecute = false,
            };
            using var p = System.Diagnostics.Process.Start(psi);
            if (p is null) return -1;
            var s = p.StandardOutput.ReadToEnd().Trim();
            p.WaitForExit(1000);
            return long.TryParse(s, out var ino) ? ino : -1;
        }
        catch { return -1; }
    }

    /// <summary>R465: 锁文件内容 pid 对应的进程是否已退出 (只读探测, **不删文件**)。
    /// 保留本方法只为诊断/审计可读性; 锁的接管不再依赖它 (内核在持有者退出时自动放锁)。</summary>
    public static bool IsHolderDead(string lockPath)
    {
        try
        {
            if (!File.Exists(lockPath)) return true;
            var content = File.ReadAllText(lockPath).Trim();
            if (!int.TryParse(content, out var pid) || pid <= 0) return false; // 无 pid 信息, 不擅断
            return !Directory.Exists($"/proc/{pid}");
        }
        catch { return false; }
    }
}
