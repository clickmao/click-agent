using System;
using System.Buffers.Binary;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace agent.llamalocal;

/// <summary>
/// v0.11.0 R103: LLM 服务客户端 — CLI 实例侧的共享模型访问。
/// 每次请求短连接 (连接→发帧→收帧→关), 串行语义由服务端排队保证;
/// 短连接避免长连接僵尸态, 实例崩溃不影响其他实例与服务。
/// 无服务时 IsAvailable=false → 调用方回落进程内加载 (独占模式, 行为兼容旧版)。
/// </summary>
public sealed class LlmServiceClient
{
    private readonly string _socketPath;
    private readonly LlmServiceProtocol _protocol = new();
    private readonly ILogger? _logger;

    public LlmServiceClient(string socketPath, ILogger? logger = null)
    {
        _socketPath = socketPath;
        _logger = logger;
    }

    /// <summary>服务是否可用 (socket 存在且 ping 得通)。</summary>
    public bool IsAvailable()
    {
        try
        {
            var resp = Request(new LlmServiceProtocol.Request { Op = LlmServiceProtocol.OpPing }, timeoutMs: 2000);
            return resp?.Ok == true;
        }
        catch
        {
            return false;
        }
    }

    /// <summary>chat 推理 (经共享服务)。服务不可用/失败返回 null — 调用方决定回落。</summary>
    public async Task<LlmServiceProtocol.Response?> ChatAsync(string system, string text, int maxTokens = 512, int timeoutMs = 300_000)
    {
        return await Task.Run(() => Request(new LlmServiceProtocol.Request
        {
            Op = LlmServiceProtocol.OpChat,
            System = system,
            Text = text,
            MaxTokens = maxTokens,
        }, timeoutMs));
    }

    /// <summary>embedding (经共享服务 bge)。失败返回 null。</summary>
    public async Task<LlmServiceProtocol.Response?> EmbedAsync(string text, int timeoutMs = 30_000)
    {
        return await Task.Run(() => Request(new LlmServiceProtocol.Request
        {
            Op = LlmServiceProtocol.OpEmbed,
            Text = text,
        }, timeoutMs));
    }

    /// <summary>同步短连接请求。异常一律外抛 (调用方按 IsAvailable 语义自查)。</summary>
    public LlmServiceProtocol.Response? Request(LlmServiceProtocol.Request req, int timeoutMs)
    {
        if (!File.Exists(_socketPath))
            return null;

        using var sock = new Socket(AddressFamily.Unix, SocketType.Stream, ProtocolType.Unspecified);
        var ep = new UnixDomainSocketEndPoint(_socketPath);
        var ar = sock.BeginConnect(ep, null, null);
        if (!ar.AsyncWaitHandle.WaitOne(Math.Min(timeoutMs, 3000)))
            return null;
        sock.EndConnect(ar);
        sock.ReceiveTimeout = timeoutMs;
        sock.SendTimeout = timeoutMs;

        using var stream = new NetworkStream(sock, ownsSocket: false);
        _protocol.WriteRequest(stream, req);
        var resp = _protocol.ReadResponse(stream);
        return resp;
    }
}
