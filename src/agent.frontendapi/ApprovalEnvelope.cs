using System.Text;
using System.Text.Json;

namespace agent.frontendapi;

/// <summary>approval.respond 的解析结果 (approved=true 批准, false 拒绝; Cancel 仅用于语义封口)。</summary>
public sealed record ApprovalReply(string ApprovalId, bool Approved, string? Reason, bool Cancel);

/// <summary>
/// R510: 审批域信封 (与 AskEnvelope 同构: v/type/event/payload; 手写 Utf8JsonWriter, 零反射 AOT 铁律)。
///   {"v":1,"type":"event","event":"approval.requested","payload":{approval_id,kind,summary,details,initiator,timeout_s}}
///   {"v":1,"type":"event","event":"approval.responded","payload":{approval_id,approved,answered_by,reason}}
/// 语义铁律 (与 IUserPromptService 契约一致): 拒绝/超时/取消一律**不批准**, 绝不伪造批准;
/// 每个 requested 必须有一个 responded 收口 (前端不会停在等待态)。
/// </summary>
public static class ApprovalEnvelope
{
    public const string EventRequested = "approval.requested";
    public const string EventResponded = "approval.responded";

    public static string BuildRequested(
        string approvalId, string kind, string summary, string details, string initiator, int timeoutSeconds)
    {
        using var ms = new MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartObject();
            w.WriteNumber("v", FrontendApiContract.Version);
            w.WriteString("type", "event");
            w.WriteString("event", EventRequested);
            w.WriteStartObject("payload");
            w.WriteString("approval_id", approvalId);
            w.WriteString("kind", kind);
            w.WriteString("summary", summary);
            w.WriteString("details", details);
            w.WriteString("initiator", initiator);
            w.WriteNumber("timeout_s", timeoutSeconds);
            w.WriteEndObject();
            w.WriteEndObject();
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }

    /// <summary>审批结果事件。answered_by 取 PromptAnswerSource 名 (RealUser/Denied/Timeout/MainAgentDelegate/AutoApproved) —— 审计可分辨真实批准与代答/自动批准。</summary>
    public static string BuildResponded(string approvalId, bool approved, string answeredBy, string reason)
    {
        using var ms = new MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartObject();
            w.WriteNumber("v", FrontendApiContract.Version);
            w.WriteString("type", "event");
            w.WriteString("event", EventResponded);
            w.WriteStartObject("payload");
            w.WriteString("approval_id", approvalId);
            w.WriteBoolean("approved", approved);
            w.WriteString("answered_by", answeredBy);
            w.WriteString("reason", reason);
            w.WriteEndObject();
            w.WriteEndObject();
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }

    /// <summary>
    /// 解析 approval.respond: {"approval_id":"apr-xxxxxxxx","approved":true,"reason":"..."}。
    /// 缺 approval_id 或 approved 非布尔 → false (调用方回 bad_payload; 不静默当拒绝)。
    /// </summary>
    public static bool TryParseResponse(string payloadJson, out ApprovalReply? reply)
    {
        reply = null;
        try
        {
            using var doc = JsonDocument.Parse(payloadJson);
            var r = doc.RootElement;
            if (r.ValueKind != JsonValueKind.Object) return false;
            if (!r.TryGetProperty("approval_id", out var idEl) || idEl.ValueKind != JsonValueKind.String) return false;
            var id = idEl.GetString();
            if (string.IsNullOrWhiteSpace(id)) return false;
            if (!r.TryGetProperty("approved", out var aEl)
                || aEl.ValueKind is not (JsonValueKind.True or JsonValueKind.False)) return false;
            var cancel = r.TryGetProperty("cancel", out var cEl) && cEl.ValueKind == JsonValueKind.True;
            var reason = r.TryGetProperty("reason", out var rEl) && rEl.ValueKind == JsonValueKind.String
                ? rEl.GetString() : null;
            reply = new ApprovalReply(id!, aEl.ValueKind == JsonValueKind.True, reason, cancel);
            return true;
        }
        catch { return false; }
    }
}
