using System.Diagnostics;
using System.Globalization;
using System.Net;
using System.Net.Sockets;

namespace agent.llamacpp;

/// <summary>
/// llama-server 进程宿主: 二进制解析 → 端口分配 → 启动 → 就绪探测 → 关闭。
/// 零 P/Invoke、零 shell (全部走 ProcessStartInfo.ArgumentList)。
/// </summary>
public sealed class LlamaServerHost : IAsyncDisposable
{
    private const int TailLines = 400;

    private readonly LlamaServerOptions _o;
    private readonly List<string> _stdout = [];
    private readonly List<string> _stderr = [];
    private readonly Lock _logGate = new();
    private Process? _p;
    private string _baseUrl = string.Empty;

    public LlamaServerHost(LlamaServerOptions options) => _o = options;

    public string BaseUrl => _baseUrl;

    public bool IsRunning => _p is { HasExited: false };

    public IReadOnlyList<string> StdoutTail { get { lock (_logGate) return [.. _stdout]; } }

    public IReadOnlyList<string> StderrTail { get { lock (_logGate) return [.. _stderr]; } }

    /// <summary>非抛出式二进制探测 (供端口 IsAvailable 判定; 零副作用, 不启动进程)。</summary>
    public static bool TryResolveBinary(LlamaServerOptions o, out string? path, out string? reason)
    {
        try
        {
            path = ResolveBinary(o);
            reason = path is null ? $"未找到 llama-server (BinaryPath / {o.BinaryEnvVar} / PATH 均未命中)" : null;
            return path is not null;
        }
        catch (LlamaCppException ex)
        {
            path = null;
            reason = ex.Message;
            return false;
        }
    }

    /// <summary>
    /// 二进制解析契约 (按优先级, 每一级失败都给出可操作信息):
    /// ① LlamaServerOptions.BinaryPath 显式路径; ② BinaryEnvVar 环境变量; ③ PATH 查找。
    /// 找不到返回 null, 由 StartAsync 抛 provider_unavailable (不静默降级到任何桩实现)。
    /// </summary>
    public static string? ResolveBinary(LlamaServerOptions o)
    {
        if (!string.IsNullOrWhiteSpace(o.BinaryPath))
        {
            if (!File.Exists(o.BinaryPath))
                throw new LlamaCppException(LlamaCppException.ProviderUnavailable,
                    $"BinaryPath 指向的文件不存在: {o.BinaryPath}");
            return o.BinaryPath;
        }

        var env = Environment.GetEnvironmentVariable(o.BinaryEnvVar);
        if (!string.IsNullOrWhiteSpace(env))
        {
            if (!File.Exists(env))
                throw new LlamaCppException(LlamaCppException.ProviderUnavailable,
                    $"{o.BinaryEnvVar} 指向的文件不存在: {env}");
            return env;
        }

        var exe = OperatingSystem.IsWindows() ? "llama-server.exe" : "llama-server";
        var path = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
        foreach (var dir in path.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
        {
            try
            {
                var candidate = Path.Combine(dir.Trim(), exe);
                if (File.Exists(candidate)) return candidate;
            }
            catch (ArgumentException) { /* PATH 中含非法片段, 跳过 */ }
        }

        return null;
    }

    /// <summary>本机空闲端口探测 (Process 边界必需: 固定端口会在并发测试下互相踩)。</summary>
    private static int ReserveFreePort(string host)
    {
        var addr = host is "0.0.0.0" or "" ? IPAddress.Any : IPAddress.Loopback;
        var listener = new TcpListener(addr, 0);
        listener.Start();
        var port = ((IPEndPoint)listener.LocalEndpoint).Port;
        listener.Stop();
        return port;
    }

    public async Task StartAsync(CancellationToken ct = default)
    {
        if (!File.Exists(_o.ModelPath))
            throw new LlamaCppException(LlamaCppException.ProviderUnavailable, $"模型文件不存在: {_o.ModelPath}");

        var bin = ResolveBinary(_o) ?? throw new LlamaCppException(LlamaCppException.ProviderUnavailable,
            $"未找到 llama-server: 设置 {_o.BinaryEnvVar} 环境变量或 LlamaServerOptions.BinaryPath " +
            "(跨平台分发 = 每个 RID 一份官方二进制, 与本程序集解耦)");

        var port = _o.Port != 0 ? _o.Port : ReserveFreePort(_o.Host);
        var psi = new ProcessStartInfo(bin)
        {
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        psi.ArgumentList.Add("-m"); psi.ArgumentList.Add(_o.ModelPath);
        psi.ArgumentList.Add("--host"); psi.ArgumentList.Add(_o.Host);
        psi.ArgumentList.Add("--port"); psi.ArgumentList.Add(port.ToString(CultureInfo.InvariantCulture));
        psi.ArgumentList.Add("-c"); psi.ArgumentList.Add(_o.ContextSize.ToString(CultureInfo.InvariantCulture));
        if (_o.Threads > 0) { psi.ArgumentList.Add("-t"); psi.ArgumentList.Add(_o.Threads.ToString(CultureInfo.InvariantCulture)); }
        psi.ArgumentList.Add("--cache-type-k"); psi.ArgumentList.Add(_o.CacheTypeK);
        psi.ArgumentList.Add("--cache-type-v"); psi.ArgumentList.Add(_o.CacheTypeV);
        if (!_o.FlashAttention) { psi.ArgumentList.Add("--flash-attn"); psi.ArgumentList.Add("off"); }
        if (_o.EmbeddingMode)
        {
            // llama-server 的 /v1/embeddings 必须显式开启; 该开关与文本生成互斥 (llama.cpp 限制)
            psi.ArgumentList.Add("--embeddings");
        }
        psi.ArgumentList.Add("--jinja");
        foreach (var extra in _o.ExtraArgs) psi.ArgumentList.Add(extra);

        var p = new Process { StartInfo = psi };
        p.OutputDataReceived += (_, e) => { if (e.Data is not null) Append(_stdout, e.Data); };
        p.ErrorDataReceived += (_, e) => { if (e.Data is not null) Append(_stderr, e.Data); };

        if (!p.Start())
            throw new LlamaCppException(LlamaCppException.StartFailed, $"Process.Start 返回 false: {bin}");
        _p = p;
        p.BeginOutputReadLine();
        p.BeginErrorReadLine();

        var host = _o.Host is "0.0.0.0" or "" ? "127.0.0.1" : _o.Host;
        var url = $"http://{host}:{port.ToString(CultureInfo.InvariantCulture)}";
        var deadline = Environment.TickCount64 + _o.StartTimeoutMs;

        using var probe = new HttpClient { Timeout = TimeSpan.FromSeconds(5) };
        while (Environment.TickCount64 < deadline)
        {
            ct.ThrowIfCancellationRequested();
            if (p.HasExited)
                throw new LlamaCppException(LlamaCppException.StartFailed,
                    $"llama-server 提前退出 exit={p.ExitCode}; stderr 尾部: {Tail(_stderr)}");

            try
            {
                using var r = await probe.GetAsync(url + "/health", ct).ConfigureAwait(false);
                if (r.IsSuccessStatusCode)
                {
                    _baseUrl = url;
                    return;
                }
                // 503 = 仍在加载模型 (llama-server 语义), 继续等
            }
            catch (HttpRequestException) { /* 未监听, 继续等 */ }
            catch (TaskCanceledException) when (!ct.IsCancellationRequested) { /* 探针超时, 继续等 */ }

            await Task.Delay(250, ct).ConfigureAwait(false);
        }

        throw new LlamaCppException(LlamaCppException.StartTimeout,
            $"llama-server {_o.StartTimeoutMs}ms 内未就绪 ({url}); stderr 尾部: {Tail(_stderr)}");
    }

    private void Append(List<string> sink, string line)
    {
        lock (_logGate)
        {
            sink.Add(line);
            if (sink.Count > TailLines) sink.RemoveAt(0);
        }
    }

    private string Tail(List<string> sink)
    {
        lock (_logGate)
        {
            var n = Math.Min(12, sink.Count);
            return n == 0 ? "(空)" : string.Join(" | ", sink.Skip(sink.Count - n));
        }
    }

    public async ValueTask DisposeAsync()
    {
        var p = _p;
        _p = null;
        if (p is null) return;

        try
        {
            if (!p.HasExited)
            {
                p.Kill(entireProcessTree: true);
                using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
                await p.WaitForExitAsync(cts.Token).ConfigureAwait(false);
            }
        }
        catch (InvalidOperationException) { /* 已退出 */ }
        catch (OperationCanceledException) { /* 强制杀已发出 */ }
        finally
        {
            p.Dispose();
            _baseUrl = string.Empty;
        }
    }
}
