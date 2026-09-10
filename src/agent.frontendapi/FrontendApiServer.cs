using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;

namespace agent.frontendapi;

/// <summary>
/// v0.19.0 P1 (R350): FrontendApiServer — TCP 47810 行 JSON 信封服务。
/// 分层: Server (传输/accept/行解析) → Router (api→handler) → DomainHandlers (状态域) → SnapshotBuilder。
/// P1 域: state.snapshot / state.hello / meta.ping (无 LLM 依赖; chat/ask 域 P1 后半接入 V2)。
/// 多客户端: accept 循环每连接一线程 (llm-manager 同模式); 单向推事件 P2。
/// </summary>
public sealed class FrontendApiServer : IDisposable
{
    private readonly int _port;
    private readonly Action<string> _log;
    private readonly CancellationTokenSource _cts = new();
    private Socket? _listener;
    private readonly Func<string, string, Task<string?>> _handler; // (api, payloadJson) → payloadJson (null=unknown_api)
    private readonly FrontendAccessControl _access; // R358: 鉴权+限流
    private bool _disposed;

    public FrontendApiServer(Func<string, string, Task<string?>> handler, Action<string> log,
        int port = FrontendApiContract.DefaultPort, FrontendAccessControl? access = null)
    {
        _handler = handler;
        _log = log;
        _port = port;
        _access = access ?? new FrontendAccessControl();
    }

    /// <summary>启动日志用: token (随机生成时打印; env 注入时不重复)。</summary>
    public string TokenHex => _access.TokenHex;

    public void Start()
    {
        _listener = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
        _listener.Bind(new IPEndPoint(IPAddress.Any, _port));
        _listener.Listen(16);
        _log($"frontendapi: 监听 :{_port} (契约 v1)");
        _ = Task.Run(AcceptLoopAsync);
    }

    private async Task AcceptLoopAsync()
    {
        while (!_cts.IsCancellationRequested)
        {
            try
            {
                var client = await _listener!.AcceptAsync(_cts.Token).ConfigureAwait(false);
                _ = Task.Run(() => ServeClientAsync(client));
            }
            catch (OperationCanceledException) { break; }
            catch (Exception ex) { _log($"frontendapi accept 异常: {ex.Message}"); }
        }
    }

    private async Task ServeClientAsync(Socket client)
    {
        try
        {
            // R358: 鉴权握手 — 首行必须 {"type":"auth","token":"..."}; 失败静默断连 (防枚举)
            if (_access.AuthEnabled && !await TryAuthHandshakeAsync(client).ConfigureAwait(false))
                return;

            var buf = new byte[16384];
            var pending = new StringBuilder();
            while (!_cts.IsCancellationRequested)
            {
                var n = await client.ReceiveAsync(new ArraySegment<byte>(buf), SocketFlags.None, _cts.Token).ConfigureAwait(false);
                if (n == 0) break;
                pending.Append(Encoding.UTF8.GetString(buf, 0, n));
                while (true)
                {
                    var text = pending.ToString();
                    var idx = text.IndexOf('\n');
                    if (idx < 0) break;
                    var line = text[..idx];
                    pending.Remove(0, idx + 1);
                    if (!_access.TryAcquire())
                    {
                        var busy = FrontendApiContract.FormatResponse("rate", false, "{}",
                            "busy", "限流/并发超限, 稍后重试");
                        var busyBytes = Encoding.UTF8.GetBytes(busy + "\n");
                        await client.SendAsync(new ArraySegment<byte>(busyBytes), SocketFlags.None, _cts.Token).ConfigureAwait(false);
                        continue;
                    }
                    string resp;
                    try { resp = await HandleLineAsync(line); }
                    finally { _access.Release(); }
                    var bytes = Encoding.UTF8.GetBytes(resp + "\n");
                    await client.SendAsync(new ArraySegment<byte>(bytes), SocketFlags.None, _cts.Token).ConfigureAwait(false);
                }
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception) { /* 客户端断开 */ }
        finally { try { client.Close(); } catch { } }
    }

    /// <summary>R358: auth 握手 — 首行 {"type":"auth","token":"..."}; 5s 超时/失败断连。</summary>
    private async Task<bool> TryAuthHandshakeAsync(Socket client)
    {
        try
        {
            using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(_cts.Token);
            timeoutCts.CancelAfter(5000);
            var buf = new byte[4096];
            var sb = new StringBuilder();
            while (true)
            {
                var n = await client.ReceiveAsync(new ArraySegment<byte>(buf), SocketFlags.None, timeoutCts.Token).ConfigureAwait(false);
                if (n == 0) return false;
                sb.Append(Encoding.UTF8.GetString(buf, 0, n));
                var text = sb.ToString();
                var idx = text.IndexOf('\n');
                if (idx < 0) continue;
                var line = text[..idx].Trim();
                if (line.Length > 4096) return false; // 超长 auth 行 = 恶意
                using var doc = System.Text.Json.JsonDocument.Parse(line);
                var root = doc.RootElement;
                if (!root.TryGetProperty("type", out var t) || t.GetString() != "auth") return false;
                var token = root.TryGetProperty("token", out var tk) ? tk.GetString() : null;
                return _access.ValidateToken(token);
            }
        }
        catch { return false; }
    }

    private async Task<string> HandleLineAsync(string line)
    {
        var req = FrontendApiContract.ParseRequest(line);
        if (req is null)
            return FrontendApiContract.FormatResponse("unknown", false, "{}",
                FrontendApiContract.ErrCodeBadPayload, "信封非法 (需 v:1/type:req/req_id/api)");
        try
        {
            var payload = await _handler(req.Api, req.PayloadJson).ConfigureAwait(false);
            if (payload is null)
                return FrontendApiContract.FormatResponse(req.ReqId, false, "{}",
                    FrontendApiContract.ErrCodeUnknownApi, $"未知 api: {req.Api}");
            return FrontendApiContract.FormatResponse(req.ReqId, true, payload);
        }
        catch (Exception ex)
        {
            return FrontendApiContract.FormatResponse(req.ReqId, false, "{}",
                FrontendApiContract.ErrCodeInternal, ex.Message);
        }
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        _cts.Cancel();
        try { _listener?.Close(); } catch { }
    }
}

/// <summary>R350: 状态域 + 元域 handler (P1; payload 由 caller 注入 — AgentRuntime 状态组装点)。</summary>
public static class FrontendApiRouter
{
    public static Func<string, string?> Build(
        Func<string> snapshotBuilder,   // state.snapshot payload 组装 (宿主注入)
        Func<string> metaInfo)          // meta.info
        => api => api switch
        {
            "state.snapshot" => snapshotBuilder(),
            "state.hello" => "{\"hello\":true}",
            "meta.ping" => "{\"pong\":true}",
            "meta.info" => metaInfo(),
            _ => null,
        };
}
