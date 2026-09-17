using System;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Xunit;
using agent.core;
using agent.frontendapi;
namespace agent.tests;

/// <summary>
/// R376 (⑫类断链·同连接回程饿死) — **真机形状**回归锁:
/// 请求处理器**内部**触发 ask 并等待答复 (真机 chat.send 正是这样: EvidenceGate → 菜单问询),
/// 客户端在**同一条连接**上回 ask.reply。修复前读循环被该请求占住 → 答复永不被读 → 真机 300s 挂死。
/// 注: R375 的 FrontendAskFlowTests 在**带外**发起 ask (读循环空闲), 因此掩盖了这个缺陷 —— test-blind-spot。
/// </summary>
public class FrontendAskSameConnTests : IDisposable
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

    public FrontendAskSameConnTests()
    {
        _port = 47860 + (Environment.ProcessId % 400) + new Random().Next(40);
        _prompts = new FrontendPromptService(_hub.EmitAsync, timeoutSeconds: 6);
        _hub.AttachAsk(_prompts);
        var router = new FrontendApiChatRouter(new StubAgent(), askSink: _hub.AskSink);
        // 关键: 处理器在请求内 await 问询 (模拟 V2 管线内 EvidenceGate 的阻塞式问询)
        _server = new FrontendApiServer(
            async (api, payload) =>
            {
                // 与真机 host 同一接线形状: ask 域回程交给 router (Program.cs 同构), 不可漏
                switch (api)
                {
                    case "ask.reply":
                    case "ask.cancel":
                        return await router.HandleAsync(api, payload).ConfigureAwait(false);
                    case "chat.send":
                    {
                        var answers = await _prompts.RequestCredentialsAsync(ChoiceRequest()).ConfigureAwait(false);
                        var picked = answers is not null && answers.TryGetValue("目标", out var v) ? v : null;
                        return picked is null
                            ? "{\"reply\":\"(无答复)\",\"answered\":false}"
                            : $"{{\"reply\":\"(已按 {picked} 继续)\",\"answered\":true}}";
                    }
                    case "meta.ping":
                        return "{\"pong\":true}";
                    default:
                        return null;
                }
            },
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

    private (Socket s, NetworkStream st) Connect()
    {
        var s = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
        s.Connect("127.0.0.1", _port);
        s.ReceiveTimeout = 10000; // 修复前此超时即失败信号 (答复永不被读)
        return (s, new NetworkStream(s, ownsSocket: false));
    }

    /// <summary>按字节收行再整体 UTF-8 解码 (逐字节 (char) 转换会把多字节汉字读成乱码)。</summary>
    private static string ReadLine(NetworkStream st)
    {
        var ms = new MemoryStream();
        var one = new byte[1];
        while (st.Read(one, 0, 1) > 0)
        {
            if (one[0] == (byte)'\n') break;
            ms.WriteByte(one[0]);
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }

    private static JsonDocument ReadUntil(NetworkStream st, string type, string? reqId = null)
    {
        for (var i = 0; i < 16; i++)
        {
            var line = ReadLine(st);
            Assert.False(string.IsNullOrWhiteSpace(line), "读到空行 (连接提前关闭?)");
            var d = JsonDocument.Parse(line);
            if (d.RootElement.TryGetProperty("type", out var t) && t.GetString() == type)
            {
                if (reqId is null) return d;
                if (d.RootElement.TryGetProperty("req_id", out var r) && r.GetString() == reqId) return d;
            }
            d.Dispose();
        }
        throw new Xunit.Sdk.XunitException($"16 行内未收到 type={type} req_id={reqId}");
    }

    private static void Send(Socket s, string api, string payload, string reqId)
    {
        s.Send(Encoding.UTF8.GetBytes(
            $"{{\"v\":1,\"type\":\"req\",\"req_id\":\"{reqId}\",\"api\":\"{api}\",\"payload\":{payload}}}\n"));
    }

    private static CredentialRequest ChoiceRequest()
    {
        var request = new CredentialRequest
        {
            ServiceName = "EvidenceGate/general",
            Purpose = "指代对象确认 (菜单)",
        };
        request.Items.Add(new CredentialItem
        {
            Key = "目标",
            DisplayName = "子任务1_指代对象",
            Required = true,
            DataType = "choice",
            Choices =
            {
                new CredentialChoice { Value = "读文件", Label = "读文件", Recommended = true },
                new CredentialChoice { Value = "写文档", Label = "写文档" },
            },
        });
        return request;
    }

    [Fact]
    public async Task 请求处理中触发ask_同连接答复可被读取并续跑()
    {
        var (s, st) = Connect();
        try
        {
            // 1) 请求内触发 ask (读循环此刻"忙着"执行该请求 —— 修复前这里就死锁)
            Send(s, "chat.send", "{\"text\":\"帮我看下这个\"}", "c1");
            using var ask = ReadUntil(st, "event");
            Assert.Equal("ask", ask.RootElement.GetProperty("event").GetString());
            var askId = ask.RootElement.GetProperty("payload").GetProperty("ask_id").GetString()!;

            // 2) 同一条连接回答复 → 必须被读到 (修复前: 永不读 → ReadLine 超时)
            Send(s, "ask.reply", $"{{\"ask_id\":\"{askId}\",\"answers\":{{\"目标\":\"读文件\"}}}}", "a1");
            using (var ack = ReadUntil(st, "resp", "a1"))
                Assert.Equal("answered", ack.RootElement.GetProperty("payload").GetProperty("outcome").GetString());

            // 3) 请求继续跑完, 答复内容确实进了后续执行
            using var done = ReadUntil(st, "resp", "c1");
            Assert.True(done.RootElement.GetProperty("ok").GetBoolean());
            var payload = done.RootElement.GetProperty("payload").GetRawText();
            Assert.Contains("读文件", payload);
            Assert.Contains("\"answered\":true", payload);
        }
        finally { s.Close(); st.Dispose(); }
    }

    [Fact]
    public async Task 长请求在途时_同连接其它请求不被饿死()
    {
        var (s, st) = Connect();
        try
        {
            Send(s, "chat.send", "{\"text\":\"帮我看下这个\"}", "c1");
            using var ask = ReadUntil(st, "event");
            var askId = ask.RootElement.GetProperty("payload").GetProperty("ask_id").GetString()!;

            // 长请求仍挂在 ask 上 → 同连接的普通请求必须照常得到响应 (并发派发的直接证据)
            Send(s, "meta.ping", "{}", "p2");
            using (var pong = ReadUntil(st, "resp", "p2"))
                Assert.True(pong.RootElement.GetProperty("payload").GetProperty("pong").GetBoolean());

            Send(s, "ask.reply", $"{{\"ask_id\":\"{askId}\",\"answers\":{{\"目标\":\"写文档\"}}}}", "a1");
            using var done = ReadUntil(st, "resp", "c1");
            Assert.Contains("写文档", done.RootElement.GetProperty("payload").GetRawText());
        }
        finally { s.Close(); st.Dispose(); }
    }

    public void Dispose() => _server.Dispose();
}
