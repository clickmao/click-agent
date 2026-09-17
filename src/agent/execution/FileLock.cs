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
                // R465: 不再「清 stale 锁文件」(unlink 会破坏 flock 互斥 — 见 Release 注释)。
                // 死持有者的锁由内核在 fd 关闭时释放, 这里只需退避重试。
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
        try { _stream.Dispose(); } catch { /* 已关闭等 */ }
        _stream = null;
        // ───────────────────────────────────────────────────────────────────────
        // R465 (真修): **绝不 unlink 锁文件** —— 这是 flock 纪律的硬要求。
        // 旧实现「释放 fd 后按 pid 校验删锁文件」有一个致命窗口: A 关 fd 的瞬间 B 的
        // Open 已成功(B 拿到同一 inode 的 flock), 但 A 此刻读到的内容仍是自己的 pid
        // ⇒ A 删文件 ⇒ B 持有的是**已 unlink 的 inode** 上的锁, 而 C 打开同名路径得到
        // 新 inode 并拿到锁 ⇒ 两个持有者同时进入临界区 (实测 119/120 段 = 一次读改写被覆盖)。
        // 锁文件因此是**长期存在的信号对象**: 锁身份 = inode, 存在性 ≠ 是否被持有;
        // 死持有者的锁由内核在 fd 关闭时自动释放 (下一次 Open 直接成功), 无需任何人删文件。
        // ───────────────────────────────────────────────────────────────────────
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        Release();
    }
}
