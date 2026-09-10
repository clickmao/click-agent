using System.Text;
using System.Text.Json;
using agent.core;

namespace agent.frontendapi;

/// <summary>
/// v0.19 P1 后半 (R355): chat 域异步 handler — chat.send 直通 IAgent.ProcessAsync (V2 完整管线)。
/// 语义: 同步等待回复 (P2 流式 chat_delta); 会话 id 默认 "frontend-main" (跨请求保持上下文)。
/// </summary>
public sealed class FrontendApiChatRouter
{
    private readonly IAgent _agent;
    private readonly string _sessionId;

    public FrontendApiChatRouter(IAgent agent, string? sessionId = null)
    {
        _agent = agent;
        _sessionId = sessionId ?? "frontend-main";
    }

    /// <summary>api → payloadJson; 未知 api → null。</summary>
    public async Task<string?> HandleAsync(string api, string payloadJson, CancellationToken ct = default)
    {
        switch (api)
        {
            case "chat.send":
            {
                using var doc = JsonDocument.Parse(payloadJson);
                var text = doc.RootElement.TryGetProperty("text", out var t) ? t.GetString() : null;
                if (string.IsNullOrWhiteSpace(text))
                    throw new BadPayloadException("chat.send 需要 text 字段");
                var resp = await _agent.ProcessAsync(new Message
                {
                    SessionId = _sessionId,
                    Role = MessageRole.User,
                    Content = text,
                }, ct).ConfigureAwait(false);
                // AOT: 手写序列化 (零反射 — 项目铁律)
                using var ms = new MemoryStream();
                using (var w = new Utf8JsonWriter(ms))
                {
                    w.WriteStartObject();
                    w.WriteString("reply", resp.Content);
                    w.WriteBoolean("success", resp.Success);
                    w.WriteEndObject();
                }
                return Encoding.UTF8.GetString(ms.ToArray());
            }
            case "meta.ping":
                return "{\"pong\":true}";
            default:
                return null;
        }
    }

    public sealed class BadPayloadException(string msg) : Exception(msg);
}
