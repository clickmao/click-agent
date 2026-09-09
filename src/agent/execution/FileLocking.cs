using System;
using System.IO;
using System.Text;
using System.Threading;

namespace agent.execution;

/// <summary>
/// v0.17.0 T1/T2 (R334, 用户钦定执行层稳固化): 跨进程 advisory 文件锁 + 原子写 + 占用者检测。
/// 解决多 agent/多实例并发写同一文件的竞争族 (R110 telemetry 竞争 / R257 轮号撞号 / 双实例写
/// guardrails|charter|sessions|rag): 锁文件 &lt;path&gt;.lock 以 FileShare.None 持有 (单机内核仲裁),
/// 锁文件内容 = 持有者 pid (T2 占用者检测即刻可答, 无需 lsof)。
/// AOT 兼容: 纯 BCL, 禁反射; Linux /proc 读取, 非 Linux 降级 "未知占用者"。
/// </summary>
public sealed class FileLock : IDisposable
{
    private readonly string _targetPath;
    private FileStream? _stream;
    private bool _disposed;
    private string _ownerPid = "";

    public string LockPath { get; }
    public bool IsHeld => _stream is not null;

    public FileLock(string targetPath)
    {
        _targetPath = targetPath;
        LockPath = targetPath + ".lock";
    }

    public string OwnerPid => _ownerPid;

    /// <summary>尝试拿锁。拿不到时探测 stale (锁文件 pid 已死 → 清除接管), 指数退避轮询至 timeout。</summary>
    public bool TryAcquire(TimeSpan timeout)
    {
        if (IsHeld) return true;
        var deadline = DateTime.UtcNow + timeout;
        var delayMs = 20;
        while (true)
        {
            try
            {
                var fs = new FileStream(LockPath, FileMode.OpenOrCreate, FileAccess.ReadWrite,
                    FileShare.None, 1, FileOptions.WriteThrough);
                // FileShare.None: Unix 映射 flock LOCK_EX (内核仲裁, 持有者进程崩溃 → fd 关闭 → 锁
                // 自动释放 → 下一轮 Open 即成功接管 — stale 无需探测); FileShare.Read 实测不互斥
                // (同进程第二 Open ReadWrite 仍成功, 测试实证)。锁文件 pid 供 Describe 快路径,
                // 读被 None 拒时 Describe 走 /proc/locks (主路径)。
                var pid = Environment.ProcessId.ToString(System.Globalization.CultureInfo.InvariantCulture);
                fs.SetLength(0);
                var buf = Encoding.UTF8.GetBytes(pid);
                fs.Write(buf, 0, buf.Length);
                fs.Flush(true);
                _stream = fs;
                _ownerPid = pid;
                return true;
            }
            catch (IOException)
            {
                if (OccupantDetector.TryBreakStaleLock(LockPath))
                    continue; // stale 锁被清除 → 下一轮重试
            }
            catch (UnauthorizedAccessException)
            {
                // 锁文件被以无写权限方式持有 — 同 stale 探测后重试
            }
            if (DateTime.UtcNow >= deadline)
                return false;
            Thread.Sleep(delayMs);
            if (delayMs < 400) delayMs *= 3;
        }
    }

    public void Release()
    {
        if (_stream is null) return;
        var myPid = _ownerPid;
        try { _stream.Dispose(); } catch { /* 锁文件已删等 */ }
        _stream = null;
        // 删除竞态防护: 先释放 fd (flock 释放) 再删 — 但删除前校验锁文件仍是自己的
        // (A 释放瞬间 B 可能已建新锁 → 内容=B pid → 不删, 避免误删他人新锁破坏互斥)。
        try
        {
            if (!string.IsNullOrEmpty(myPid) && File.Exists(LockPath))
            {
                var content = File.ReadAllText(LockPath).Trim();
                if (content == myPid) File.Delete(LockPath);
            }
        }
        catch { /* 已删或瞬态 */ }
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        Release();
    }
}

/// <summary>原子写: tmp 同目录写 + Flush(true) + Move(overwrite) — 读者永不见半写文件 (同卷 rename 原子)。</summary>
public static class AtomicFileWriter
{
    public static void WriteAllText(string path, string content)
    {
        var dir = Path.GetDirectoryName(Path.GetFullPath(path))!;
        Directory.CreateDirectory(dir);
        var tmp = Path.Combine(dir,
            $".{Path.GetFileName(path)}.tmp-{Environment.ProcessId}-{Guid.NewGuid():N}");
        try
        {
            using (var fs = new FileStream(tmp, FileMode.CreateNew, FileAccess.Write, FileShare.None, 4096,
                       FileOptions.WriteThrough))
            {
                var buf = Encoding.UTF8.GetBytes(content);
                fs.Write(buf, 0, buf.Length);
                fs.Flush(true);
            }
            File.Move(tmp, path, overwrite: true);
        }
        finally
        {
            try { if (File.Exists(tmp)) File.Delete(tmp); } catch { /* 已 move 或清理竞争 */ }
        }
    }
}

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
        try
        {
            if (File.Exists(lockPath))
            {
                var pid = File.ReadAllText(lockPath).Trim();
                if (int.TryParse(pid, out var p) && p > 0)
                    return $"PID {p} ({ReadComm(p)}) 持有锁 {Path.GetFileName(lockPath)}";
            }
        }
        catch { /* FileShare.None 拒读 → 走 /proc/locks */ }
        // flock 加在锁文件 (LockPath) 的 inode 上 — 必须扫锁文件而非目标文件
        var byLocks = ScanProcLocks(lockPath);
        return string.IsNullOrEmpty(byLocks) ? "未知占用者 (平台无 /proc/locks 或锁未记录)" : byLocks;
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

    /// <summary>stale 锁清除: 锁文件内容 pid 无对应进程 (Linux /proc/&lt;pid&gt;) → 删锁文件。返回是否清除。</summary>
    public static bool TryBreakStaleLock(string lockPath)
    {
        try
        {
            if (!File.Exists(lockPath)) return false;
            var content = File.ReadAllText(lockPath).Trim();
            if (!int.TryParse(content, out var pid) || pid <= 0) return false; // 无 pid 信息, 不擅动
            if (!Directory.Exists($"/proc/{pid}")) // 持有者已死
            {
                File.Delete(lockPath);
                return true;
            }
            return false;
        }
        catch { return false; }
    }
}
