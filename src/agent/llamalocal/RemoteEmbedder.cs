using System;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using agent.llmservice;

namespace agent.llamalocal;

/// <summary>
/// v0.20.0 P1/P2 (R342, 用户钦定 LLM 服务独立进程 + 纠正: 仅新增本机 LLM host, 不改框架现有使用流程):
/// RemoteEmbedder = 新能力的客户端 (调用方显式选用; 现有 BgeEmbedder DI 路径原样不动)。
/// P2 (用户三问: 双 CLI 并发 / 中途崩溃 / 内存显存崩):
///  - 双 CLI 并发: pid 文件 CreateNew 原子抢占 — 抢到者负责 spawn, 抢不到者等 READY 复用同一 daemon;
///    daemon 侧双启保护 (LlmServiceHost 构造: pid 活 → 抛) 兜底。
///  - 中途崩溃: EmbedAsync 前探活失败 → EnsureServiceAsync (pid 判定死 → 抢占重启) → 自动恢复。
///  - 反复崩溃 (内存/显存不足): RestartWindow 内 ≥RestartBudget 次 → 熔断不再自启, 抛明确错误 (防重启风暴)。
/// spawn: env AGENTFRAMEWORK_LLM_SERVICE_BIN 优先, 缺省当前进程即 agenthost 时自举; daemon 日志经 sh 重定向落 .log 文件
/// (无管道持有 — 客户端退出不杀 daemon)。
/// </summary>
public sealed class RemoteEmbedder : agent.contextgradient.ITextEmbedder, IDisposable
{
    private readonly string _sockPath;
    private readonly string _pidPath;
    private readonly string _startLockPath;
    private readonly string _restartsPath;
    private readonly Func<string?>? _spawnFactory; // 可注入 (测试); null = 默认 spawn。返回 null=成功, 非 null=错误串
    private Socket? _socket;

    public static string DefaultSockPath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "af-llm.sock");
    public const int RestartBudget = 3;
    public static readonly TimeSpan RestartWindow = TimeSpan.FromMinutes(5);
    public static readonly TimeSpan StartLockStale = TimeSpan.FromSeconds(60);

    public RemoteEmbedder(string? sockPath = null, Func<string?>? spawnFactory = null)
    {
        _sockPath = sockPath ?? GetSockFromEnv();
        _pidPath = _sockPath + ".manager.pid";  // manager 写 (自身 pid); 客户端只读
        _startLockPath = _sockPath + ".startlock"; // 客户端抢占用 (CreateNew 原子); 与 daemon pid 文件隔离
        _restartsPath = _sockPath + ".restarts";
        _spawnFactory = spawnFactory;
    }

    public static string GetSockFromEnv()
    {
        var v = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLM_SERVICE_SOCK");
        return string.IsNullOrEmpty(v) ? DefaultSockPath : v;
    }

    public static bool Probe(string? sockPath = null, int timeoutMs = 400)
    {
        try
        {
            using var s = NewConnected(sockPath ?? GetSockFromEnv());
            return s.Connected;
        }
        catch { return false; }
    }

    private static Socket NewConnected(string sockPath)
    {
        var s = new Socket(AddressFamily.Unix, SocketType.Stream, ProtocolType.Unspecified);
        s.Connect(new UnixDomainSocketEndPoint(sockPath));
        s.ReceiveTimeout = 30_000;
        return s;
    }

    public bool IsAvailable => Probe(_sockPath);

    public async Task<float[]> EmbedAsync(string text, CancellationToken ct = default)
    {
        if (!Probe(_sockPath, 120))
            await EnsureServiceAsync(ct).ConfigureAwait(false);   // 崩溃自动恢复入口
        var resp = await RoundTripAsync(text, ct).ConfigureAwait(false);
        using var doc = System.Text.Json.JsonDocument.Parse(resp);
        var root = doc.RootElement;
        if (!root.TryGetProperty("ok", out var ok) || !ok.GetBoolean())
        {
            var err = root.TryGetProperty("error", out var e) ? e.GetString() : "unknown";
            throw new IOException($"llm-service embed 失败: {err}");
        }
        var arr = root.GetProperty("vec");
        var vec = new float[arr.GetArrayLength()];
        var i = 0;
        foreach (var el in arr.EnumerateArray()) vec[i++] = el.GetSingle();
        return vec;
    }

    /// <summary>P2: 确保 daemon 在线。幂等, 多客户端并发安全。</summary>
    public async Task EnsureServiceAsync(CancellationToken ct = default)
    {
        if (Probe(_sockPath, 120)) return;                                  // ① 已在线
        if (await TryAwaitReadyAsync(TimeSpan.FromSeconds(3), ct).ConfigureAwait(false)) return; // ② 别人启动中

        // ③ pid 判定: 残留 pid 若活 (如另一个 CLI 正在启) → 等 READY; 死 → 继续抢占
        if (LlmServiceHost.TryReadPid(_pidPath, out var existing) && LlmServiceHost.IsProcessAlive(existing))
        {
            if (await TryAwaitReadyAsync(TimeSpan.FromSeconds(45), ct).ConfigureAwait(false)) return;
            throw new IOException($"llm-service pid={existing} 存活但 45s 未就绪 — 状态异常, 请检查日志");
        }

        var pidClaimed = false;
        try
        {
            // ④ 原子抢占 startlock: CreateNew 成功者负责 spawn; 失败 = 并发对手启动中 → 等 READY
            try
            {
                using (var fs = new FileStream(_startLockPath, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                using (var w = new StreamWriter(fs))
                    w.Write(Environment.ProcessId);
                pidClaimed = true;
            }
            catch (IOException)
            {
                // 锁存在: stale (持有者崩了) → 清理重抢; 否则等对手 READY
                if (IsStartLockStale())
                {
                    TryDeleteFile(_startLockPath);
                    try
                    {
                        using var fs = new FileStream(_startLockPath, FileMode.CreateNew, FileAccess.Write, FileShare.None);
                        using var w = new StreamWriter(fs);
                        w.Write(Environment.ProcessId);
                        pidClaimed = true;
                    }
                    catch (IOException) { }
                }
            }
            catch (UnauthorizedAccessException) { }

            if (pidClaimed)
            {
                // ⑤ 熔断: 窗口内超预算 → 拒启 (内存/显存反复崩场景)
                if (!TryCheckRestartBudget(out var budgetDetail))
                {
                    TryDeleteFile(_startLockPath);
                    throw new IOException($"llm-service 反复崩溃 ({RestartBudget} 次/{RestartWindow.TotalMinutes:0}min) — 自动重启已熔断, 请检查模型路径/内存/显存后手动启动。{budgetDetail}");
                }
                var spawnErr = _spawnFactory is null ? SpawnDaemon() : _spawnFactory();
                if (spawnErr is not null)
                {
                    TryDeleteFile(_startLockPath);
                    throw new IOException($"llm-service 自动拉起失败: {spawnErr}");
                }
                RecordRestart(); // spawn 成功才计数
            }
            // ⑥ 等 READY (模型加载预算 45s)
            if (await TryAwaitReadyAsync(TimeSpan.FromSeconds(45), ct).ConfigureAwait(false))
            {
                if (pidClaimed) TryDeleteFile(_startLockPath); // 启动完成 → 释放锁
                return;
            }
            if (pidClaimed) TryDeleteFile(_startLockPath);
            throw new IOException("llm-service 启动超时 (45s) — 未就绪, 请查看日志");
        }
        catch (OperationCanceledException) { throw; }
        catch (IOException) { throw; }
        catch (Exception ex) { throw new IOException($"llm-service 启动失败: {ex.Message}"); }
    }

    private bool IsStartLockStale()
    {
        try
        {
            if (!File.Exists(_startLockPath)) return true;
            return DateTime.UtcNow - File.GetLastWriteTimeUtc(_startLockPath) > StartLockStale;
        }
        catch { return true; }
    }

    /// <summary>默认 spawn (跨平台, 用户 OOB 修正): 直接 Process.Start 无 shell 依赖;
    /// daemon 自身把日志重定向到文件 (env AGENTFRAMEWORK_LLM_SERVICE_LOG) — 无管道持有、父退出不杀子进程。</summary>
    private string? SpawnDaemon()
    {
        var bin = ResolveSpawnCommand();
        if (bin is null) return "未找到 agenthost 可执行 (AGENTFRAMEWORK_LLM_SERVICE_BIN 未设且当前进程非 agenthost)";
        try
        {
            var logPath = _sockPath + ".log";
            var psi = new ProcessStartInfo
            {
                FileName = bin,
                UseShellExecute = false,
                CreateNoWindow = true,
            };
            psi.ArgumentList.Add("--llm-manager");
            psi.Environment["AGENTFRAMEWORK_LLM_SERVICE_SOCK"] = _sockPath;
            psi.Environment["AGENTFRAMEWORK_LLM_SERVICE_LOG"] = logPath;
            var bge = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_BGE_MODEL");
            if (!string.IsNullOrEmpty(bge)) psi.Environment["AGENTFRAMEWORK_BGE_MODEL"] = bge;
            var p = Process.Start(psi);
            if (p is null) return "Process.Start 返回 null";
            p.Dispose(); // 不持有 — daemon 独立存活 (CLI 退出不杀)
            AppendLog(logPath, $"[spawner] pid={Environment.ProcessId} 拉起 llm-manager at {DateTime.Now:O} (log 由 daemon 自写)");
            return null;
        }
        catch (Exception ex) { return ex.Message; }
    }

    private string? ResolveSpawnCommand()
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

    private async Task<bool> TryAwaitReadyAsync(TimeSpan budget, CancellationToken ct)
    {
        var deadline = DateTime.UtcNow + budget;
        while (DateTime.UtcNow < deadline)
        {
            if (Probe(_sockPath, 120)) return true;
            await Task.Delay(150, ct).ConfigureAwait(false);
        }
        return false;
    }

    private bool TryCheckRestartBudget(out string detail)
    {
        detail = string.Empty;
        try
        {
            if (!File.Exists(_restartsPath)) return true;
            var raw = File.ReadAllText(_restartsPath);
            using var doc = System.Text.Json.JsonDocument.Parse(raw);
            var ts = doc.RootElement.GetProperty("ts").GetInt64();
            var count = doc.RootElement.GetProperty("count").GetInt32();
            var age = DateTime.UtcNow - DateTimeOffset.FromUnixTimeSeconds(ts).UtcDateTime;
            if (age > RestartWindow) return true;
            if (count >= RestartBudget)
            {
                detail = $"最近 {RestartWindow.TotalMinutes:0}min 内已重启 {count} 次";
                return false;
            }
            return true;
        }
        catch { return true; }
    }

    private void RecordRestart()
    {
        try
        {
            var ts = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            var count = 1;
            if (File.Exists(_restartsPath))
            {
                try
                {
                    var raw = File.ReadAllText(_restartsPath);
                    using var doc = System.Text.Json.JsonDocument.Parse(raw);
                    var age = DateTime.UtcNow - DateTimeOffset.FromUnixTimeSeconds(doc.RootElement.GetProperty("ts").GetInt64()).UtcDateTime;
                    if (age <= RestartWindow) count = doc.RootElement.GetProperty("count").GetInt32() + 1;
                }
                catch { }
            }
            File.WriteAllText(_restartsPath, "{\"ts\":" + ts + ",\"count\":" + count + "}");
        }
        catch { }
    }

    private void TryDeleteFile(string path)
    {
        try { if (File.Exists(path)) File.Delete(path); } catch { }
    }

    private static void AppendLog(string path, string line)
    {
        try { File.AppendAllText(path, line + Environment.NewLine); } catch { }
    }

    private async Task<string> RoundTripAsync(string text, CancellationToken ct)
    {
        var payload = "{\"op\":\"embed\",\"text\":" + JsonEsc(text) + "}\n";
        for (var attempt = 0; attempt < 3; attempt++)
        {
            try
            {
                EnsureConnected();
                var buf = Encoding.UTF8.GetBytes(payload);
                _socket!.Send(buf, SocketFlags.None);
                return await ReadLineAsync(ct).ConfigureAwait(false) ?? throw new IOException("连接被关闭");
            }
            catch (Exception) when (attempt < 2)
            {
                Teardown();
                await Task.Delay(80 * (attempt + 1), ct).ConfigureAwait(false);
            }
        }
        Teardown();
        throw new IOException($"llm-service ({_sockPath}) 不可达: 3 次重试失败 (daemon 未启动?)");
    }

    private void EnsureConnected()
    {
        if (_socket is { Connected: true }) return;
        _socket = NewConnected(_sockPath);
    }

    private async Task<string?> ReadLineAsync(CancellationToken ct)
    {
        var sb = new StringBuilder();
        var one = new byte[1];
        while (true)
        {
            var n = await _socket!.ReceiveAsync(new ArraySegment<byte>(one), SocketFlags.None, ct).ConfigureAwait(false);
            if (n == 0) return null;
            var ch = (char)one[0];
            if (ch == '\n') break;
            sb.Append(ch);
        }
        return sb.ToString();
    }

    private void Teardown()
    {
        try { _socket?.Close(); } catch { }
        _socket = null;
    }

    private static string JsonEsc(string s)
        => "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n").Replace("\r", "\\r").Replace("\t", "\\t") + "\"";

    public void Dispose() => Teardown();
}
