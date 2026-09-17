using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;

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
