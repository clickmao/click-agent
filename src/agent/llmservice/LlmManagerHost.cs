using System;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace agent.llmservice;

/// <summary>
/// v0.20.0 P3 (R343, 用户钦定策略): llm-manager — 轻量常驻编排进程 (0 模型加载), 对外 UDS 与 CLI 通讯,
/// 背后按需 spawn llm-service-host (真 LLM/bge, 可被杀)。
///  - lazy load: 首个使用请求 → spawn worker → 等 READY → 转发 (首次请求延迟 = 模型加载, 仅此一次)
///  - supervise: worker 崩溃/被杀 → 下次请求自动重拉 (客户端无感)
///  - unload: 资源紧张 ∧ 无 CLI 实例 ∧ 无活跃请求/连接 → **直接 kill worker** (OS 回收全部 native 内存 —
///    避开 LLamaSharp weights/context 手工释放与引用计数, 用户钦定巧妙策略)
///  - manager 自身常驻且极轻 (不随 CLI 生死; CLI 全退仍在) → 解决"0 实例 → 新 CLI 必须重载模型"
/// 对外协议与 worker 完全一致 (透明代理) → 客户端零改动。
/// 双启保护: manager pid 文件 (同 LlmServiceHost 模式)。
/// </summary>
public sealed class LlmManagerHost : IDisposable
{
    private readonly string _sockPath;
    private readonly string _workerSockPath;
    private readonly string _pidPath;
    private readonly Action<string> _log;
    private readonly Func<string?> _workerBinResolver;
    private readonly Func<Process?>? _workerSpawner; // 可注入 (测试); null = 默认 sh -c spawn
    private readonly Func<long> _memAvailableMb;
    private readonly Func<int> _activeCliCount;
    private readonly long _memFloorMb;
    private readonly int _unloadCheckMs;

    private Socket? _listener;
    private readonly CancellationTokenSource _cts = new();
    private readonly SemaphoreSlim _workerGate = new(1, 1);
    private Process? _worker;
    private int _activeConnections;
    private int _inflightRequests;
    private long _requests;
    private long _workerSpawns;
    private long _workerUnloads;
    private bool _disposed;

    public static string WorkerSockSuffix = ".worker";
    public const int WorkerReadyBudgetSec = 45;

    public LlmManagerHost(
        Action<string> log,
        string? sockPath = null,
        Func<string?>? workerBinResolver = null,
        Func<long>? memAvailableMb = null,
        Func<int>? activeCliCount = null,
        long memFloorMb = 512,
        int unloadCheckMs = 15_000,
        Func<Process?>? workerSpawner = null)
    {
        _sockPath = sockPath ?? agent.llamalocal.RemoteEmbedder.GetSockFromEnv();
        _workerSockPath = _sockPath + WorkerSockSuffix;
        _pidPath = _sockPath + ".manager.pid";
        _log = log;
        _workerBinResolver = workerBinResolver ?? ResolveWorkerBin;
        _workerSpawner = workerSpawner;
        _memAvailableMb = memAvailableMb ?? ReadMemAvailableMb;
        _activeCliCount = activeCliCount ?? ReadActiveCliCount;
        _memFloorMb = memFloorMb;
        _unloadCheckMs = unloadCheckMs;
    }

    public long RequestCount => Interlocked.Read(ref _requests);
    public long WorkerSpawnCount => Interlocked.Read(ref _workerSpawns);
    public long WorkerUnloadCount => Interlocked.Read(ref _workerUnloads);
    public bool WorkerRunning => _worker is { HasExited: false };
    public string WorkerSockPath => _workerSockPath;

    /// <summary>启动 manager: pid 双启保护 + 对外监听 + 卸载巡检。</summary>
    public void Start()
    {
        if (LlmServiceHost.TryReadPid(_pidPath, out var existing) && LlmServiceHost.IsProcessAlive(existing))
            throw new InvalidOperationException($"llm-manager 已在运行 (pid={existing}); 复用现有实例");
        LlmServiceHost.TryWritePid(_pidPath, Environment.ProcessId, out _);
        CleanupOrphanWorker();
        _ = Task.Run(AcceptLoopAsync);
        _ = Task.Run(UnloadLoopAsync);
    }

    private async Task AcceptLoopAsync()
    {
        try
        {
            if (File.Exists(_sockPath)) File.Delete(_sockPath);
            _listener = new Socket(AddressFamily.Unix, SocketType.Stream, ProtocolType.Unspecified);
            _listener.Bind(new UnixDomainSocketEndPoint(_sockPath));
            _listener.Listen(32);
            _log($"llm-manager 监听 {_sockPath} (pid={Environment.ProcessId}; worker 按需拉起)");
            while (!_cts.IsCancellationRequested)
            {
                var client = await _listener.AcceptAsync(_cts.Token).ConfigureAwait(false);
                _ = Task.Run(() => ServeClientAsync(client));
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception ex) { _log($"llm-manager accept 异常: {ex.Message}"); }
    }

    private async Task ServeClientAsync(Socket client)
    {
        Interlocked.Increment(ref _activeConnections);
        try
        {
            var buf = new byte[16384];
            var pending = new StringBuilder();
            while (!_cts.IsCancellationRequested)
            {
                var n = await client.ReceiveAsync(new ArraySegment<byte>(buf), SocketFlags.None, _cts.Token).ConfigureAwait(false);
                if (n == 0) break;
                pending.Append(Encoding.UTF8.GetString(buf, 0, n));
                while (true)
                {
                    var lineEnd = pending.ToString().IndexOf('\n');
                    if (lineEnd < 0) break;
                    var line = pending.ToString()[..lineEnd];
                    pending.Remove(0, lineEnd + 1);
                    var resp = await HandleLineAsync(line).ConfigureAwait(false);
                    var outBytes = Encoding.UTF8.GetBytes(resp + "\n");
                    await client.SendAsync(new ArraySegment<byte>(outBytes), SocketFlags.None, _cts.Token).ConfigureAwait(false);
                }
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception ex) { _log($"llm-manager 会话异常: {ex.Message}"); }
        finally
        {
            Interlocked.Decrement(ref _activeConnections);
            try { client.Close(); } catch { }
        }
    }

    private async Task<string> HandleLineAsync(string line)
    {
        Interlocked.Increment(ref _requests);
        Interlocked.Increment(ref _inflightRequests);
        try
        {
            // ping 由 manager 直接应答 (探活不触发 worker 加载 — lazy 语义)
            var op = ExtractOp(line);
            if (op == "ping") return "{\"ok\":true,\"pong\":true,\"manager\":true}";
            if (op == "status") return StatusJson();
            var forward = await ForwardToWorkerAsync(line).ConfigureAwait(false);
            return forward;
        }
        catch (Exception ex)
        {
            return "{\"ok\":false,\"error\":\"" + ex.Message.Replace("\\", "/").Replace("\"", "'") + "\"}";
        }
        finally { Interlocked.Decrement(ref _inflightRequests); }
    }

    private static string ExtractOp(string line)
    {
        try
        {
            using var doc = System.Text.Json.JsonDocument.Parse(line);
            return doc.RootElement.TryGetProperty("op", out var o) ? o.GetString() ?? "" : "";
        }
        catch { return ""; }
    }

    /// <summary>确保 worker 在线 (lazy spawn) 并转发请求 (行级透明代理)。</summary>
    private async Task<string> ForwardToWorkerAsync(string requestLine)
    {
        await EnsureWorkerAsync().ConfigureAwait(false);
        using var ws = new Socket(AddressFamily.Unix, SocketType.Stream, ProtocolType.Unspecified);
        ws.Connect(new UnixDomainSocketEndPoint(_workerSockPath));
        ws.ReceiveTimeout = 120_000; // 模型冷加载 + 推理预算
        var buf = Encoding.UTF8.GetBytes(requestLine + "\n");
        ws.Send(buf, SocketFlags.None);
        var sb = new StringBuilder();
        var one = new byte[1];
        while (true)
        {
            var n = ws.Receive(one, 0, 1, SocketFlags.None);
            if (n == 0) break;
            var ch = (char)one[0];
            if (ch == '\n') break;
            sb.Append(ch);
        }
        return sb.Length > 0 ? sb.ToString() : "{\"ok\":false,\"error\":\"worker 无响应\"}";
    }

    /// <summary>lazy: worker 不在 → spawn (并发请求由 gate 串行, 只 spawn 一次) → 等 READY。</summary>
    public async Task EnsureWorkerAsync()
    {
        if (ProbeWorker()) return;
        await _workerGate.WaitAsync(_cts.Token).ConfigureAwait(false);
        try
        {
            if (ProbeWorker()) return;
            // stale worker sock 清理
            try { if (File.Exists(_workerSockPath)) File.Delete(_workerSockPath); } catch { }
            Process? p;
            if (_workerSpawner is not null)
            {
                p = _workerSpawner(); // 测试注入
            }
            else
            {
                // 跨平台 (用户 OOB 修正): 直接 spawn 无 shell 依赖; worker 自写日志 (env LOG), 无管道持有
                var bin = _workerBinResolver();
                if (bin is null) throw new IOException("未找到 worker 可执行 (AGENTFRAMEWORK_LLM_SERVICE_BIN / 当前进程非 agenthost)");
                var psi = new ProcessStartInfo
                {
                    FileName = bin,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                };
                psi.ArgumentList.Add("--llm-service");
                psi.Environment["AGENTFRAMEWORK_LLM_SERVICE_SOCK"] = _workerSockPath;
                psi.Environment["AGENTFRAMEWORK_LLM_SERVICE_LOG"] = _sockPath + ".worker.log";
                var bge = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_BGE_MODEL");
                if (!string.IsNullOrEmpty(bge)) psi.Environment["AGENTFRAMEWORK_BGE_MODEL"] = bge;
                p = Process.Start(psi);
            }
            if (p is null) throw new IOException("worker spawn 返回 null");
            _worker = p;
            Interlocked.Increment(ref _workerSpawns);
            _log($"llm-manager: 拉起 worker (pid={SafePid(p)}) — 加载模型 (lazy)");
            var deadline = DateTime.UtcNow.AddSeconds(WorkerReadyBudgetSec);
            while (DateTime.UtcNow < deadline)
            {
                if (ProbeWorker()) { _log($"llm-manager: worker READY (pid={SafePid(p)})"); return; }
                try { if (p.HasExited) throw new IOException($"worker 启动失败退出 (exit={p.ExitCode}); 见 {_sockPath}.worker.log"); }
                catch (InvalidOperationException) { }
                await Task.Delay(200, _cts.Token).ConfigureAwait(false);
            }
            throw new IOException($"worker {WorkerReadyBudgetSec}s 未就绪; 见 {_sockPath}.worker.log");
        }
        finally { _workerGate.Release(); }
    }

    /// <summary>v0.20.2 (R345): 状态查询 (供 /llm-service 指令观测) — 跨平台 (Process.WorkingSet64)。</summary>
    public string StatusJson()
    {
        var workerUp = WorkerRunning || ProbeWorker();
        var wpid = -1;
        if (_worker is { HasExited: false }) wpid = SafePid(_worker);
        else if (LlmServiceHost.TryReadPid(_workerSockPath + ".pid", out var p)) wpid = p;
        var wrss = wpid > 0 ? ReadRssMb(wpid) : 0;
        return "{\"ok\":true"
            + ",\"manager_pid\":" + Environment.ProcessId
            + ",\"worker_running\":" + (workerUp ? "true" : "false")
            + ",\"worker_pid\":" + wpid
            + ",\"worker_rss_mb\":" + wrss
            + ",\"requests\":" + RequestCount
            + ",\"spawns\":" + WorkerSpawnCount
            + ",\"unloads\":" + WorkerUnloadCount
            + ",\"mem_available_mb\":" + _memAvailableMb()
            + ",\"mem_floor_mb\":" + _memFloorMb
            + ",\"active_cli\":" + _activeCliCount() + "}";
    }

    /// <summary>进程 RSS (MB); 跨平台 (WorkingSet64)。失败 → 0。</summary>
    public static long ReadRssMb(int pid)
    {
        try
        {
            using var pr = Process.GetProcessById(pid);
            return pr.WorkingSet64 / (1024 * 1024);
        }
        catch { return 0; }
    }

    private bool ProbeWorker()
    {
        try
        {
            using var s = new Socket(AddressFamily.Unix, SocketType.Stream, ProtocolType.Unspecified);
            s.Connect(new UnixDomainSocketEndPoint(_workerSockPath));
            return s.Connected;
        }
        catch { return false; }
    }

    /// <summary>卸载巡检: 资源紧张 ∧ 无 CLI 实例 ∧ 无请求/连接 → kill worker (OS 回收内存)。</summary>
    private async Task UnloadLoopAsync()
    {
        while (!_cts.IsCancellationRequested)
        {
            try { await Task.Delay(_unloadCheckMs, _cts.Token).ConfigureAwait(false); }
            catch (OperationCanceledException) { return; }
            try { MaybeUnload(); }
            catch (Exception ex) { _log($"llm-manager 卸载巡检异常: {ex.Message}"); }
        }
    }

    /// <summary>可测的卸载判定 (纯逻辑): 资源紧张 ∧ 无 CLI 实例 ∧ 无进行中请求 ∧ worker 在。
    /// 注意: **空闲长连接不阻止卸载** — CLI 保持 socket 但无请求时不代表在用 (客户端有重连/重拉逻辑, worker 被杀无感)。</summary>
    public static bool ShouldUnload(long availMb, long floorMb, int cliCount, int inflight, bool workerUp)
        => workerUp && inflight == 0 && availMb > 0 && availMb < floorMb && cliCount == 0;

    /// <summary>卸载巡检动作: 判定 → kill worker。</summary>
    public bool MaybeUnload()
    {
        var workerUp = WorkerRunning || ProbeWorker();
        var avail = _memAvailableMb();
        var cli = _activeCliCount();
        var inflight = Interlocked.CompareExchange(ref _inflightRequests, 0, 0);
        if (!ShouldUnload(avail, _memFloorMb, cli, inflight, workerUp)) return false;
        KillWorker($"资源紧张 (MemAvailable={avail}MB < {_memFloorMb}MB) 且 无 CLI 实例");
        return true;
    }

    /// <summary>清理孤儿 worker: manager 崩溃/被杀 (SIGKILL 无 Dispose) 后残留的 worker 进程 → 杀掉 + 删 sock/pid。
    /// 否则新 manager 会误复用孤儿 worker (占内存且不归它管)。</summary>
    public void CleanupOrphanWorker()
    {
        if (_worker is not null) return;
        var pidFile = _workerSockPath + ".pid";
        var orphanPid = -1;
        if (LlmServiceHost.TryReadPid(pidFile, out var pid)) orphanPid = pid;
        var hasSock = File.Exists(_workerSockPath);
        if (orphanPid > 0 && LlmServiceHost.IsProcessAlive(orphanPid))
        {
            try
            {
                using var pr = Process.GetProcessById(orphanPid);
                pr.Kill(entireProcessTree: true);
                _log($"llm-manager: 清理孤儿 worker (pid={orphanPid}, 上个 manager 崩溃残留)");
            }
            catch (Exception ex) { _log($"llm-manager: 孤儿 worker 清理失败: {ex.Message}"); }
        }
        try { if (File.Exists(pidFile)) File.Delete(pidFile); } catch { }
        try { if (hasSock) File.Delete(_workerSockPath); } catch { }
    }

    /// <summary>kill worker 进程 (含子进程树) — 卸载模型 (OS 回收 native 内存)。
    /// 无 _worker 引用 (孤儿/复用场景) 时按 workerSock.pid 文件杀。</summary>
    public void KillWorker(string reason)
    {
        var p = _worker;
        if (p is not null)
        {
            try { if (!p.HasExited) p.Kill(entireProcessTree: true); } catch { }
            try { p.Dispose(); } catch { }
            _worker = null;
        }
        else
        {
            if (LlmServiceHost.TryReadPid(_workerSockPath + ".pid", out var pid) && LlmServiceHost.IsProcessAlive(pid))
                try
                {
                    using var pr = Process.GetProcessById(pid);
                    pr.Kill(entireProcessTree: true);
                }
                catch { }
        }
        try { if (File.Exists(_workerSockPath)) File.Delete(_workerSockPath); } catch { }
        try { if (File.Exists(_workerSockPath + ".pid")) File.Delete(_workerSockPath + ".pid"); } catch { }
        Interlocked.Increment(ref _workerUnloads);
        _log($"llm-manager: 卸载 worker — {reason} (下次请求将 lazy 重载)");
    }

    // ---- 默认探测器 (可注入替换以便测试) ----

    /// <summary>系统可用内存 MB (Linux: /proc/meminfo MemAvailable; Windows: GlobalMemoryStatusEx; 其他 → -1)。</summary>
    public static long ReadMemAvailableMb()
    {
        if (OperatingSystem.IsWindows()) return WindowsMemory.GetAvailableMb();
        try
        {
            foreach (var line in File.ReadAllLines("/proc/meminfo"))
                if (line.StartsWith("MemAvailable:", StringComparison.Ordinal))
                {
                    var parts = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                    if (parts.Length >= 2 && long.TryParse(parts[1], out var kb)) return kb / 1024;
                }
        }
        catch { }
        return -1;
    }

    /// <summary>活跃 CLI 实例数 (ActivityService 跨进程心跳注册表; 过期 90s 自动排除)。</summary>
    public static int ReadActiveCliCount()
    {
        try { return new agent.activity.ActivityService().QueryActive().Count; }
        catch { return 0; }
    }

    private string? ResolveWorkerBin()
    {
        var bin = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLM_SERVICE_BIN");
        if (!string.IsNullOrEmpty(bin) && File.Exists(bin)) return bin;
        try
        {
            var self = Environment.ProcessPath;
            if (!string.IsNullOrEmpty(self) && File.Exists(self)
                && Path.GetFileNameWithoutExtension(self).Contains("agenthost", StringComparison.OrdinalIgnoreCase))
                return self;
        }
        catch { }
        return null;
    }

    private static int SafePid(Process p)
    {
        try { return p.Id; } catch { return -1; }
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        _cts.Cancel();
        try { _listener?.Close(); } catch { }
        KillWorker("manager 退出");
        try { if (File.Exists(_sockPath)) File.Delete(_sockPath); } catch { }
        try
        {
            if (File.Exists(_pidPath) && LlmServiceHost.TryReadPid(_pidPath, out var mine) && mine == Environment.ProcessId)
                File.Delete(_pidPath);
        }
        catch { }
    }
}
