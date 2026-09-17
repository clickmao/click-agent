using System.Text.Json;

namespace agent.vision;

/// <summary>
/// 屏幕任务信号 —— **由远端 LLM 的结构化输出给出**（合同字段 vision）。
/// 铁律: 本地模型不参与真假判定 —— 本地缺失/不可用/未加载时，本信号的解析结果完全不受影响。
/// 解析 fail-closed: JSON 缺字段 / 类型错 / 枚举外 ⇒ <see cref="None"/>（Needed=false ⇒ 不加载本地视觉模型）。
/// </summary>
public sealed record ScreenTaskSignal(bool Needed, string Kind, string Subgoal)
{
    /// <summary>合法 kind 取值（白名单，与渲染进远端契约的枚举逐字一致）。</summary>
    public static readonly string[] Kinds = { "screenshot_ui", "element_grounding", "screen_flow", "none" };

    /// <summary>未识别为屏幕任务（默认值；fail-closed 的落点）。</summary>
    public static readonly ScreenTaskSignal None = new(false, "none", string.Empty);

    private static bool InKinds(string? v)
    {
        foreach (var k in Kinds)
        {
            if (k == v)
            {
                return true;
            }
        }
        return false;
    }

    /// <summary>
    /// 解析远端返回的顶层 JSON 里的 vision 字段:
    /// <c>{"vision":{"needed":true,"kind":"screenshot_ui","subgoal":"..."}}</c>。
    /// 任何不合规 ⇒ None（绝不抛异常、绝不猜）。
    /// </summary>
    public static ScreenTaskSignal Parse(string? remoteJson)
    {
        if (string.IsNullOrWhiteSpace(remoteJson))
        {
            return None;
        }
        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(remoteJson);
        }
        catch (JsonException)
        {
            return None;
        }
        using (doc)
        {
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object || !root.TryGetProperty("vision", out var v) || v.ValueKind != JsonValueKind.Object)
            {
                return None;
            }
            if (!v.TryGetProperty("needed", out var n) || (n.ValueKind != JsonValueKind.True && n.ValueKind != JsonValueKind.False))
            {
                return None;
            }
            var needed = n.ValueKind == JsonValueKind.True;
            var kind = v.TryGetProperty("kind", out var k) && k.ValueKind == JsonValueKind.String ? k.GetString() : null;
            if (!InKinds(kind))
            {
                return None;
            }
            var subgoal = v.TryGetProperty("subgoal", out var s) && s.ValueKind == JsonValueKind.String ? s.GetString() ?? string.Empty : string.Empty;
            // 互斥: needed=true 不允许 kind=none; needed=false 不允许具体 kind
            if (needed != (kind != "none"))
            {
                return None;
            }
            return new ScreenTaskSignal(needed, kind!, subgoal);
        }
    }
}
