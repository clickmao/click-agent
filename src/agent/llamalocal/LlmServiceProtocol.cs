using System;
using System.Buffers;
using System.Buffers.Binary;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.llamalocal;

/// <summary>
/// v0.11.0 R103: 本地 LLM 服务化协议 (多 CLI 实例共享单次模型加载)。
/// 传输: Unix domain socket (Linux) / Named pipe (Windows), 长度前缀帧:
///   [4B big-endian payload length][payload = UTF-8 JSON]
/// 请求: {"op":"chat"|"embed"|"ping","text":...,"system":...,"max_tokens":N}
/// 响应: {"ok":true,"content":...,"tokens":N,"ms":N,"model":"..."} 或 {"ok":false,"error":...}
/// 序列化: STJ source-gen (AOT 零反射红线)。
/// </summary>
public sealed class LlmServiceProtocol
{
    public const string OpChat = "chat";
    public const string OpEmbed = "embed";
    public const string OpPing = "ping";

    public const int DefaultMaxFrame = 8 * 1024 * 1024; // 8MB 防御上限

    private readonly int _maxFrame;
    public LlmServiceProtocol(int maxFrame = DefaultMaxFrame) => _maxFrame = maxFrame;

    // ── DTO (source-gen 序列化) ──

    public sealed class Request
    {
        [JsonPropertyName("op")] public string Op { get; set; } = OpPing;
        [JsonPropertyName("text")] public string? Text { get; set; }
        [JsonPropertyName("system")] public string? System { get; set; }
        [JsonPropertyName("max_tokens")] public int MaxTokens { get; set; } = 512;
    }

    public sealed class Response
    {
        [JsonPropertyName("ok")] public bool Ok { get; set; }
        [JsonPropertyName("content")] public string? Content { get; set; }
        [JsonPropertyName("tokens")] public int Tokens { get; set; }
        [JsonPropertyName("ms")] public long Ms { get; set; }
        [JsonPropertyName("model")] public string? Model { get; set; }
        [JsonPropertyName("error")] public string? Error { get; set; }
    }



    // ── 帧读写 ──

    /// <summary>读一帧 (阻塞直到完整帧或流结束)。返回 null = 对端关闭。</summary>
    public Request? ReadRequest(Stream stream)
    {
        var header = ReadExact(stream, 4);
        if (header == null) return null;
        var len = BinaryPrimitives.ReadInt32BigEndian(header);
        if (len <= 0 || len > _maxFrame)
            throw new IOException($"帧长度非法: {len}");
        var payload = ReadExact(stream, len);
        if (payload == null) return null;
        return JsonSerializer.Deserialize(payload, LlmServiceJsonContext.Default.Request);
    }

    /// <summary>写一帧。</summary>
    public void WriteResponse(Stream stream, Response response)
    {
        var payload = JsonSerializer.SerializeToUtf8Bytes(response, LlmServiceJsonContext.Default.Response);
        var frame = new byte[4 + payload.Length];
        BinaryPrimitives.WriteInt32BigEndian(frame, payload.Length);
        Buffer.BlockCopy(payload, 0, frame, 4, payload.Length);
        stream.Write(frame, 0, frame.Length);
        stream.Flush();
    }

    private static byte[]? ReadExact(Stream stream, int count)
    {
        var buffer = new byte[count];
        var read = 0;
        while (read < count)
        {
            var n = stream.Read(buffer, read, count - read);
            if (n <= 0) return read == 0 ? null : null; // 对端关闭
            read += n;
        }
        return buffer;
    }

    /// <summary>客户端侧: 写请求帧。</summary>
    public void WriteRequest(Stream stream, Request request)
    {
        var payload = JsonSerializer.SerializeToUtf8Bytes(request, LlmServiceJsonContext.Default.Request);
        var frame = new byte[4 + payload.Length];
        BinaryPrimitives.WriteInt32BigEndian(frame, payload.Length);
        Buffer.BlockCopy(payload, 0, frame, 4, payload.Length);
        stream.Write(frame, 0, frame.Length);
        stream.Flush();
    }

    /// <summary>客户端侧: 读响应帧。返回 null = 对端关闭。</summary>
    public Response? ReadResponse(Stream stream)
    {
        var header = ReadExact(stream, 4);
        if (header == null) return null;
        var len = BinaryPrimitives.ReadInt32BigEndian(header);
        if (len <= 0 || len > _maxFrame)
            throw new IOException($"响应帧长度非法: {len}");
        var payload = ReadExact(stream, len);
        if (payload == null) return null;
        return JsonSerializer.Deserialize(payload, LlmServiceJsonContext.Default.Response);
    }

    /// <summary>socket 文件路径 (每个数据目录一个服务实例)。</summary>
    public static string SocketPath(string dataDir = "./data") =>
        Path.Combine(Path.GetFullPath(dataDir), "llm.sock");
}

/// <summary>STJ source-gen (AOT 零反射)。顶层 partial — 嵌套类内 [JsonSerializable] 不被生成器识别。</summary>
[JsonSerializable(typeof(agent.llamalocal.LlmServiceProtocol.Request))]
[JsonSerializable(typeof(agent.llamalocal.LlmServiceProtocol.Response))]
internal sealed partial class LlmServiceJsonContext : JsonSerializerContext;
