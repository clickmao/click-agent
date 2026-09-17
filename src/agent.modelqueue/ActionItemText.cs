using System;
using System.Text.Json;

namespace agent.modelqueue;

/// <summary>
/// R538: 工具调用 → 前端「条目」文案 (kind / title / detail) 与输出尾裁剪。
///
/// 单源原则: 这里只从**已有的** <see cref="ActionToolCall"/> 事实派生展示要素 (工具名 + 参数 JSON + 输出),
/// 不重新执行、不二次渲染、不复制工具语义表 (kind 由 <see cref="ActionToolDecl"/> 常量派生)。
/// 零反射 (AOT 铁律): 只用 <see cref="JsonDocument"/> (非反射路径) 取参数, 手写裁剪, 不用 STJ 序列化。
/// </summary>
public static class ActionItemText
{
    /// <summary>detail (参数 JSON) 字符上限 —— 前端折叠展示用, 不无限放大事件体。</summary>
    public const int DetailCharCap = 2000;

    /// <summary>output_tail 字符上限 (取**尾部**: 命令的最后几行才是结论)。</summary>
    public const int OutputTailCharCap = 1200;

    /// <summary>title 字符上限。</summary>
    public const int TitleCharCap = 200;

    private const string TruncatedSuffix = "...[truncated]";

    /// <summary>工具名 → 条目 kind (前端按 kind 决定图标/渲染分支)。</summary>
    public static string KindOf(string? tool) => tool switch
    {
        ActionToolDecl.RunCommand => "command",
        ActionToolDecl.WriteFile => "file_write",
        ActionToolDecl.ReadFile => "file_read",
        ActionToolDecl.DeleteFile => "file_delete",
        ActionToolDecl.ListDir => "listing",
        _ => "other",
    };

    /// <summary>
    /// 从工具名 + 参数 JSON 派生 (kind, title, detail)。
    /// title = 工具名 + 主参数 (命令取 cmd, 文件类取 path); 参数不可解析 ⇒ title 只留工具名 (不伪造)。
    /// </summary>
    public static (string Kind, string Title, string Detail) Describe(string? tool, string? argsJson)
    {
        var name = tool ?? string.Empty;
        var kind = KindOf(name);
        var detail = Cap(argsJson ?? string.Empty, DetailCharCap);

        // 主参数键 = 声明面 schema 的 required[0] (与 ActionToolSpec 同源; 不另维护映射表 ⇒ 不会与工具 schema 漂移)。
        var key = ActionToolSpec.PrimaryArgKey(name);

        var primary = key.Length > 0 ? ReadString(argsJson, key) : null;
        var title = primary is { Length: > 0 } ? name + " " + primary : name;
        return (kind, Cap(title, TitleCharCap), detail);
    }

    /// <summary>
    /// 输出尾裁剪: (tail, lines_total, truncated)。
    /// lines_total 计**全量**输出的行数 (前端显示 "+N lines"), tail 只带末 cap 字符。
    /// </summary>
    public static (string Tail, int LinesTotal, bool Truncated) Tail(string? output)
    {
        var body = output ?? string.Empty;
        if (body.Length == 0) return (string.Empty, 0, false);
        var lines = 0;
        for (var i = 0; i < body.Length; i++) if (body[i] == '\n') lines++;
        // 尾换行不算出多一行 (与 wc -l 同口径): "ok\n" = 1 行, "a\nb" = 2 行 —— 前端显示的行数须为真实内容行数。
        var linesTotal = body[^1] == '\n' ? lines : lines + 1;
        var truncated = body.Length > OutputTailCharCap;
        var tail = truncated ? body.Substring(body.Length - OutputTailCharCap) : body;
        return (tail, linesTotal, truncated);
    }

    /// <summary>取参数 JSON 顶层字符串字段; 解析失败/字段缺失/非字符串 ⇒ null (绝不猜)。</summary>
    private static string? ReadString(string? argsJson, string key)
    {
        if (string.IsNullOrWhiteSpace(argsJson)) return null;
        try
        {
            using var doc = JsonDocument.Parse(argsJson);
            if (doc.RootElement.ValueKind != JsonValueKind.Object) return null;
            if (!doc.RootElement.TryGetProperty(key, out var v)) return null;
            return v.ValueKind == JsonValueKind.String ? v.GetString() : v.ToString();
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private static string Cap(string s, int max)
        => s.Length <= max ? s : s.Substring(0, max) + TruncatedSuffix;

    /// <summary>条目 id 兜底 (模型未给 call id 时按步号生成, 保证 started/completed 可配对)。</summary>
    public static string ItemIdOf(string? callId, int stepIndex)
        => string.IsNullOrWhiteSpace(callId)
            ? "item-" + stepIndex.ToString(System.Globalization.CultureInfo.InvariantCulture)
            : callId!;
}
