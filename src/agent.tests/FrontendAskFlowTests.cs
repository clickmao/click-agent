using System;
using System.Net.Sockets;
using System.Text;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Xunit;
using agent.core;
using agent.frontendapi;
namespace agent.tests;

/// <summary>
/// R375 (exp2 P0-1): ask 闭环 — **真 TCP + 真信封** (非 mock):
/// ① 问询发出 → 客户端真收到 ask 事件 (含 options[]) ② ask.reply → 等待中的调用拿到答案
/// ③ 未知 ask_id 显式拒绝且不误投 ④ cancel/超时 → null (诚实放弃) ⑤ 幂等重放不二次投递
/// 附带机检「响应与事件共用发送锁」: 每行必须能独立解析为完整 JSON (交错即失败)。
/// </summary>
public class FrontendAskFlowTests : IDisposable
{
    private sealed class StubAgent : IAgent
    {
        public string Id => "stub";
        public string Name => "stub";
        public AgentState State => default;
        public event EventHandler<AgentStateChangedEventArgs>? StateChanged { add { } remove { } }
        public event EventHandler<Message>? MessageReceived { add { } remove { } }
        public Task InitializeAsync(IAgentContext context, CancellationToken ct = default) => Task.CompletedTask;
        public Task<AgentResponse> ProcessAsync(Message message, CancellationToken ct = default) =>
            Task.FromResult(new AgentResponse { Content = "stub", Success = true });
        public Task<AgentResponse> ExecuteTaskAsync(agent.core.SubAgentTask task, CancellationToken ct = default) =>
            Task.FromResult(new AgentResponse { Content = "stub", Success = true });
        public Task<AgentResponse> RouteAsync(Message message, CancellationToken ct = default) =>
            Task.FromResult(new AgentResponse { Content = "stub", Success = true });
        public Task ShutdownAsync(CancellationToken ct = default) => Task.CompletedTask;
    }

    private readonly int _port;
    private readonly FrontendApiServer _server;
    private readonly FrontendEventHub _hub = new();
    private readonly FrontendPromptService _prompts;

    public FrontendAskFlowTests()
    {
        _port = 47700 + (Environment.ProcessId % 500) + new Random().Next(50);
        _prompts = new FrontendPromptService(_hub.EmitAsync, timeoutSeconds: 5);
        _hub.AttachAsk(_prompts);
        var router = new FrontendApiChatRouter(new StubAgent(), askSink: _hub.AskSink);
        _server = new FrontendApiServer(
            (api, payload) => router.HandleAsync(api, payload),
            _ => { }, _port, access: new FrontendAccessControl(authDisabledOverride: true));
        _hub.AttachServer(line => _server.EmitEventAsync(line));
        _server.Start();
        var deadline = DateTime.UtcNow.AddSeconds(5);
        while (DateTime.UtcNow < deadline)
        {
            try
            {
                using var s = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
                s.Connect("127.0.0.1", _port);
                s.Close();
                return;
            }
            catch { Thread.Sleep(50); }
        }
        throw new TimeoutException("frontendapi server 未就绪");
    }

    private (Socket s, NetworkStream st) ConnectAndRegister()
    {
        var s = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
        s.Connect("127.0.0.1", _port);
        s.ReceiveTimeout = 8000;
        var st = new NetworkStream(s, ownsSocket: false);
        // 先跑一次请求-响应, 保证服务端已把本连接登记为事件接收端 (消除登记竞态)
        using var d = JsonDocument.Parse(SendReq(s, st, "meta.ping", "{}", "warm"));
        Assert.True(d.RootElement.GetProperty("ok").GetBoolean());
        return (s, st);
    }

    private static string ReadLine(NetworkStream st)
    {
        var sb = new StringBuilder();
        var one = new byte[1];
        while (st.Read(one, 0, 1) > 0)
            if (one[0] == (byte)'\n') break;
            else sb.Append((char)one[0]);
        return sb.ToString();
    }

    /// <summary>读一行并**强制要求合法 JSON** (行交错/半行会在此炸)。</summary>
    private static JsonDocument ReadJson(NetworkStream st)
    {
        var line = ReadLine(st);
        Assert.False(string.IsNullOrWhiteSpace(line), "读到空行 (连接提前关闭?)");
        return JsonDocument.Parse(line);
    }

    /// <summary>读到首个 type 匹配的行 (事件可能先于响应到达)。</summary>
    /// <summary>R376: 事件与响应**不保证相对顺序** (并发派发下 ask_closed 可能先于 ask.* 的 resp)。
    /// 原实现把途中不匹配的行直接 Dispose → 先到达的事件被吞 → 后续断言假红。现暂存不丢。</summary>
    private readonly List<JsonDocument> _stash = new();

    private JsonDocument ReadUntil(NetworkStream st, string type)
    {
        for (var i = 0; i < _stash.Count; i++)
        {
            var d = _stash[i];
            if (d.RootElement.TryGetProperty("type", out var t0) && t0.GetString() == type)
            {
                _stash.RemoveAt(i);
                return d;
            }
        }
        for (var i = 0; i < 12; i++)
        {
            var d = ReadJson(st);
            if (d.RootElement.TryGetProperty("type", out var t) && t.GetString() == type) return d;
            _stash.Add(d);
        }
        throw new Xunit.Sdk.XunitException($"12 行内未收到 type={type} (事件/响应未按行送达)");
    }

    private string SendReq(Socket s, NetworkStream st, string api, string payload, string reqId = "r1")
    {
        s.Send(Encoding.UTF8.GetBytes(
            $"{{\"v\":1,\"type\":\"req\",\"req_id\":\"{reqId}\",\"api\":\"{api}\",\"payload\":{payload}}}\n"));
        using var d = ReadUntil(st, "resp");
        return d.RootElement.GetRawText();
    }

    private static CredentialRequest ChoiceRequest(int? timeoutSeconds = null)
    {
        var request = new CredentialRequest
        {
            ServiceName = "deploy",
            Purpose = "选择部署区域",
            TimeoutSeconds = timeoutSeconds,
        };
        request.Items.Add(new CredentialItem
        {
            Key = "region",
            DisplayName = "部署区域 (菜单)",
            Required = true,
            DataType = "choice",
            DefaultValue = "cn-north",
            Choices =
            {
                new CredentialChoice { Value = "cn-north", Label = "华北", Recommended = true },
                new CredentialChoice { Value = "cn-south", Label = "华南" },
            },
        });
        return request;
    }

    [Fact]
    public async Task 问询信封抵达客户端_回复后调用方拿到答案()
    {
        var (s, st) = ConnectAndRegister();
        try
        {
            // R527: 就绪探针连接 (ctor 里的 Connect 循环) 的注销在服务端异步读收口,
            // 原「立即断言 =1」与探针注销存在竞态 (轮内复现: Expected 1 / Actual 2) ⇒ 改为有界收敛后断言。
            var settle = DateTime.UtcNow.AddSeconds(3);
            while (_server.ClientCount > 1 && DateTime.UtcNow < settle)
            {
                await Task.Delay(20);
            }

            Assert.Equal(1, _server.ClientCount);
            var pending = _prompts.RequestCredentialsAsync(ChoiceRequest());

            string askId;
            using (var ask = ReadUntil(st, "event"))
            {
                Assert.Equal("ask", ask.RootElement.GetProperty("event").GetString());
                var p = ask.RootElement.GetProperty("payload");
                askId = p.GetProperty("ask_id").GetString()!;
                Assert.False(string.IsNullOrWhiteSpace(askId));
                Assert.Equal(5, p.GetProperty("timeout_s").GetInt32());
                Assert.Equal("deploy", p.GetProperty("service").GetString());
                var q = p.GetProperty("questions")[0];
                Assert.Equal("region", q.GetProperty("key").GetString());
                Assert.Equal("choice", q.GetProperty("data_type").GetString());
                Assert.Equal("cn-north", q.GetProperty("default_value").GetString());
                Assert.Equal(2, q.GetProperty("options").GetArrayLength());
                Assert.True(q.GetProperty("options")[0].GetProperty("recommended").GetBoolean());
            }

            using (var resp = JsonDocument.Parse(SendReq(s, st, "ask.reply",
                $"{{\"ask_id\":\"{askId}\",\"answers\":{{\"region\":\"cn-south\"}}}}", "a1")))
            {
                Assert.True(resp.RootElement.GetProperty("ok").GetBoolean());
                Assert.Equal("answered", resp.RootElement.GetProperty("payload").GetProperty("outcome").GetString());
                Assert.Equal(askId, resp.RootElement.GetProperty("payload").GetProperty("ask_id").GetString());
            }

            var answers = await pending;
            Assert.NotNull(answers);
            Assert.Equal("cn-south", answers!["region"]);
            Assert.True(_hub.Emitted >= 2, $"事件应经 hub 真送达 (Emitted={_hub.Emitted})");
            Assert.Equal(0, _hub.Dropped);
        }
        finally { s.Close(); st.Dispose(); }
    }

    [Fact]
    public async Task 未知ask_id_显式拒绝且不误投()
    {
        var (s, st) = ConnectAndRegister();
        try
        {
            var pending = _prompts.RequestCredentialsAsync(ChoiceRequest());
            string askId;
            using (var ask = ReadUntil(st, "event"))
                askId = ask.RootElement.GetProperty("payload").GetProperty("ask_id").GetString()!;

            using (var resp = JsonDocument.Parse(SendReq(s, st, "ask.reply",
                "{\"ask_id\":\"ask-forged\",\"answers\":{\"region\":\"cn-north\"}}", "a1")))
            {
                Assert.True(resp.RootElement.GetProperty("ok").GetBoolean()); // 请求已处理
                Assert.Equal("unknown_ask", resp.RootElement.GetProperty("payload").GetProperty("outcome").GetString());
            }
            await Task.Delay(200);
            Assert.False(pending.IsCompleted, "伪造 ask_id 不得投递答案");

            // 真 id 取消收尾 (诚实放弃 → null)
            using (var resp = JsonDocument.Parse(SendReq(s, st, "ask.cancel",
                $"{{\"ask_id\":\"{askId}\"}}", "a2")))
            {
                Assert.Equal("cancelled", resp.RootElement.GetProperty("payload").GetProperty("outcome").GetString());
            }
            Assert.Null(await pending);
        }
        finally { s.Close(); st.Dispose(); }
    }

    [Fact]
    public async Task 取消_返回null且下发关闭事件()
    {
        var (s, st) = ConnectAndRegister();
        try
        {
            var pending = _prompts.RequestCredentialsAsync(ChoiceRequest());
            string askId;
            using (var ask = ReadUntil(st, "event"))
                askId = ask.RootElement.GetProperty("payload").GetProperty("ask_id").GetString()!;

            SendReq(s, st, "ask.cancel", $"{{\"ask_id\":\"{askId}\"}}", "a1");
            Assert.Null(await pending);

            using var closed = ReadUntil(st, "event");
            Assert.Equal("ask_closed", closed.RootElement.GetProperty("event").GetString());
            Assert.Equal(askId, closed.RootElement.GetProperty("payload").GetProperty("ask_id").GetString());
            Assert.Equal("cancelled", closed.RootElement.GetProperty("payload").GetProperty("reason").GetString());
        }
        finally { s.Close(); st.Dispose(); }
    }

    [Fact]
    public async Task 超时_返回null且关闭事件带timeout()
    {
        var (s, st) = ConnectAndRegister();
        try
        {
            var pending = _prompts.RequestCredentialsAsync(ChoiceRequest(timeoutSeconds: 1));
            using (var ask = ReadUntil(st, "event"))
                Assert.Equal("ask", ask.RootElement.GetProperty("event").GetString());

            Assert.Null(await pending); // 超时 = 诚实放弃 (不伪造答案)

            using var closed = ReadUntil(st, "event");
            Assert.Equal("ask_closed", closed.RootElement.GetProperty("event").GetString());
            Assert.Equal("timeout", closed.RootElement.GetProperty("payload").GetProperty("reason").GetString());
        }
        finally { s.Close(); st.Dispose(); }
    }

    [Fact]
    public async Task 幂等_同ask_id重复提交不二次投递()
    {
        var (s, st) = ConnectAndRegister();
        try
        {
            var pending = _prompts.RequestCredentialsAsync(ChoiceRequest());
            string askId;
            using (var ask = ReadUntil(st, "event"))
                askId = ask.RootElement.GetProperty("payload").GetProperty("ask_id").GetString()!;

            var body = $"{{\"ask_id\":\"{askId}\",\"answers\":{{\"region\":\"cn-north\"}}}}";
            using (var r1 = JsonDocument.Parse(SendReq(s, st, "ask.reply", body, "a1")))
                Assert.Equal("answered", r1.RootElement.GetProperty("payload").GetProperty("outcome").GetString());
            Assert.Equal("cn-north", (await pending)!["region"]);

            using var r2 = JsonDocument.Parse(SendReq(s, st, "ask.reply", body, "a2"));
            Assert.Equal("already_answered", r2.RootElement.GetProperty("payload").GetProperty("outcome").GetString());
        }
        finally { s.Close(); st.Dispose(); }
    }

    [Fact]
    public void 信封缺ask_id_报bad_payload()
    {
        var (s, st) = ConnectAndRegister();
        try
        {
            using var resp = JsonDocument.Parse(SendReq(s, st, "ask.reply", "{}", "a1"));
            Assert.False(resp.RootElement.GetProperty("ok").GetBoolean());
            Assert.Equal("bad_payload", resp.RootElement.GetProperty("error").GetProperty("code").GetString());
        }
        finally { s.Close(); st.Dispose(); }
    }

    public void Dispose() => _server.Dispose();
}
