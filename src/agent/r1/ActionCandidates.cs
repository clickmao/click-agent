using System;
using System.Collections.Generic;
using System.Text.Json;
using agent.modelqueue;

namespace agent.r1;

/// <summary>
/// R610（RF0004.2 · M3 第一刀）—— **动作候选**的本地机械裁选器。
///
/// 设计动因（Fable 5.1 抽取 · 动因 5/6「工具准入/排除判据」「主体=机械件」）:
///   编排决策**不得**停在远端自由文本里 —— 契约面只让远端**声明**候选（可选字段 `action_candidates`），
///   是否成立由本类按 **白名单 + 结构** 机械裁定（零语义判断、零模型自裁判）。
///
/// 同源铁律: 工具白名单直接取 <see cref="ActionToolDecl.Names"/>（声明面/执行面同一事实源），
///   本类**不另立**第二份工具表；契约面渲染出的枚举由 `ActionCandidatesTests` 逐名钉住。
///
/// 轴: env <c>AGENTFRAMEWORK_R1_ACTION_CANDIDATES</c>（缺省 on；off/0/false ⇒ 关）。
///   轴关 ⇒ 管道不解析、台账不出现候选字段 ⇒ 与旧台账**逐字节同**（零回归可机检）。
/// 本轴只落「声明数 / 采纳数 / 拒绝数」三个**机制面**计数；能力面（是否真的少调用、质量是否不降）由后续窗集轮判。
/// </summary>
public static class ActionCandidates
{
    public const string EnvKey = "AGENTFRAMEWORK_R1_ACTION_CANDIDATES";

    /// <summary>轴开关（缺省 on ⇒ 产品缺省即声明的消费面；显式 off ⇒ 旧行为）。</summary>
    public static bool IsEnabled()
    {
        var v = Environment.GetEnvironmentVariable(EnvKey);
        if (string.IsNullOrWhiteSpace(v))
        {
            return true;
        }
        v = v.Trim();
        return !(v.Equals("off", StringComparison.OrdinalIgnoreCase)
                 || v.Equals("0", StringComparison.Ordinal)
                 || v.Equals("false", StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>逐条裁选结果（机制面读数；拒绝原因可机检 ⇒ 不是「跑了 N 条」而是「判定了 N 条」）。</summary>
    public sealed record Selection(
        int Declared,
        int Accepted,
        int Rejected,
        IReadOnlyList<string> AcceptedIds,
        IReadOnlyList<string> RejectReasons,
        // R615：**键到达**（字段存在且为数组，**空数组合法**）——与「声明非空」(Declared>0) 是两个读数。
        //   动因：只在 Declared>0 时落台账 ⇒「模型给了空数组」结构性不可见（arXiv:2608.04355v1 的抽取边界假象）。
        bool Present = false);

    public static readonly Selection Empty =
        new(0, 0, 0, new List<string>(), new List<string>());

    /// <summary>从模型回复正文抽 `action_candidates` 并逐条裁选。非 JSON / 无该字段 ⇒ 声明数 0（不作判据）。</summary>
    public static Selection Select(string? replyText)
    {
        if (string.IsNullOrWhiteSpace(replyText))
        {
            return Empty;
        }
        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(replyText!);
        }
        catch (JsonException)
        {
            return Empty;
        }
        using (doc)
        {
            return Select(doc.RootElement);
        }
    }

    public static Selection Select(JsonElement root)
    {
        if (root.ValueKind != JsonValueKind.Object
            || !root.TryGetProperty("action_candidates", out var arr)
            || arr.ValueKind != JsonValueKind.Array)
        {
            return Empty;
        }
        // R615：走到这里 = 键**到达**（数组形态，含空数组）⇒ Present 与「声明非空」解耦。
        const bool present = true;
        var accepted = new List<string>();
        var reasons = new List<string>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        var declared = 0;
        foreach (var it in arr.EnumerateArray())
        {
            declared++;
            if (it.ValueKind != JsonValueKind.Object)
            {
                reasons.Add("item_not_object");
                continue;
            }
            var id = Str(it, "id");
            var tool = Str(it, "tool");
            var why = Str(it, "why");
            if (string.IsNullOrEmpty(id) || string.IsNullOrEmpty(tool) || string.IsNullOrEmpty(why))
            {
                reasons.Add("missing_field");
                continue;
            }
            if (!ActionToolDecl.IsDeclared(tool))
            {
                reasons.Add("tool_not_declared:" + tool);
                continue;
            }
            if (!seen.Add(id))
            {
                reasons.Add("duplicate_id:" + id);
                continue;
            }
            if (!it.TryGetProperty("args", out var args) || args.ValueKind != JsonValueKind.Object)
            {
                reasons.Add("args_not_object");
                continue;
            }
            if (!ArgsSatisfy(tool, args))
            {
                reasons.Add("args_missing_required:" + tool);
                continue;
            }
            accepted.Add(id);
        }
        return new Selection(declared, accepted.Count, reasons.Count, accepted, reasons, present);
    }

    private static string Str(JsonElement o, string key)
    {
        return o.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.String
            ? (v.GetString() ?? string.Empty)
            : string.Empty;
    }

    /// <summary>
    /// 该工具的必填参数键 —— **由声明面自身的 JSON Schema 派生**（禁另立表）：
    /// 参数规格本来就在 <see cref="ActionToolSpec.ParametersJson"/> 里，抄一份必然漂移。
    /// </summary>
    public static IReadOnlyList<string> RequiredArgsOf(string tool)
    {
        return Required.Value.TryGetValue(tool, out var keys) ? keys : Array.Empty<string>();
    }

    private static readonly Lazy<Dictionary<string, IReadOnlyList<string>>> Required =
        new(BuildRequired, isThreadSafe: true);

    private static Dictionary<string, IReadOnlyList<string>> BuildRequired()
    {
        var map = new Dictionary<string, IReadOnlyList<string>>(StringComparer.Ordinal);
        foreach (var spec in ActionToolSpec.All)
        {
            var keys = new List<string>();
            try
            {
                using var doc = JsonDocument.Parse(spec.ParametersJson);
                if (doc.RootElement.TryGetProperty("required", out var req)
                    && req.ValueKind == JsonValueKind.Array)
                {
                    foreach (var k in req.EnumerateArray())
                    {
                        if (k.ValueKind == JsonValueKind.String)
                        {
                            keys.Add(k.GetString()!);
                        }
                    }
                }
            }
            catch (JsonException)
            {
                // 声明面本身坏 ⇒ 该工具无可达必填键 ⇒ 裁选按「无必填」放行（fail-open 于此**不等于**放行工具：白名单仍生效）
            }
            map[spec.Name] = keys;
        }
        return map;
    }

    private static bool ArgsSatisfy(string tool, JsonElement args)
    {
        foreach (var key in RequiredArgsOf(tool))
        {
            if (!args.TryGetProperty(key, out var v))
            {
                return false;
            }
            if (v.ValueKind == JsonValueKind.String && v.GetString()!.Length == 0)
            {
                return false;
            }
            if (v.ValueKind == JsonValueKind.Null || v.ValueKind == JsonValueKind.Undefined)
            {
                return false;
            }
        }
        return true;
    }
}
