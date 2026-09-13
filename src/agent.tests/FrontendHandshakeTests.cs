using System;
using System.Linq;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using Xunit;
using agent.frontendapi;

namespace agentframework.tests;

/// <summary>
/// R376 (⑪类断链·握手残包): **真 TCP** 证明 —— auth 行与首个请求**同一次写入** (同一 TCP 段到达) 时,
/// 首个请求不得被静默丢弃。
/// 修复前: 服务端在鉴权握手时取走换行前的 auth 行, 换行之后的字节被直接丢弃 →
/// 客户端等不到任何响应 (真机探针首跑挂起的真实根因)。
/// 修复后: 握手把残包交还请求循环并预置进待解析缓冲。
/// </summary>
public class FrontendHandshakeTests : IDisposable
{
    private const string Token = "r376-test-token";
    private const string AuthLine = "{\"type\":\"auth\",\"token\":\"r376-test-token\"}";

    private readonly int _port;
    private readonly FrontendApiServer _server;

    public FrontendHandshakeTests()
    {
        _port = 48300 + (Environment.ProcessId % 400) + new Random().Next(50);
        var route = FrontendApiRouter.Build(
            snapshotBuilder: () => "{\"ok\":true}",
            metaInfo: () => "{\"version\":\"0.22.0\"}");
        _server = new FrontendApiServer(
            (api, _) => Task.FromResult(route(api)),
            _ => { }, _port, access: new FrontendAccessControl(tokenOverride: Token));
        _server.Start();
        var deadline = DateTime.UtcNow.AddSeconds(5);
        while (DateTime.UtcNow < deadline)
        {
            try
            {
                using var s = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
                s.Connect("127.0.0.1", _port);
                s.Close();
                break;
            }
            catch { Thread.Sleep(50); }
        }
    }

    private static string Req(string id) =>
        $"{{\"v\":1,\"type\":\"req\",\"req_id\":\"{id}\",\"api\":\"meta.ping\",\"payload\":{{}}}}";

    private Socket Connect()
    {
        var s = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
        s.Connect("127.0.0.1", _port);
        s.ReceiveTimeout = 4000;
        return s;
    }

    private static void Send(Socket s, string text) =>
        s.Send(Encoding.UTF8.GetBytes(text), SocketFlags.None);

    /// <summary>读到 n 行或超时/对端关闭; 返回已读到的完整行。</summary>
    private static string[] ReadLines(Socket s, int want)
    {
        var sb = new StringBuilder();
        var buf = new byte[4096];
        var deadline = DateTime.UtcNow.AddSeconds(4);
        while (DateTime.UtcNow < deadline)
        {
            try
            {
                var n = s.Receive(buf, SocketFlags.None);
                if (n == 0) break; // 对端关闭
                sb.Append(Encoding.UTF8.GetString(buf, 0, n));
                if (sb.ToString().Split('\n', StringSplitOptions.RemoveEmptyEntries).Length >= want) break;
            }
            catch (SocketException) { break; }
        }
        return sb.ToString().Split('\n', StringSplitOptions.RemoveEmptyEntries);
    }

    [Fact]
    public void 鉴权与首个请求同段一次写入_请求不被丢弃()
    {
        using var s = Connect();
        // 关键: auth 与请求**合并成一次 SendAsync** (同一 TCP 段) — 修复前请求被吞掉
        Send(s, AuthLine + "\n" + Req("r1") + "\n");
        var lines = ReadLines(s, 1);
        Assert.True(lines.Length >= 1, "同段发送时首个请求被丢弃 (响应 0 行)");
        Assert.Contains("\"req_id\":\"r1\"", lines[0]);
        Assert.Contains("pong", lines[0]);
    }

    [Fact]
    public void 同段多个请求_全部处理且按req_id关联()
    {
        using var s = Connect();
        Send(s, AuthLine + "\n" + Req("r1") + "\n" + Req("r2") + "\n");
        var lines = ReadLines(s, 2);
        Assert.Equal(2, lines.Length);
        // R376 契约澄清: 并发派发下**响应顺序不保证**, 客户端必须按 req_id 关联
        // (原断言了顺序 —— 那要求读循环串行执行, 正是⑫类断链的成因, 不能作为契约)
        Assert.Single(lines.Where(l => l.Contains("\"req_id\":\"r1\"")));
        Assert.Single(lines.Where(l => l.Contains("\"req_id\":\"r2\"")));
    }

    [Fact]
    public void 握手后另发_常规路径不回归()
    {
        using var s = Connect();
        Send(s, AuthLine + "\n");
        Thread.Sleep(150);
        Send(s, Req("r1") + "\n");
        var lines = ReadLines(s, 1);
        Assert.Single(lines);
        Assert.Contains("pong", lines[0]);
    }

    [Fact]
    public void 非法token同段请求_静默断连不响应()
    {
        using var s = Connect();
        Send(s, "{\"type\":\"auth\",\"token\":\"wrong\"}\n" + Req("r1") + "\n");
        var lines = ReadLines(s, 1);
        Assert.Empty(lines); // 契约: 鉴权失败不响应 (防枚举)
    }

    public void Dispose() => _server.Dispose();
}
