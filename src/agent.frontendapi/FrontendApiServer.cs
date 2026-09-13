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
    /// <summary>v0.21.1 (R367): 待解析行缓冲上限 (1MB) — 超过即断连, 防无换行数据无界增长。</summary>
    private const int MaxPendingBytes = 1 << 20;

    /// <summary>v0.21.1 (R367): 鉴权握手缓冲上限 (auth 行本身很小, 8KB 绰绰有余)。</summary>
    private const int MaxAuthBytes = 8192;

    /// <summary>R376 (⑫类断链): 单连接在途请求上限 (背压) — 请求并发派发后必须有界, 
    /// 否则一个客户端持续灌入行即可无限占用执行槽/线程。</summary>
    private const int MaxInflightPerClient = 8;

    private readonly int _port;
    private readonly Action<string> _log;
    private readonly CancellationTokenSource _cts = new();
    private Socket? _listener;
    private readonly Func<string, string, Task<string?>> _handler; // (api, payloadJson) → payloadJson (null=unknown_api)
    private readonly FrontendAccessControl _access; // R358: 鉴权+限流

    /// <summary>R375 (exp2 P0-1): 在线连接登记 — ask 事件信封的送达面 (每连接一把发送锁防行交错)。</summary>
    private readonly System.Collections.Concurrent.ConcurrentDictionary<ClientConn, byte> _clients = new();

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
        ClientConn? conn = null;
        try
        {
            // R358: 鉴权握手 — 首行必须 {"type":"auth","token":"..."}; 失败静默断连 (防枚举)
            var rest = string.Empty;
            if (_access.AuthEnabled)
            {
                var hs = await TryAuthHandshakeAsync(client).ConfigureAwait(false);
                if (!hs.Ok) return;
                // R376 (⑪类断链·握手残包): auth 之后的剩余字节必须交还请求循环, 不得丢弃
                rest = hs.Tail;
            }

            // R375: 鉴权通过才登记为事件接收端 (未鉴权连接不得收到 ask 信封)
            conn = new ClientConn(client);
            _clients[conn] = 0;
            var buf = new byte[16384];
            var pending = new StringBuilder(rest);
            while (!_cts.IsCancellationRequested)
            {
                // R376: 先排空缓冲 (含握手残包里的完整行) — 原结构只在收到新数据后才解析,
                // 残留的完整行会被无谓地推迟到下一次 Receive (若客户端不再发数据即永挂)。
                // R376 (⑫类断链): 排空只做「解析 + 派发」, 不 await 请求执行 —— 见 Dispatch。
                if (!DrainPendingAsync(pending, conn)) return;
                var n = await client.ReceiveAsync(new ArraySegment<byte>(buf), SocketFlags.None, _cts.Token).ConfigureAwait(false);
                if (n == 0) break;
                pending.Append(Encoding.UTF8.GetString(buf, 0, n));
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception) { /* 客户端断开 */ }
        finally
        {
            if (conn is not null)
            {
                // R376: 断开前给在途请求 2s 收尾 (有界, 不让连接线程永久等)
                await conn.WhenDrainedAsync(TimeSpan.FromSeconds(2)).ConfigureAwait(false);
                _clients.TryRemove(conn, out _);
            }
            try { client.Close(); } catch { }
        }
    }

    /// <summary>R358: auth 握手 — 首行 {"type":"auth","token":"..."}; 5s 超时/失败断连。
    /// R376 修复 (⑪类断链·握手残包): 原实现只取 '\n' 之前的内容, **同一 TCP 段中随后的字节被静默丢弃** ——
    /// 客户端把 auth 与首个请求合并发送 (换行分隔) 时首个请求凭空消失 (真机探针首跑挂起即此因)。
    /// 现返回换行之后的残包 (Tail), 由请求循环预置进待解析缓冲, 一个字节不丢。</summary>
    private async Task<(bool Ok, string Tail)> TryAuthHandshakeAsync(Socket client)
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
                if (n == 0) return (false, string.Empty);
                sb.Append(Encoding.UTF8.GetString(buf, 0, n));
                var text = sb.ToString();
                var idx = text.IndexOf('\n');
                // v0.21.1 (R367): 与请求循环同类的无界增长防护。
                // 原实现的 4096 检查只在"找到 '\n' 之后"生效, 未遇换行前 sb 可持续增长;
                // 且 auth 阶段位于限流/并发准入之前, 5s 窗口内可灌入大量数据 → 提前掐断。
                // R376: 上限只约束「尚未出现换行的 auth 行」, 换行之后的残包属请求侧 (另有 1MB 上限)。
                if (idx < 0)
                {
                    if (sb.Length > MaxAuthBytes) return (false, string.Empty);
                    continue;
                }
                var line = text[..idx].Trim();
                var rest = text[(idx + 1)..];
                if (line.Length > 4096) return (false, string.Empty); // 超长 auth 行 = 恶意
                using var doc = System.Text.Json.JsonDocument.Parse(line);
                var root = doc.RootElement;
                if (!root.TryGetProperty("type", out var t) || t.GetString() != "auth") return (false, string.Empty);
                var token = root.TryGetProperty("token", out var tk) ? tk.GetString() : null;
                return (_access.ValidateToken(token), rest);
            }
        }
        catch { return (false, string.Empty); }
    }

    /// <summary>R376: 排空待解析缓冲中的完整行 (含握手残包); 返回 false = 超上限应断连。
    /// 与旧内联循环语义一致: 行缓冲上限检查仍在处理完完整行之后 (只有不带换行的超长数据才断连)。</summary>
    /// <summary>v0.21.1: 行缓冲 → 逐行解析。R376: 改为同步排空 (解析 + 并发派发), 不 await 请求执行。</summary>
    private bool DrainPendingAsync(StringBuilder pending, ClientConn conn)
    {
        while (true)
        {
            var text = pending.ToString();
            var idx = text.IndexOf('\n');
            if (idx < 0) break;
            var line = text[..idx];
            pending.Remove(0, idx + 1);
            Dispatch(conn, line);
        }
        // v0.21.1 (R367): 不带 '\n' 的超长数据 = 恶意/异常客户端 → 断连。
        // 原实现 pending 无上限, 持续灌入无换行数据可致内存无界增长 (真缺陷)。
        if (pending.Length > MaxPendingBytes)
        {
            _log("frontendapi: 客户端行缓冲超过上限, 断开连接");
            return false;
        }
        return true;
    }

    /// <summary>
    /// R376 (⑫类断链·同连接回程饿死): 请求必须**并发派发**, 绝不在读循环里 await。
    /// 真机证据 (R376 探针): chat.send 处理器内部触发 ask 并等待答复 → 读循环被这条请求占住 →
    /// **同一条连接**上的 ask.reply 永远读不到 → ask 挂到 300s 超时, 菜单式问询在真机上无法闭环。
    /// 单测此前全绿的原因: 它们在带外直接发起 ask (读循环空闲), 属 test-blind-spot;
    /// 真机形状的回归锁见 FrontendAskSameConnTests (请求处理中触发 ask, 同连接答复)。
    /// 三条不变量: ①有界在途 (背压, 超限回 busy) ②异常必被观测 (不静默吞) ③发送面共用连接锁 (行不交错)。
    /// </summary>
    private void Dispatch(ClientConn conn, string line)
    {
        if (!conn.TryEnterInflight())
        {
            _ = conn.TryWriteLineAsync(FrontendApiContract.FormatResponse("unknown", false, "{}",
                "busy", "单连接在途请求超限, 稍后重试"), _cts.Token);
            return;
        }
        _ = Task.Run(async () =>
        {
            try
            {
                var resp = await ServeOneLineAsync(line).ConfigureAwait(false);
                await conn.TryWriteLineAsync(resp, _cts.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException) { }
            catch (Exception ex) { _log($"frontendapi 请求执行异常: {ex.Message}"); }
            finally { conn.ExitInflight(); }
        });
    }

    /// <summary>
    /// v0.21.1: 单行请求 — 解析 → 限流 → 执行 → 格式化。
    /// 修复 (R367): 限流响应曾把 req_id 硬编码为 "rate", 违反"响应回显 req_id"契约,
    /// 客户端无法关联被限流的请求 → 现回显真实 req_id (信封非法时用 "unknown")。
    /// </summary>
    private async Task<string> ServeOneLineAsync(string line)
    {
        var req = FrontendApiContract.ParseRequest(line);
        if (req is null)
            return FrontendApiContract.FormatResponse("unknown", false, "{}",
                FrontendApiContract.ErrCodeBadPayload, "信封非法 (需 v:1/type:req/req_id/api)");
        // 限流/并发准入 (解析后执行: 非法信封不再白占令牌)
        if (!_access.TryAcquire())
            return FrontendApiContract.FormatResponse(req.ReqId, false, "{}",
                "busy", "限流/并发超限, 稍后重试");
        try
        {
            var payload = await _handler(req.Api, req.PayloadJson).ConfigureAwait(false);
            if (payload is null)
                return FrontendApiContract.FormatResponse(req.ReqId, false, "{}",
                    FrontendApiContract.ErrCodeUnknownApi, $"未知 api: {req.Api}");
            return FrontendApiContract.FormatResponse(req.ReqId, true, payload);
        }
        // v0.21.1: 业务层显式声明的参数错误 → bad_payload (契约语义)。
        // 原实现被下方 catch-all 吞成 internal, 与契约定义的 bad_payload 语义不符。
        catch (FrontendApiChatRouter.BadPayloadException ex)
        {
            return FrontendApiContract.FormatResponse(req.ReqId, false, "{}",
                FrontendApiContract.ErrCodeBadPayload, ex.Message);
        }
        catch (Exception ex)
        {
            return FrontendApiContract.FormatResponse(req.ReqId, false, "{}",
                FrontendApiContract.ErrCodeInternal, ex.Message);
        }
        finally
        {
            _access.Release();
        }
    }

    /// <summary>R375 (exp2 P0-1): 向所有在线客户端推送事件信封; 返回实际送达连接数 (0 = 无人监听, 不伪造送达)。</summary>
    public async Task<int> EmitEventAsync(string envelopeLine)
    {
        if (_clients.IsEmpty) return 0;
        var sent = 0;
        foreach (var conn in _clients.Keys)
            if (await conn.TryWriteLineAsync(envelopeLine, _cts.Token).ConfigureAwait(false)) sent++;
        return sent;
    }

    /// <summary>在线客户端数 (诊断/真机探针用)。</summary>
    public int ClientCount => _clients.Count;

    /// <summary>
    /// R375: 单连接发送面 — 响应与事件信封**共用一把锁**。
    /// 原实现只有请求-响应 (天然串行), 加入事件推送后若无锁, 并发写同一 socket 会把两行 JSON 交错 → 客户端解析必坏。
    /// </summary>
    private sealed class ClientConn
    {
        private readonly Socket _sock;
        private readonly SemaphoreSlim _gate = new(1, 1);
        private int _inflight;

        public ClientConn(Socket sock) => _sock = sock;

        /// <summary>R376: 在途请求计数 (背压 + 断开前收尾); 超限返回 false 由调用方回 busy。</summary>
        public bool TryEnterInflight()
        {
            if (Interlocked.Increment(ref _inflight) <= MaxInflightPerClient) return true;
            Interlocked.Decrement(ref _inflight);
            return false;
        }

        public void ExitInflight() => Interlocked.Decrement(ref _inflight);

        public int Inflight => Volatile.Read(ref _inflight);

        /// <summary>R376: 有界等待在途请求收尾 (连接关闭路径用, 不让连接线程永久等)。</summary>
        public async Task WhenDrainedAsync(TimeSpan timeout)
        {
            var deadline = Environment.TickCount64 + (long)timeout.TotalMilliseconds;
            while (Inflight > 0 && Environment.TickCount64 < deadline)
                await Task.Delay(25).ConfigureAwait(false);
        }

        public Task WriteLineAsync(string line, CancellationToken ct) => TryWriteLineAsync(line, ct);

        public async Task<bool> TryWriteLineAsync(string line, CancellationToken ct)
        {
            var bytes = Encoding.UTF8.GetBytes(line + "\n");
            await _gate.WaitAsync(ct).ConfigureAwait(false);
            try
            {
                await _sock.SendAsync(new ArraySegment<byte>(bytes), SocketFlags.None, ct).ConfigureAwait(false);
                return true;
            }
            catch { return false; }
            finally { _gate.Release(); }
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
