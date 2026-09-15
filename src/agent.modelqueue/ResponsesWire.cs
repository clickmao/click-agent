using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;

/// <summary>Responses 输入项种类 (协议层 typed item; 不把一切塞进一段文本)。</summary>
public enum ResponsesItemKind
{
    /// <summary>对话消息 (role + content[])。用户输入 = 独立字段, 不与本地指示混写。</summary>
    Message,

    /// <summary>工具执行结果回灌 (call_id + output), 独立 item。</summary>
    FunctionCallOutput,
}

/// <summary>
/// R479: Responses 协议**输入项** (typed)。构建后不可变 (值语义), 便于逐字节复现。
/// </summary>
public sealed class ResponsesInputItem
{
    public ResponsesItemKind Kind { get; private init; }

    public string Role { get; private init; } = "user";

    public string Text { get; private init; } = string.Empty;

    public string CallId { get; private init; } = string.Empty;

    public string Output { get; private init; } = string.Empty;

    public static ResponsesInputItem UserText(string text)
        => new() { Kind = ResponsesItemKind.Message, Role = "user", Text = text };

    public static ResponsesInputItem SystemText(string text)
        => new() { Kind = ResponsesItemKind.Message, Role = "system", Text = text };

    public static ResponsesInputItem AssistantText(string text)
        => new() { Kind = ResponsesItemKind.Message, Role = "assistant", Text = text };

    /// <summary>动作环回灌: 工具结果作为独立 typed item (不混进 user 文本)。</summary>
    public static ResponsesInputItem FunctionCallOutput(string callId, string output)
        => new() { Kind = ResponsesItemKind.FunctionCallOutput, CallId = callId ?? string.Empty, Output = output ?? string.Empty };
}

/// <summary>
/// R479: Responses 协议**真实输入数据格式** —— 手写 JSON 写入器 (零反射, AOT 安全)。
/// 字段面取自协议实测 (R479 三通道均 200): model / instructions / input[] / tools[] /
/// max_output_tokens / store:false / prompt_cache_key。
/// `instructions` 与 `input[]` 是**两个独立字段** (本地指示/权限类内容走 instructions, 用户输入走 input),
/// 不靠"整包塞成一段文本"表达结构。
/// </summary>
public static class ResponsesWire
{
    /// <summary>协议无状态: 实测 store:false 照常 ⇒ 历史仍由我方全量传, 前缀仍在我方可控面。</summary>
    public const string StoreFalse = "\"store\":false";

    public static string BuildRequest(
        string model,
        string instructions,
        IReadOnlyList<ResponsesInputItem> input,
        string? toolsJson = null,
        int? maxOutputTokens = null,
        string? promptCacheKey = null)
    {
        var sb = new StringBuilder(1024);
        sb.Append("{\"model\":\"").Append(Escape(model)).Append('"');
        if (!string.IsNullOrEmpty(instructions))
            sb.Append(",\"instructions\":\"").Append(Escape(instructions)).Append('"');
        sb.Append(",\"input\":[");
        for (var i = 0; i < input.Count; i++)
        {
            if (i > 0) sb.Append(',');
            AppendItem(sb, input[i]);
        }
        sb.Append(']');
        if (!string.IsNullOrEmpty(toolsJson)) sb.Append(",\"tools\":").Append(toolsJson);
        if (maxOutputTokens is > 0) sb.Append(",\"max_output_tokens\":").Append(maxOutputTokens.Value);
        sb.Append(',').Append(StoreFalse);
        if (!string.IsNullOrEmpty(promptCacheKey))
            sb.Append(",\"prompt_cache_key\":\"").Append(Escape(promptCacheKey)).Append('"');
        sb.Append('}');
        return sb.ToString();
    }

    private static void AppendItem(StringBuilder sb, ResponsesInputItem item)
    {
        if (item.Kind == ResponsesItemKind.FunctionCallOutput)
        {
            sb.Append("{\"type\":\"function_call_output\",\"call_id\":\"").Append(Escape(item.CallId))
              .Append("\",\"output\":\"").Append(Escape(item.Output)).Append("\"}");
            return;
        }

        // assistant 复述走 output_text, 其余角色走 input_text (协议事实)。
        var content = string.Equals(item.Role, "assistant", StringComparison.Ordinal) ? "output_text" : "input_text";
        sb.Append("{\"type\":\"message\",\"role\":\"").Append(Escape(item.Role))
          .Append("\",\"content\":[{\"type\":\"").Append(content)
          .Append("\",\"text\":\"").Append(Escape(item.Text)).Append("\"}]}");
    }

    /// <summary>JSON 字符串体转义 (手写; 禁 STJ 反射序列化)。</summary>
    internal static string Escape(string s)
    {
        var sb = new StringBuilder(s.Length + 8);
        foreach (var c in s)
        {
            switch (c)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                case '\b': sb.Append("\\b"); break;
                case '\f': sb.Append("\\f"); break;
                default:
                    if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4", System.Globalization.CultureInfo.InvariantCulture));
                    else sb.Append(c);
                    break;
            }
        }
        return sb.ToString();
    }
}

/// <summary>Responses 输出项 (解析后; 只保留校准所需字段)。</summary>
public sealed class ResponsesOutputItem
{
    public string Type { get; set; } = string.Empty;

    public string Text { get; set; } = string.Empty;

    public string Name { get; set; } = string.Empty;

    public string ArgumentsJson { get; set; } = string.Empty;

    public string CallId { get; set; } = string.Empty;
}

/// <summary>
/// R479: 供应商 usage 口径 (真值面)。**未上报 ≠ 0**: 缺字段 ⇒ Present=false (R474–R477 铁律)。
/// </summary>
public sealed class ResponsesUsage
{
    public bool Present { get; set; }

    public bool CachedPresent { get; set; }

    public int InputTokens { get; set; }

    public int CachedTokens { get; set; }

    public int OutputTokens { get; set; }

    public int ReasoningTokens { get; set; }

    /// <summary>新算 token = input − cached (供应商自洽口径); 任一侧缺失 ⇒ null (不冒充 0)。</summary>
    public int? NewTokens => Present && CachedPresent ? Math.Max(0, InputTokens - CachedTokens) : null;
}

/// <summary>Responses 响应解析结果 (协议字段面; <see cref="Failure"/> 非空 ⇒ 不可用, fail-closed)。</summary>
public sealed class ResponsesResult
{
    public string Id { get; set; } = string.Empty;

    public string Status { get; set; } = string.Empty;

    /// <summary>incomplete_details.reason (如 max_output_tokens)。</summary>
    public string IncompleteReason { get; set; } = string.Empty;

    public string Text { get; set; } = string.Empty;

    public string ReasoningText { get; set; } = string.Empty;

    public List<ResponsesOutputItem> Items { get; } = new();

    public List<ActionToolCall> ToolCalls { get; } = new();

    public ResponsesUsage Usage { get; set; } = new();

    /// <summary>未知 item 计数 (不静默丢弃; 全未知 ⇒ fail-closed)。</summary>
    public int UnknownItems { get; set; }

    public string? Failure { get; set; }

    public bool HasText => Text.Length > 0;
}

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
