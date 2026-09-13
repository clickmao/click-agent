using System.Text;
using System.Text.Json;
using agent.core;

namespace agent.frontendapi;

/// <summary>
/// v0.19 P1 后半 (R355): chat 域异步 handler — chat.send 直通 IAgent.ProcessAsync (V2 完整管线)。
/// R375 (exp2 P0-1): 增 ask 域回程 — ask.reply / ask.cancel 经 IAskReplySink 打到同一 ask 通道 (幂等 + 未知 id 显式拒绝)。
/// 语义: 同步等待回复 (P2 流式 chat_delta); 会话 id 默认 "frontend-main" (跨请求保持上下文)。
/// </summary>
public sealed class FrontendApiChatRouter
{
    private readonly IAgent _agent;
    private readonly string _sessionId;
    private readonly IAskReplySink? _askSink;

    public FrontendApiChatRouter(IAgent agent, string? sessionId = null, IAskReplySink? askSink = null)
    {
        _agent = agent;
        _sessionId = sessionId ?? "frontend-main";
        _askSink = askSink;
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
            // R375 (exp2 P0-1): 问询回程 — 前端答复必须能落到等待中的 ask (否则 ask 永远超时 = 声称支持却打不通)
            case "ask.reply":
            case "ask.cancel":
            {
                if (!AskEnvelope.TryParseReply(payloadJson, out var reply) || reply is null)
                    throw new BadPayloadException($"{api} 需要非空 ask_id (payload: {{\"ask_id\":\"ask-xxxxxxxx\"}})");
                var cancel = reply.Cancel || api == "ask.cancel";
                // 结果语义只在 payload.outcome 表达: 外层 ok 表示"请求已处理", 内层再放一个 ok 会让
                // "请求成功但 ask 已过期" 出现两个含义相反的 ok (契约歧义) — 单一语义更利于前端。
                var outcomeText = "channel_unavailable";
                if (_askSink is not null)
                {
                    var outcome = _askSink.Complete(reply.AskId, cancel ? null : reply.Answers);
                    outcomeText = outcome switch
                    {
                        AskReplyOutcome.Answered => cancel ? "cancelled" : "answered",
                        AskReplyOutcome.UnknownAsk => "unknown_ask",
                        _ => "already_answered",
                    };
                }
                using var ms = new MemoryStream();
                using (var w = new Utf8JsonWriter(ms))
                {
                    w.WriteStartObject();
                    w.WriteString("ask_id", reply.AskId);
                    w.WriteString("outcome", outcomeText);
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
