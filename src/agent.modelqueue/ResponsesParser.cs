using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;


/// <summary>R479: Responses 响应解析器 (JsonDocument, 零反射, AOT 安全; 解析失败一律 fail-closed)。</summary>
public static class ResponsesParser
{
    public const string TypeMessage = "message";
    public const string TypeFunctionCall = "function_call";
    public const string TypeReasoning = "reasoning";

    public static ResponsesResult Parse(string json)
    {
        var r = new ResponsesResult();
        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(json);
        }
        catch (Exception ex)
        {
            r.Failure = "unparsable:" + ex.GetType().Name;
            return r;
        }

        using (doc)
        {
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                r.Failure = "not_object";
                return r;
            }

            r.Id = Str(root, "id");
            r.Status = Str(root, "status");
            if (root.TryGetProperty("incomplete_details", out var inc) && inc.ValueKind == JsonValueKind.Object)
                r.IncompleteReason = Str(inc, "reason");

            if (root.TryGetProperty("error", out var err) && err.ValueKind == JsonValueKind.Object)
                r.Failure = "upstream_error:" + Str(err, "code") + Str(err, "message");

            if (root.TryGetProperty("output", out var outEl) && outEl.ValueKind == JsonValueKind.Array)
            {
                foreach (var item in outEl.EnumerateArray())
                {
                    var type = Str(item, "type");
                    switch (type)
                    {
                        case TypeMessage:
                            AppendMessageText(r, item);
                            break;
                        case TypeFunctionCall:
                            r.Items.Add(new ResponsesOutputItem
                            {
                                Type = type,
                                Name = Str(item, "name"),
                                ArgumentsJson = Str(item, "arguments"),
                                CallId = Str(item, "call_id"),
                            });
                            r.ToolCalls.Add(new ActionToolCall
                            {
                                Id = Str(item, "call_id"),
                                Name = Str(item, "name"),
                                ArgumentsJson = Str(item, "arguments") is { Length: > 0 } a ? a : "{}",
                            });
                            break;
                        case TypeReasoning:
                            var reasoning = ExtractReasoning(item);
                            r.ReasoningText = r.ReasoningText.Length == 0 ? reasoning : r.ReasoningText + "\n" + reasoning;
                            r.Items.Add(new ResponsesOutputItem { Type = type, Text = reasoning });
                            break;
                        default:
                            r.UnknownItems++;
                            break;
                    }
                }
            }

            ParseUsage(root, r.Usage);

            // fail-closed: 无可读面 (无正文 ∧ 无工具调用 ∧ 无状态) 或 output 全是未知类型 ⇒ 不可用。
            if (r.Failure == null && !r.HasText && r.ToolCalls.Count == 0)
            {
                if (r.UnknownItems > 0) r.Failure = "unknown_items_only";
                else if (r.Status.Length == 0) r.Failure = "no_status_no_output";
            }
        }

        return r;
    }

    private static void AppendMessageText(ResponsesResult r, JsonElement item)
    {
        if (!item.TryGetProperty("content", out var content) || content.ValueKind != JsonValueKind.Array) return;
        foreach (var block in content.EnumerateArray())
        {
            var bt = Str(block, "type");
            if (bt is "output_text" or "input_text" or "text")
            {
                var text = Str(block, "text");
                if (text.Length == 0) continue;
                r.Items.Add(new ResponsesOutputItem { Type = bt, Text = text });
                r.Text = r.Text.Length == 0 ? text : r.Text + "\n" + text;
            }
        }
    }

    private static string ExtractReasoning(JsonElement item)
    {
        if (!item.TryGetProperty("summary", out var summary) || summary.ValueKind != JsonValueKind.Array) return string.Empty;
        var sb = new StringBuilder();
        foreach (var s in summary.EnumerateArray())
        {
            var t = Str(s, "text");
            if (t.Length == 0) continue;
            if (sb.Length > 0) sb.Append('\n');
            sb.Append(t);
        }
        return sb.ToString();
    }

    private static void ParseUsage(JsonElement root, ResponsesUsage usage)
    {
        if (!root.TryGetProperty("usage", out var u) || u.ValueKind != JsonValueKind.Object) return;
        usage.Present = true;
        usage.InputTokens = Int(u, "input_tokens");
        usage.OutputTokens = Int(u, "output_tokens");
        if (u.TryGetProperty("input_tokens_details", out var d) && d.ValueKind == JsonValueKind.Object)
        {
            usage.CachedPresent = d.TryGetProperty("cached_tokens", out var c) && c.ValueKind == JsonValueKind.Number;
            usage.CachedTokens = Int(d, "cached_tokens");
        }
        if (u.TryGetProperty("output_tokens_details", out var od) && od.ValueKind == JsonValueKind.Object)
            usage.ReasoningTokens = Int(od, "reasoning_tokens");
    }

    private static string Str(JsonElement obj, string name)
        => obj.ValueKind == JsonValueKind.Object && obj.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String
            ? v.GetString() ?? string.Empty
            : string.Empty;

    private static int Int(JsonElement obj, string name)
        => obj.ValueKind == JsonValueKind.Object && obj.TryGetProperty(name, out var v)
            && v.ValueKind == JsonValueKind.Number && v.TryGetInt32(out var n) ? n : 0;
}
