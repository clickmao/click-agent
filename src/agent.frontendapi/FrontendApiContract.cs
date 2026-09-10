using System.Net.Sockets;
using System.Text;
using System.Text.Json;

namespace agent.frontendapi;

/// <summary>
/// v0.19.0 P1 (R350, 用户钦定): 前端统一接口契约 — 统一信封 (JSON Lines)。
/// 请求: {"v":1,"type":"req","req_id":"r1","api":"domain.action","payload":{...}}
/// 响应: {"v":1,"type":"resp","req_id":"r1","ok":true|false,"payload":{...},"error":{code,msg}?}
/// 事件: {"v":1,"type":"event","event":"domain_event","payload":{...}}
/// 错误码: unknown_api / bad_payload / busy / conflict / not_found / internal
/// STJ 手写序列化 (零反射 AOT; union 信封不进 source-gen — ModelQueue 同模式先例)。
/// </summary>
public static class FrontendApiContract
{
    public const int Version = 1;
    public const int DefaultPort = 47810;

    public static string ErrCodeUnknownApi = "unknown_api";
    public static string ErrCodeBadPayload = "bad_payload";
    public static string ErrCodeNotFound = "not_found";
    public static string ErrCodeInternal = "internal";

    /// <summary>解析一行请求信封; 非法 → null (调用方回 bad_payload)。</summary>
    public static FrontendRequest? ParseRequest(string line)
    {
        try
        {
            using var doc = JsonDocument.Parse(line);
            var r = doc.RootElement;
            if (!r.TryGetProperty("v", out var v) || v.GetInt32() != Version) return null;
            if (!r.TryGetProperty("type", out var t) || t.GetString() != "req") return null;
            if (!r.TryGetProperty("req_id", out var rid)) return null;
            if (!r.TryGetProperty("api", out var api)) return null;
            return new FrontendRequest
            {
                ReqId = rid.GetString() ?? "",
                Api = api.GetString() ?? "",
                PayloadJson = r.TryGetProperty("payload", out var p) ? p.GetRawText() : "{}",
            };
        }
        catch { return null; }
    }

    public static string FormatResponse(string reqId, bool ok, string payloadJson, string? errCode = null, string? errMsg = null)
    {
        using var ms = new MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartObject();
            w.WriteNumber("v", Version);
            w.WriteString("type", "resp");
            w.WriteString("req_id", reqId);
            w.WriteBoolean("ok", ok);
            w.WritePropertyName("payload");
            w.WriteRawValue(payloadJson, skipInputValidation: true);
            if (!ok)
            {
                w.WriteStartObject("error");
                w.WriteString("code", errCode ?? ErrCodeInternal);
                w.WriteString("msg", errMsg ?? "");
                w.WriteEndObject();
            }
            w.WriteEndObject();
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }

    public static string FormatEvent(string eventName, string payloadJson)
    {
        using var ms = new MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartObject();
            w.WriteNumber("v", Version);
            w.WriteString("type", "event");
            w.WriteString("event", eventName);
            w.WritePropertyName("payload");
            w.WriteRawValue(payloadJson, skipInputValidation: true);
            w.WriteEndObject();
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }
}

public sealed class FrontendRequest
{
    public string ReqId { get; init; } = "";
    public string Api { get; init; } = "";
    public string PayloadJson { get; init; } = "{}";
}
