using System.Text.Json;

namespace agent.exploration;

/// <summary>
/// v0.13.2 G1 — JSON 修复插件 (确定性规则族; 校验=System.Text.Json 原生 parser 当权威)。
/// 规则族覆盖用户提供的实例: undefined→null / {"nested":} 缺值补 {} / 末尾多余 } 删除。
/// </summary>
public sealed class JsonRepairPlugin : IFormatRepairPlugin
{
    public string Format => "json";

    public bool CanDetect(string text)
    {
        var t = text.TrimStart();
        return t.StartsWith('{') || t.StartsWith('[') || text.Contains("```json", StringComparison.OrdinalIgnoreCase);
    }

    public (int Start, int Length)? FindCandidate(string text)
    {
        if (string.IsNullOrEmpty(text)) return null;
        // 首个 { 或 [ 到最后一个 } 或 ] — 括号域扫描 (宽容: 修复器随后处理内部破损):
        int s = -1, e = -1;
        for (var i = 0; i < text.Length; i++)
        {
            if (s < 0 && (text[i] == '{' || text[i] == '[')) s = i;
            if (text[i] == '}' || text[i] == ']') e = i;
        }
        return s >= 0 && e > s ? (s, e - s + 1) : null;
    }

    public IReadOnlyList<string> Validate(string text)
    {
        var errors = new List<string>();
        try
        {
            using var doc = JsonDocument.Parse(text);
        }
        catch (JsonException ex)
        {
            errors.Add($"json parse: {ex.Message}");
        }
        return errors;
    }

    public (string Fixed, int ChangedN) Repair(string text)
    {
        var changed = 0;
        var t = text;
        // 规则1: undefined / NaN / Infinity → null (JSON 不支持):
        foreach (var bad in new[] { "undefined", "NaN", "Infinity", "-Infinity" })
        {
            if (t.Contains(bad, StringComparison.Ordinal))
            {
                t = System.Text.RegularExpressions.Regex.Replace(
                    t, $@"(?<=[:\[,]\s*){System.Text.RegularExpressions.Regex.Escape(bad)}(?=\s*[,\]}}])", "null");
                changed++;
            }
        }
        // 规则2: Python 字面量 True/False/None → true/false/null:
        foreach (var (bad, good) in new[] { ("True", "true"), ("False", "false"), ("None", "null") })
        {
            var replaced = System.Text.RegularExpressions.Regex.Replace(
                t, $@"(?<=[:\[,]\s*){bad}(?=\s*[,\]}}])", good);
            if (replaced != t) { t = replaced; changed++; }
        }
        // 规则2b: 单引号字符串 → 双引号 (键与值; 简化: 成对替换 — 已有双引号体内不受影响因 JSON 无单引号字符串):
        if (t.Contains('\''))
        {
            t = t.Replace('\'', '"');
            changed++;
        }
        // 规则3: 尾逗号 (},] / ,] / ,}):
        var t2 = System.Text.RegularExpressions.Regex.Replace(t, ",(\\s*[\\]}])", "$1");
        if (t2 != t) { t = t2; changed++; }
        // 规则5(前置): 缺值 (":}" 或 ":," → ":{}") — 用户实例 {"nested": }:
        var t5 = System.Text.RegularExpressions.Regex.Replace(t, @":(\s*)([,\]}]|$)", ":{}$1");
        if (t5 != t) { t = t5; changed++; }
        // 规则4: 栈感知括号修复 (类型匹配闭合/丢弃多余/尾部补齐) —
        // 用户实例回放: {"nested": }}} → 补缺值 {} 后栈顶类型不匹配的 } 被替换为 ], 尾部补齐:
        var stack = new List<char>();
        var sb = new System.Text.StringBuilder();
        var inStr = false;
        var escape = false;
        foreach (var c in t)
        {
            if (escape) { escape = false; sb.Append(c); continue; }
            if (c == '\\' && inStr) { escape = true; sb.Append(c); continue; }
            if (c == '"') { inStr = !inStr; sb.Append(c); continue; }
            if (inStr) { sb.Append(c); continue; }
            if (c == '{') { stack.Add('}'); sb.Append(c); }
            else if (c == '[') { stack.Add(']'); sb.Append(c); }
            else if (c == '}' || c == ']')
            {
                if (stack.Count > 0)
                {
                    var want = stack[^1];
                    stack.RemoveAt(stack.Count - 1);
                    sb.Append(want); // 类型匹配的闭合 (错型自动纠正)
                }
                // 栈空的多余闭合 — 丢弃 (用户实例"末尾多余的 } 删除"语义):
            }
            else sb.Append(c);
        }
        // 补齐未闭合 (尾部):
        for (var i = stack.Count - 1; i >= 0; i--) sb.Append(stack[i]);
        if (sb.ToString() != t) changed++;
        t = sb.ToString();
        return (t, changed);
    }
}
