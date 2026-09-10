using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace agent.llmservice;

/// <summary>
/// v0.20.0 P1/P2 (R342): 本机 LLM service daemon — 独立进程常驻加载 bge, Unix Domain Socket 服务多 CLI,
/// **新 CLI 不再重复加载模型**。P2 (用户三问): 双启保护 + 崩溃重启 (客户端拉起) + 熔断。
/// 文件布局 (sock 同路径旁): .sock 监听 / .pid daemon 自身 pid (Start 写/Dispose 删) / .restarts 重启计数 (客户端写)。
/// 双启保护: Start 时 pid 文件存在且 pid 存活 → 已有一实例 → 抛异常 (exit 4)。
/// AOT: 纯 BCL; 经 _log 回调输出。
/// </summary>
public sealed class LlmServiceHost : IDisposable
{
    private readonly Func<string, CancellationToken, Task<float[]>> _embed;
    private readonly Action<string> _log;
    private readonly string _sockPath;
    private readonly CancellationTokenSource _cts = new();
    private Socket? _listener;
    private readonly SemaphoreSlim _embedGate = new(1, 1);
    private readonly ConcurrentBag<Socket> _clients = new();
    private readonly Task _acceptLoop;
    private long _requests;
    private bool _disposed;

    public LlmServiceHost(Func<string, CancellationToken, Task<float[]>> embed, Action<string> log,
        string? sockPath = null)
    {
        _embed = embed;
        _log = log;
        _sockPath = sockPath ?? agent.llamalocal.RemoteEmbedder.GetSockFromEnv();
        var pidPath = _sockPath + ".pid";
        // P2 双启保护: pid 文件存在且 pid 存活 → 已有实例 (启动中或健康) — 拒绝第二实例
        if (TryReadPid(pidPath, out var existing) && IsProcessAlive(existing))
        {
            throw new InvalidOperationException(
                $"llm-service 已在运行 (pid={existing}, sock={_sockPath}); 双实例会双载模型 — 请复用现有实例");
        }
        // stale pid (进程死但文件残留) → 覆盖
        TryWritePid(pidPath, Environment.ProcessId, out _);
        _acceptLoop = Task.Run(AcceptLoopAsync);
    }

    public long RequestCount => Interlocked.Read(ref _requests);
    public string SockPath => _sockPath;

    public static string? GetSockPathFromEnv()
        => Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLM_SERVICE_SOCK");

    /// <summary>pid 存活检测 (本机): 有效 pid + 进程存在。</summary>
    public static bool IsProcessAlive(int pid)
    {
        if (pid <= 0) return false;
        try
        {
            using var p = System.Diagnostics.Process.GetProcessById(pid);
            return !p.HasExited;
        }
        catch (ArgumentException) { return false; }   // 无此进程
        catch (InvalidOperationException) { return false; }
    }

    public static bool TryReadPid(string pidPath, out int pid)
    {
        pid = 0;
        try
        {
            if (!File.Exists(pidPath)) return false;
            var s = File.ReadAllText(pidPath).Trim();
            return int.TryParse(s, out pid);
        }
        catch { return false; }
    }

    public static bool TryWritePid(string pidPath, int pid, out string? error)
    {
        error = null;
        try
        {
            File.WriteAllText(pidPath, pid.ToString());
            return true;
        }
        catch (Exception ex) { error = ex.Message; return false; }
    }

    private async Task AcceptLoopAsync()
    {
        try
        {
            if (File.Exists(_sockPath)) File.Delete(_sockPath); // stale socket 清理
            _listener = new Socket(AddressFamily.Unix, SocketType.Stream, ProtocolType.Unspecified);
            _listener.Bind(new UnixDomainSocketEndPoint(_sockPath));
            _listener.Listen(16);
            _log($"llm-service 监听 {_sockPath} (pid={Environment.ProcessId})");
            while (!_cts.IsCancellationRequested)
            {
                var client = await _listener.AcceptAsync(_cts.Token).ConfigureAwait(false);
                _clients.Add(client);
                _ = Task.Run(() => ServeClientAsync(client));
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception ex) { _log($"llm-service accept 异常: {ex.Message}"); }
    }

    private async Task ServeClientAsync(Socket client)
    {
        try
        {
            var buf = new byte[8192];
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
        catch (Exception ex) { _log($"llm-service 客户端会话异常: {ex.Message}"); }
        finally
        {
            try { client.Close(); } catch { }
        }
    }

    private async Task<string> HandleLineAsync(string line)
    {
        Interlocked.Increment(ref _requests);
        try
        {
            using var doc = System.Text.Json.JsonDocument.Parse(line);
            var root = doc.RootElement;
            var op = root.TryGetProperty("op", out var o) ? o.GetString() : "";
            if (op == "embed")
            {
                var text = root.TryGetProperty("text", out var t) ? t.GetString() : "";
                if (text is null) return "{\"ok\":false,\"error\":\"missing text\"}";
                await _embedGate.WaitAsync(_cts.Token).ConfigureAwait(false);
                try
                {
                    var vec = await _embed(text, _cts.Token).ConfigureAwait(false);
                    var sb = new StringBuilder("{\"ok\":true,\"dim\":" + vec.Length + ",\"vec\":[");
                    for (var i = 0; i < vec.Length; i++)
                    {
                        if (i > 0) sb.Append(',');
                        sb.Append(vec[i].ToString("R", System.Globalization.CultureInfo.InvariantCulture));
                    }
                    sb.Append("]}");
                    return sb.ToString();
                }
                finally { _embedGate.Release(); }
            }
            if (op == "ping") return "{\"ok\":true,\"pong\":true}";
            return "{\"ok\":false,\"error\":\"unknown op: " + op + "\"}";
        }
        catch (Exception ex)
        {
            return "{\"ok\":false,\"error\":" + "\"" + ex.Message.Replace("\"", "'") + "\"}";
        }
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        _cts.Cancel();
        try { _listener?.Close(); } catch { }
        foreach (var c in _clients) { try { c.Close(); } catch { } }
        try
        {
            if (File.Exists(_sockPath)) File.Delete(_sockPath);
            var pidPath = _sockPath + ".pid";
            // 只删自己写的 pid (防误删: 崩溃后客户端抢占重启已写入新 pid 的场景)
            if (File.Exists(pidPath) && TryReadPid(pidPath, out var mine) && mine == Environment.ProcessId)
                File.Delete(pidPath);
        }
        catch { }
    }
}
