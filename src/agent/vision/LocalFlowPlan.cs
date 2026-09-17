using System;
using System.Collections.Generic;
using System.Text.Json;

namespace agent.vision;

/// <summary>
/// 本地视觉模型返回的**多步骤操作流程**（agent 侧可执行 + 可回放，并把结果反馈给 agent）。
///
/// 形态: {"goal":"...","mode":"short|long","steps":[{"op":...,"target":"...","box_2d":[x1,y1,x2,y2],"text":"...","verify":"..."}],"notes":"..."}
/// 长/短任务: mode=short ⇒ ≤ <see cref="ShortMaxSteps"/> 步、单轮完成; mode=long ⇒ ≤ <see cref="LongMaxSteps"/> 步、
/// 允许中途重新感知（<see cref="NeedsReperception"/> ⇒ agent 回灌新截图后继续）。
/// 解析 fail-closed: 未知 op / 坐标越界 / 缺必填 / 步数超预算 ⇒ null（绝不半信半疑地执行）。
/// </summary>
public sealed record LocalFlowPlan(string Goal, string Mode, IReadOnlyList<LocalFlowStep> Steps, string Notes)
{
    /// <summary>短任务步数上限（单轮可完成）。</summary>
    public const int ShortMaxSteps = 8;

    /// <summary>长任务步数上限（多轮 + 重新感知）。</summary>
    public const int LongMaxSteps = 64;

    /// <summary>box 坐标归一化上界（含）。</summary>
    public const int BoxMax = 1000;

    public static bool IsMode(string? m) => m == "short" || m == "long";

    /// <summary>本流程的步数预算（由 mode 决定）。</summary>
    public int Budget => Mode == "long" ? LongMaxSteps : ShortMaxSteps;

    /// <summary>长任务需要中途重新感知（每 N 步回灌新截图）。</summary>
    public bool NeedsReperception => Mode == "long";

    private static bool TryBox(JsonElement el, out int[] box, out string err)
    {
        box = Array.Empty<int>();
        err = string.Empty;
        if (el.ValueKind != JsonValueKind.Array || el.GetArrayLength() != 4)
        {
            err = "box_2d 必须是长度 4 的整数数组";
            return false;
        }
        var b = new int[4];
        var i = 0;
        foreach (var v in el.EnumerateArray())
        {
            if (v.ValueKind != JsonValueKind.Number || !v.TryGetInt32(out var n))
            {
                err = "box_2d 必须是整数";
                return false;
            }
            if (n < 0 || n > BoxMax)
            {
                err = "box_2d 越界 (须 0.." + BoxMax + ")";
                return false;
            }
            b[i++] = n;
        }
        if (b[0] >= b[2] || b[1] >= b[3])
        {
            err = "box_2d 必须 x1<x2 且 y1<y2";
            return false;
        }
        box = b;
        return true;
    }

    /// <summary>解析并校验（errors 为空 ⇔ 返回值非 null）。</summary>
    public static LocalFlowPlan? TryParse(string? json, out IReadOnlyList<string> errors)
    {
        var errs = new List<string>();
        errors = errs;
        if (string.IsNullOrWhiteSpace(json))
        {
            errs.Add("空响应");
            return null;
        }
        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(json);
        }
        catch (JsonException ex)
        {
            errs.Add("JSON 解析失败: " + ex.Message);
            return null;
        }

        using (doc)
        {
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                errs.Add("顶层必须是 JSON object");
                return null;
            }
            var goal = root.TryGetProperty("goal", out var g) && g.ValueKind == JsonValueKind.String ? g.GetString() : null;
            if (string.IsNullOrWhiteSpace(goal))
            {
                errs.Add("goal 缺失/为空");
            }
            var mode = root.TryGetProperty("mode", out var m) && m.ValueKind == JsonValueKind.String ? m.GetString() : null;
            if (!IsMode(mode))
            {
                errs.Add("mode 缺失/非法 (合法: short|long)");
            }
            var notes = root.TryGetProperty("notes", out var nt) && nt.ValueKind == JsonValueKind.String ? nt.GetString() ?? string.Empty : string.Empty;

            var steps = new List<LocalFlowStep>();
            if (!root.TryGetProperty("steps", out var st) || st.ValueKind != JsonValueKind.Array)
            {
                errs.Add("steps 缺失/类型错");
            }
            else
            {
                var budget = IsMode(mode) ? (mode == "long" ? LongMaxSteps : ShortMaxSteps) : ShortMaxSteps;
                if (st.GetArrayLength() == 0)
                {
                    errs.Add("steps 为空");
                }
                if (st.GetArrayLength() > budget)
                {
                    errs.Add("steps 超预算: " + st.GetArrayLength() + " > " + budget + " (mode=" + mode + ")");
                }
                var i = 0;
                foreach (var s in st.EnumerateArray())
                {
                    if (s.ValueKind != JsonValueKind.Object)
                    {
                        errs.Add("steps[" + i + "] 类型错");
                        i++;
                        continue;
                    }
                    var op = s.TryGetProperty("op", out var o) && o.ValueKind == JsonValueKind.String ? o.GetString() : null;
                    if (!LocalFlowStep.IsOp(op))
                    {
                        errs.Add("steps[" + i + "].op 非法/缺失 (合法: " + string.Join("|", LocalFlowStep.Ops) + ")");
                    }
                    var target = s.TryGetProperty("target", out var t) && t.ValueKind == JsonValueKind.String ? t.GetString() ?? string.Empty : string.Empty;
                    var text = s.TryGetProperty("text", out var tx) && tx.ValueKind == JsonValueKind.String ? tx.GetString() ?? string.Empty : string.Empty;
                    var verify = s.TryGetProperty("verify", out var vf) && vf.ValueKind == JsonValueKind.String ? vf.GetString() ?? string.Empty : string.Empty;

                    var hasBox = s.TryGetProperty("box_2d", out var bx);
                    var box = Array.Empty<int>();
                    if (hasBox)
                    {
                        if (!TryBox(bx, out box, out var berr))
                        {
                            errs.Add("steps[" + i + "].box_2d 非法: " + berr);
                        }
                    }
                    else if (LocalFlowStep.NeedsBox(op))
                    {
                        errs.Add("steps[" + i + "] op=" + op + " 必须带 box_2d");
                    }
                    if (LocalFlowStep.NeedsBox(op) && string.IsNullOrWhiteSpace(target) && !hasBox)
                    {
                        errs.Add("steps[" + i + "] 既无 target 也无 box_2d (无法定位)");
                    }
                    if (op == "type" && string.IsNullOrWhiteSpace(text))
                    {
                        errs.Add("steps[" + i + "] op=type 必须带 text");
                    }
                    if (op == "assert" && string.IsNullOrWhiteSpace(verify))
                    {
                        errs.Add("steps[" + i + "] op=assert 必须带 verify");
                    }
                    steps.Add(new LocalFlowStep(op ?? string.Empty, target, box, text, verify));
                    i++;
                }
            }

            if (errs.Count > 0)
            {
                return null;
            }
            return new LocalFlowPlan(goal!, mode!, steps, notes);
        }
    }
}
