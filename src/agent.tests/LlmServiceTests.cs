using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;
using agent.llamalocal;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.11.0 R103: LLM 服务化 (多 CLI 实例共享单次模型加载) — 协议帧/存活探测/服务回环 E2E。
/// 真模型不进单测 (体积/耗时), 用帧回环 + 假服务验证传输与互斥语义。
/// </summary>
public class LlmServiceTests
{
    private static string TempSock()
    {
        var p = Path.Combine(Path.GetTempPath(), $"llm-test-{Guid.NewGuid():N}.sock");
        File.Delete(p); // 清残留
        return p;
    }

    [Fact]
    public void Protocol_FrameRoundtrip()
    {
        var proto = new LlmServiceProtocol();
        using var ms = new MemoryStream();
        proto.WriteRequest(ms, new LlmServiceProtocol.Request { Op = "chat", Text = "你好", MaxTokens = 64 });
        ms.Position = 0;
        var back = proto.ReadRequest(ms);
        Assert.NotNull(back);
        Assert.Equal("chat", back!.Op);
        Assert.Equal("你好", back.Text);
        Assert.Equal(64, back.MaxTokens);
    }

    [Fact]
    public void Protocol_ResponseRoundtrip_WithChineseAndPunctuation()
    {
        var proto = new LlmServiceProtocol();
        using var ms = new MemoryStream();
        proto.WriteResponse(ms, new LlmServiceProtocol.Response
        {
            Ok = true, Content = "回答：2+3=5，完成。", Tokens = 9, Ms = 42, Model = "bge-local",
        });
        ms.Position = 0;
        var back = proto.ReadResponse(ms);
        Assert.NotNull(back);
        Assert.True(back!.Ok);
        Assert.Equal("回答：2+3=5，完成。", back.Content);
        Assert.Equal(9, back.Tokens);
    }

    [Fact]
    public void IsAlive_NoSocket_False()
    {
        Assert.False(LlmServiceHost.IsAlive("/tmp/definitely-not-exists.sock"));
    }

    [Fact]
    public void IsAlive_ListeningSocket_True()
    {
        var sock = TempSock();
        try
        {
            using var lsock = new Socket(AddressFamily.Unix, SocketType.Stream, ProtocolType.Unspecified);
            lsock.Bind(new UnixDomainSocketEndPoint(sock));
            lsock.Listen(2);
            Assert.True(LlmServiceHost.IsAlive(sock));
        }
        finally
        {
            File.Delete(sock);
        }
    }

    [Fact]
    public async Task ServiceLoop_PingEcho_ThroughRealSocket()
    {
        var sock = TempSock();
        try
        {
            using var lsock = new Socket(AddressFamily.Unix, SocketType.Stream, ProtocolType.Unspecified);
            lsock.Bind(new UnixDomainSocketEndPoint(sock));
            lsock.Listen(4);

            // 最小服务循环: ping → pong (真实帧协议路径)
            var server = Task.Run(() =>
            {
                using var client = lsock.Accept();
                using var stream = new NetworkStream(client, ownsSocket: false);
                var proto = new LlmServiceProtocol();
                var req = proto.ReadRequest(stream);
                var resp = new LlmServiceProtocol.Response
                {
                    Ok = true,
                    Content = req!.Op == LlmServiceProtocol.OpPing ? "pong" : "unknown",
                };
                proto.WriteResponse(stream, resp);
            });

            var client2 = new LlmServiceClient(sock);
            var resp = client2.Request(new LlmServiceProtocol.Request { Op = LlmServiceProtocol.OpPing }, 5000);
            await server;
            Assert.NotNull(resp);
            Assert.True(resp!.Ok);
            Assert.Equal("pong", resp.Content);
        }
        finally
        {
            File.Delete(sock);
        }
    }

    [Fact]
    public void Client_NoSocket_ReturnsNull_NotThrow()
    {
        var client = new LlmServiceClient("/tmp/definitely-not-exists.sock");
        var resp = client.Request(new LlmServiceProtocol.Request { Op = "chat", Text = "x" }, 1000);
        Assert.Null(resp);
        Assert.False(client.IsAvailable());
    }

    [Fact]
    public void SocketPath_UnderDataDir()
    {
        var p = LlmServiceProtocol.SocketPath("/tmp/afdata");
        Assert.Equal("/tmp/afdata/llm.sock", p);
    }
}
