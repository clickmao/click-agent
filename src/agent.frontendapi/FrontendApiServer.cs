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
    private readonly Func<string, string?> _handler; // api → payloadJson (null=unknown_api)
    private bool _disposed;

    public FrontendApiServer(Func<string, string?> handler, Action<string> log, int port = FrontendApiContract.DefaultPort)
    {
        _handler = handler;
        _log = log;
        _port = port;
    }

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
                    var resp = HandleLine(line);
                    var bytes = Encoding.UTF8.GetBytes(resp + "\n");
                    await client.SendAsync(new ArraySegment<byte>(bytes), SocketFlags.None, _cts.Token).ConfigureAwait(false);
                }
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception) { /* 客户端断开 */ }
        finally { try { client.Close(); } catch { } }
    }

    private string HandleLine(string line)
    {
        var req = FrontendApiContract.ParseRequest(line);
        if (req is null)
            return FrontendApiContract.FormatResponse("unknown", false, "{}",
                FrontendApiContract.ErrCodeBadPayload, "信封非法 (需 v:1/type:req/req_id/api)");
        try
        {
            var payload = _handler(req.Api);
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
