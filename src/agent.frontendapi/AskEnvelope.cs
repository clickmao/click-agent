using System.Text;
using System.Text.Json;

namespace agent.frontendapi;

/// <summary>menu 问询选项 (前端可直接渲染为菜单项)。</summary>
public sealed record AskOption(string Value, string Label, bool Recommended);

/// <summary>
/// menu 问询单题 (R375 · exp2 P0-3): 选项/数据类型/多选/默认值必须**进通道**,
/// 不得只拼进 Display 文本 (旧实现把菜单拼进 DisplayName, 前端无法渲染)。
/// </summary>
public sealed record AskQuestion(
    string Key,
    string Display,
    bool Required,
    bool Sensitive,
    string DataType,
    bool MultiSelect,
    IReadOnlyList<AskOption> Options,
    string? DefaultValue);

/// <summary>ask.reply / ask.cancel 的解析结果 (answers=null 且 Cancel=true 表示取消)。</summary>
public sealed record AskReply(string AskId, Dictionary<string, string>? Answers, bool Cancel);

/// <summary>
/// R375 (exp2 P0-2/P0-3): ask 域信封 — 与 FrontendApiContract 同构 (v/type/event/payload):
///   {"v":1,"type":"event","event":"ask","payload":{ask_id,service,purpose,timeout_s,group_size,questions:[...]}}
///   {"v":1,"type":"event","event":"ask_closed","payload":{ask_id,reason}}
/// 手写 Utf8JsonWriter (零反射 AOT 铁律; 手写枚举避免 STJ source-gen 之外的动态路径)。
/// </summary>
public static class AskEnvelope
{
    public const string EventAsk = "ask";
    public const string EventAskClosed = "ask_closed";

    public static string BuildAsk(
        string askId, string service, string purpose, int timeoutSeconds, int groupSize,
        IEnumerable<AskQuestion> questions)
    {
        using var ms = new MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartObject();
            w.WriteNumber("v", FrontendApiContract.Version);
            w.WriteString("type", "event");
            w.WriteString("event", EventAsk);
            w.WriteStartObject("payload");
            w.WriteString("ask_id", askId);
            w.WriteString("service", service);
            w.WriteString("purpose", purpose);
            w.WriteNumber("timeout_s", timeoutSeconds);
            w.WriteNumber("group_size", groupSize);
            w.WriteStartArray("questions");
            foreach (var q in questions)
            {
                w.WriteStartObject();
                w.WriteString("key", q.Key);
                w.WriteString("display", q.Display);
                w.WriteBoolean("required", q.Required);
                w.WriteBoolean("sensitive", q.Sensitive);
                w.WriteString("data_type", q.DataType);
                w.WriteBoolean("multi_select", q.MultiSelect);
                if (q.DefaultValue is not null) w.WriteString("default_value", q.DefaultValue);
                w.WriteStartArray("options");
                foreach (var o in q.Options)
                {
                    w.WriteStartObject();
                    w.WriteString("value", o.Value);
                    w.WriteString("label", o.Label);
                    w.WriteBoolean("recommended", o.Recommended);
                    w.WriteEndObject();
                }
                w.WriteEndArray();
                w.WriteEndObject();
            }
            w.WriteEndArray();
            w.WriteEndObject();
            w.WriteEndObject();
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }

    /// <summary>问询关闭事件 (P1-4/P1-5): 前端必须能区分 已答/超时/取消/被覆盖。</summary>
    public static string BuildClosed(string askId, string reason)
    {
        using var ms = new MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartObject();
            w.WriteNumber("v", FrontendApiContract.Version);
            w.WriteString("type", "event");
            w.WriteString("event", EventAskClosed);
            w.WriteStartObject("payload");
            w.WriteString("ask_id", askId);
            w.WriteString("reason", reason);
            w.WriteEndObject();
            w.WriteEndObject();
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }

    /// <summary>
    /// 解析 ask.reply / ask.cancel 的 payload: {"ask_id":"...","answers":{"k":"v"},"cancel":false}。
    /// 缺 ask_id / 非法 JSON → false (调用方回 bad_payload; 不静默吞)。
    /// </summary>
    public static bool TryParseReply(string payloadJson, out AskReply? reply)
    {
        reply = null;
        try
        {
            using var doc = JsonDocument.Parse(payloadJson);
            var r = doc.RootElement;
            if (r.ValueKind != JsonValueKind.Object) return false;
            if (!r.TryGetProperty("ask_id", out var idEl) || idEl.ValueKind != JsonValueKind.String) return false;
            var askId = idEl.GetString();
            if (string.IsNullOrWhiteSpace(askId)) return false;

            var cancel = r.TryGetProperty("cancel", out var cEl) && cEl.ValueKind == JsonValueKind.True;
            Dictionary<string, string>? answers = null;
            if (!cancel && r.TryGetProperty("answers", out var aEl) && aEl.ValueKind == JsonValueKind.Object)
            {
                answers = new Dictionary<string, string>(StringComparer.Ordinal);
                foreach (var p in aEl.EnumerateObject())
                {
                    answers[p.Name] = p.Value.ValueKind == JsonValueKind.String
                        ? p.Value.GetString() ?? string.Empty
                        : p.Value.ValueKind is JsonValueKind.Number or JsonValueKind.True or JsonValueKind.False
                            ? p.Value.GetRawText()
                            : string.Empty;
                }
            }
            reply = new AskReply(askId, answers, cancel);
            return true;
        }
        catch { return false; }
    }
}
