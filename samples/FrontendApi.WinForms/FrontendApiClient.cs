using System.Net.Sockets;
using System.Text;
using System.Text.Json;

namespace Samples.FrontendApi.WinForms;

/// <summary>
/// AgentFrontendApi v1 契约响应 (见 src/agent.frontendapi/FrontendApiContract.cs)。
/// 信封: {"v":1,"type":"resp","req_id":"r1","ok":true,"payload":{...},"error":{code,msg}?}
/// </summary>
public sealed class FrontendResponse
{
    public string ReqId { get; set; } = string.Empty;
    public bool Ok { get; set; }
    public string Payload { get; set; } = "{}";
    public string ErrorCode { get; set; }
    public string ErrorMessage { get; set; }

    public override string ToString() =>
        Ok ? $"ok (req={ReqId})" : $"err {ErrorCode}: {ErrorMessage} (req={ReqId})";
}

/// <summary>
/// FrontendApi v1 TCP 行 JSON 客户端 (samples 演示用, 非 AOT)。
///
/// 协议要点 (实测自 FrontendApiServer / Program.cs 接线):
///   1. 鉴权: 若服务端 auth 开启 (默认开启, 仅 AGENTFRAMEWORK_FRONTEND_AUTH=0 关闭),
///      连接后**首行**必须 {"type":"auth","token":"..."}; 成功无任何响应, 失败直接静默断连。
///      → 客户端只能以"auth 后首次请求是否立刻断连"间接判定鉴权失败。
///   2. 请求: 每行 {"v":1,"type":"req","req_id":"r1","api":"domain.action","payload":{...}} + '\n'
///   3. 响应: 每行 {"v":1,"type":"resp","req_id":"...","ok":true|false,"payload":{...},"error":{...}}
///   4. 事件: 每行 {"v":1,"type":"event","event":"...","payload":{...}} (单向推送, 无 req_id)
///   5. 限流/并发超限: ok=false, error.code="busy" (旧实现 req_id 恒为 "rate", 无法关联 — 见 Improvements R367)
/// </summary>
public sealed class FrontendApiClient : IDisposable
{
    private TcpClient _tcp;
    private NetworkStream _stream;
    private readonly StringBuilder _pending = new();
    private readonly object _sync = new();
    private readonly Dictionary<string, TaskCompletionSource<FrontendResponse>> _waiting = new();
    private CancellationTokenSource _cts = new();
    private int _reqSeq;

    public bool IsConnected => _tcp != null && _tcp.Connected;

    /// <summary>收到任意一行 (调试/协议观测用) — 后台线程触发, UI 需 BeginInvoke。</summary>
    public event Action<string, string> LineReceived; // (方向 ">>"/"<<", 行内容)

    /// <summary>收到 event 信封 — 后台线程触发。</summary>
    public event Action<string, string> EventReceived; // (event 名, payload json)

    /// <summary>连接断开通知 — 后台线程触发。</summary>
    public event Action<string> Disconnected;

    public async Task ConnectAsync(string host, int port, int timeoutMs = 3000)
    {
        _tcp = new TcpClient();
        var connectTask = _tcp.ConnectAsync(host, port);
        var timeoutTask = Task.Delay(timeoutMs);
        if (await Task.WhenAny(connectTask, timeoutTask) == timeoutTask)
            throw new TimeoutException($"连接 {host}:{port} 超时 ({timeoutMs}ms)");
        await connectTask;
        _stream = _tcp.GetStream();
        _cts = new CancellationTokenSource();
        _ = Task.Run(ReceiveLoopAsync);
    }

    /// <summary>鉴权首行 (成功无响应; 失败服务端静默断连)。</summary>
    public async Task SendAuthAsync(string token)
    {
        var line = JsonSerializer.Serialize(new { type = "auth", token });
        await SendRawLineAsync(line);
    }

    /// <summary>发送 api 请求并等待对应 req_id 的响应。</summary>
    public Task<FrontendResponse> SendAsync(string api, object payload = null, int timeoutMs = 120000)
        => SendAsync(api, payload == null ? "{}" : JsonSerializer.Serialize(payload), timeoutMs);

    public async Task<FrontendResponse> SendAsync(string api, string payloadJson, int timeoutMs = 120000)
    {
        if (_stream == null) throw new InvalidOperationException("未连接");

        string reqId;
        lock (_sync) { reqId = "r" + (++_reqSeq); }

        var tcs = new TaskCompletionSource<FrontendResponse>(TaskCreationOptions.RunContinuationsAsynchronously);
        lock (_sync) _waiting[reqId] = tcs;

        var req = new { v = 1, type = "req", req_id = reqId, api, payload = JsonSerializer.Deserialize<JsonElement>(payloadJson) };
        await SendRawLineAsync(JsonSerializer.Serialize(req));

        var delay = Task.Delay(timeoutMs);
        if (await Task.WhenAny(tcs.Task, delay) == delay)
        {
            lock (_sync) _waiting.Remove(reqId);
            throw new TimeoutException($"api {api} 超时 ({timeoutMs}ms) — 服务端未回 req_id={reqId}");
        }
        return await tcs.Task;
    }

    private async Task SendRawLineAsync(string line)
    {
        var bytes = Encoding.UTF8.GetBytes(line + "\n");
        LineReceived?.Invoke(">>", line);
        try { await _stream.WriteAsync(bytes, 0, bytes.Length); await _stream.FlushAsync(); }
        catch (Exception ex) { FailAll(ex.Message); throw; }
    }

    private async Task ReceiveLoopAsync()
    {
        var buf = new byte[16384];
        try
        {
            while (!_cts.IsCancellationRequested)
            {
                var n = await _stream.ReadAsync(buf, 0, buf.Length, _cts.Token);
                if (n == 0) break;
                string chunk;
                lock (_sync)
                {
                    _pending.Append(Encoding.UTF8.GetString(buf, 0, n));
                    chunk = _pending.ToString();
                }
                int idx;
                while ((idx = chunk.IndexOf('\n')) >= 0)
                {
                    var line = chunk.Substring(0, idx).Trim();
                    lock (_sync) { _pending.Remove(0, idx + 1); }
                    chunk = chunk.Substring(idx + 1);
                    if (line.Length > 0) HandleLine(line);
                }
            }
        }
        catch (Exception)
        {
            // 断开
        }
        finally
        {
            Disconnected?.Invoke("连接已断开");
            FailAll("连接已断开");
        }
    }

    private void HandleLine(string line)
    {
        LineReceived?.Invoke("<<", line);
        try
        {
            using var doc = JsonDocument.Parse(line);
            var root = doc.RootElement;
            if (!root.TryGetProperty("type", out var t)) return;
            var type = t.GetString();

            if (type == "event")
            {
                var name = root.TryGetProperty("event", out var ev) ? ev.GetString() : "";
                var payload = root.TryGetProperty("payload", out var ep) ? ep.GetRawText() : "{}";
                EventReceived?.Invoke(name ?? "", payload);
                return;
            }
            if (type != "resp") return;

            var resp = new FrontendResponse
            {
                ReqId = root.TryGetProperty("req_id", out var rid) ? (rid.GetString() ?? "") : "",
                Ok = root.TryGetProperty("ok", out var ok) && ok.GetBoolean(),
                Payload = root.TryGetProperty("payload", out var p) ? p.GetRawText() : "{}",
            };
            if (root.TryGetProperty("error", out var err) && err.ValueKind == JsonValueKind.Object)
            {
                resp.ErrorCode = err.TryGetProperty("code", out var c) ? c.GetString() : null;
                resp.ErrorMessage = err.TryGetProperty("msg", out var m) ? m.GetString() : null;
            }

            TaskCompletionSource<FrontendResponse> target = null;
            lock (_sync)
            {
                if (_waiting.TryGetValue(resp.ReqId, out var hit))
                {
                    _waiting.Remove(resp.ReqId);
                    target = hit;
                }
                else if (_waiting.Count > 0)
                {
                    // 兼容: 旧服务端限流响应 req_id 恒为 "rate" (无法关联) —
                    // 退化为"完成最早未决请求", 避免演示界面永久挂起。
                    var first = _waiting.Keys.First();
                    target = _waiting[first];
                    _waiting.Remove(first);
                }
            }
            target?.TrySetResult(resp);
        }
        catch (Exception)
        {
            // 非法行: 仅记录
        }
    }

    private void FailAll(string why)
    {
        List<TaskCompletionSource<FrontendResponse>> all;
        lock (_sync) { all = _waiting.Values.ToList(); _waiting.Clear(); }
        foreach (var t in all)
            t.TrySetException(new IOException($"请求未完成: {why}"));
    }

    public void Dispose()
    {
        try { _cts.Cancel(); } catch { }
        try { _stream?.Close(); } catch { }
        try { _tcp?.Close(); } catch { }
    }
}
