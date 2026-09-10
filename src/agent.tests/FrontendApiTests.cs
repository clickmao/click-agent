using System;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using Xunit;
using agent.frontendapi;

namespace agentframework.tests;

/// <summary>v0.19.0 P1 (R350): FrontendApi 契约 + Server — 信封解析/响应配对/未知 api 错误/真 TCP 往返。</summary>
public class FrontendApiTests : IDisposable
{
    private readonly FrontendApiServer? _server;
    private readonly int _port;

    public FrontendApiTests()
    {
        // R361: auth 关闭改用构造参数 (全局 env 在并行测试间串扰 — 真 bug)
        // 每测试独立端口 (并行安全): 47900 + 随机偏移
        _port = 47900 + (System.Environment.ProcessId % 500) + new Random().Next(50);
        _server = new FrontendApiServer(
            async (api, _) =>
            {
                var sync = FrontendApiRouter.Build(
                    snapshotBuilder: () => "{\"v\":1,\"agent\":{\"name\":\"click-agent\",\"status\":\"idle\"}}",
                    metaInfo: () => "{\"version\":\"0.20.4\",\"contract\":1}");
                return sync(api);
            },
            _ => { }, _port, access: new FrontendAccessControl(authDisabledOverride: true));
        _server.Start();
        // 等监听就绪
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
        throw new TimeoutException("server 未就绪");
    }

    private (Socket s, NetworkStream st) Connect()
    {
        var s = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
        s.Connect("127.0.0.1", _port);
        s.ReceiveTimeout = 5000;
        return (s, new NetworkStream(s, ownsSocket: false));
    }

    private static string ReadLine(NetworkStream st)
    {
        var sb = new StringBuilder();
        var one = new byte[1];
        while (st.Read(one, 0, 1) > 0)
        {
            if (one[0] == (byte)'\n') break;
            sb.Append((char)one[0]);
        }
        return sb.ToString();
    }

    [Fact]
    public void ParseRequest_ValidAndInvalid()
    {
        var ok = FrontendApiContract.ParseRequest("{\"v\":1,\"type\":\"req\",\"req_id\":\"r1\",\"api\":\"state.snapshot\",\"payload\":{}}");
        Assert.NotNull(ok);
        Assert.Equal("r1", ok!.ReqId);
        Assert.Equal("state.snapshot", ok.Api);
        // 缺 v / type 错 / 坏 JSON → null
        Assert.Null(FrontendApiContract.ParseRequest("{\"type\":\"req\",\"req_id\":\"r\",\"api\":\"a\"}"));
        Assert.Null(FrontendApiContract.ParseRequest("{\"v\":1,\"type\":\"event\",\"req_id\":\"r\",\"api\":\"a\"}"));
        Assert.Null(FrontendApiContract.ParseRequest("not-json"));
    }

    [Fact]
    public void Tcp_RoundTrip_SnapshotAndPing()
    {
        var (s, st) = Connect();
        try
        {
            var req = Encoding.UTF8.GetBytes("{\"v\":1,\"type\":\"req\",\"req_id\":\"r1\",\"api\":\"state.snapshot\"}\n");
            s.Send(req);
            var line = ReadLine(st);
            using var doc = System.Text.Json.JsonDocument.Parse(line);
            var r = doc.RootElement;
            Assert.Equal("resp", r.GetProperty("type").GetString());
            Assert.Equal("r1", r.GetProperty("req_id").GetString());
            Assert.True(r.GetProperty("ok").GetBoolean());
            Assert.Equal("click-agent", r.GetProperty("payload").GetProperty("agent").GetProperty("name").GetString());

            var req2 = Encoding.UTF8.GetBytes("{\"v\":1,\"type\":\"req\",\"req_id\":\"r2\",\"api\":\"meta.ping\"}\n");
            s.Send(req2);
            var line2 = ReadLine(st);
            using var doc2 = System.Text.Json.JsonDocument.Parse(line2);
            Assert.True(doc2.RootElement.GetProperty("payload").GetProperty("pong").GetBoolean());
        }
        finally { s.Close(); st.Dispose(); }
    }

    [Fact]
    public void Tcp_UnknownApi_StructuredError()
    {
        var (s, st) = Connect();
        try
        {
            var req = Encoding.UTF8.GetBytes("{\"v\":1,\"type\":\"req\",\"req_id\":\"rx\",\"api\":\"nope.what\"}\n");
            s.Send(req);
            var line = ReadLine(st);
            using var doc = System.Text.Json.JsonDocument.Parse(line);
            var r = doc.RootElement;
            Assert.False(r.GetProperty("ok").GetBoolean());
            Assert.Equal("unknown_api", r.GetProperty("error").GetProperty("code").GetString());
        }
        finally { s.Close(); st.Dispose(); }
    }

    [Fact]
    public void Tcp_BadEnvelope_BadPayloadError()
    {
        var (s, st) = Connect();
        try
        {
            var req = Encoding.UTF8.GetBytes("garbage-line\n");
            s.Send(req);
            var line = ReadLine(st);
            using var doc = System.Text.Json.JsonDocument.Parse(line);
            Assert.Equal("bad_payload", doc.RootElement.GetProperty("error").GetProperty("code").GetString());
        }
        finally { s.Close(); st.Dispose(); }
    }

    public void Dispose() => _server?.Dispose();
}
