using System.Collections.Generic;
using System.Text.Json;

namespace agent.contract;

/// <summary>
/// R1 结构化契约 —— **单一真源**（抽自 Claude-Fable-5.1 动因⑥）：
/// SchemaText 既渲染进 <output_contract> 段，又驱动本校验器与管道准入闸；禁手工漂移。
/// 零反射：只用 JsonDocument（AOT 安全），全程 fail-closed（无法解析/不合契约 ⇒ 不推进）。
/// </summary>
public static class StructuredContract
{
    public const string SchemaVersion = "r1.0";

    /// <summary>渲染进 prompt 的契约段（与原型 contract.render_schema_text() 逐字节同源）。</summary>
    public const string SchemaText = @"必填字段（缺一即无效）: schema_version, intent, confidence, entities, constraints, missing_slots, ambiguities, plan, done_when, refusal

- schema_version (string == 'r1.0'): 
- intent (string ∈ code_task|question|ops_task|refusal): code_task=要写/改可执行代码并跑验证; question=只要信息; ops_task=对已有环境做操作; refusal=应拒绝
- confidence (number): 0-1; <0.5 应改用 missing_slots/ambiguities 而不是猜
- entities (array；子字段必填: kind, value；子字段取值: kind ∈ path|symbol|command|value|language): 
- constraints (array): 
- missing_slots (array): 推进管道**必需**但请求未给出的信息（不要臆造；没有就空数组）
- ambiguities (array；子字段必填: span, issue, options): 指代不明/多种合理解读的片段。span=原文片段; options=可选项; 非空 ⇒ 管道必须停下要澄清
- plan (array；子字段必填: id, tool, args, depends_on；子字段取值: tool ∈ write_file|run|none): 可执行步骤; tool 仅 write_file|run; args: write_file={path,content} run={cmd,expect_stdout?}; depends_on 引用先前的 id
- done_when (array): 机械可判的完成条件（供外部校验，不是给你的自述）
- refusal (object|null；子字段必填: reason, category): 

互斥规则（违反即无效）: refusal≠null ⇒ plan 必空; 有 missing_slots 或 ambiguities ⇒ plan 必空; intent=code_task ⇒ plan 非空; depends_on 只能引用先前步骤的 id。";

    private static readonly string[] TopRequired =
    {
        "schema_version", "intent", "confidence", "entities", "constraints",
        "missing_slots", "ambiguities", "plan", "done_when", "refusal",
    };

    private static readonly string[] IntentEnum = { "code_task", "question", "ops_task", "refusal" };
    private static readonly string[] ToolEnum = { "write_file", "run", "none" };
    private static readonly string[] EntityKindEnum = { "path", "symbol", "command", "value", "language" };

    private static bool InEnum(string? v, string[] set)
    {
        foreach (var s in set)
        {
            if (s == v)
            {
                return true;
            }
        }
        return false;
    }

    private static bool IsStringArray(JsonElement el)
    {
        if (el.ValueKind != JsonValueKind.Array)
        {
            return false;
        }
        foreach (var it in el.EnumerateArray())
        {
            if (it.ValueKind != JsonValueKind.String)
            {
                return false;
            }
        }
        return true;
    }

    private static void CheckTextArray(List<string> errs, JsonElement root, string key)
    {
        if (!root.TryGetProperty(key, out var el))
        {
            return;
        }
        if (!IsStringArray(el))
        {
            errs.Add(key + " 类型错: 期望 string[]");
        }
    }

    /// <summary>校验（空列表 = 通过）。规则与原型 contract.validate() 一一对应。</summary>
    public static IReadOnlyList<string> Validate(string json)
    {
        var errs = new List<string>();
        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(json);
        }
        catch (JsonException ex)
        {
            errs.Add("JSON 解析失败: " + ex.Message);
            return errs;
        }

        using (doc)
        {
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                errs.Add("顶层必须是 JSON object");
                return errs;
            }

            foreach (var k in TopRequired)
            {
                if (!root.TryGetProperty(k, out _))
                {
                    errs.Add("缺必填字段: " + k);
                }
            }

            if (root.TryGetProperty("schema_version", out var sv) && (sv.ValueKind != JsonValueKind.String || sv.GetString() != SchemaVersion))
            {
                errs.Add("schema_version 常数不符: 期望 " + SchemaVersion);
            }
            if (root.TryGetProperty("intent", out var it) && (it.ValueKind != JsonValueKind.String || !InEnum(it.GetString(), IntentEnum)))
            {
                errs.Add("intent 取值非法");
            }
            if (root.TryGetProperty("confidence", out var cf))
            {
                if (cf.ValueKind != JsonValueKind.Number)
                {
                    errs.Add("confidence 类型错: 期望 number");
                }
                else if (cf.GetDouble() < 0 || cf.GetDouble() > 1)
                {
                    errs.Add("confidence 越界: " + cf.GetDouble());
                }
            }

            CheckTextArray(errs, root, "constraints");
            CheckTextArray(errs, root, "missing_slots");
            CheckTextArray(errs, root, "done_when");

            if (root.TryGetProperty("entities", out var ents))
            {
                if (ents.ValueKind != JsonValueKind.Array)
                {
                    errs.Add("entities 类型错: 期望 array");
                }
                else
                {
                    var i = 0;
                    foreach (var e in ents.EnumerateArray())
                    {
                        if (e.ValueKind != JsonValueKind.Object)
                        {
                            errs.Add("entities[" + i + "] 类型错");
                        }
                        else
                        {
                            if (!e.TryGetProperty("kind", out var kind) || kind.ValueKind != JsonValueKind.String || !InEnum(kind.GetString(), EntityKindEnum))
                            {
                                errs.Add("entities[" + i + "].kind 非法/缺失 (合法: " + string.Join("|", EntityKindEnum) + ")");
                            }
                            if (!e.TryGetProperty("value", out var val) || val.ValueKind != JsonValueKind.String || string.IsNullOrEmpty(val.GetString()))
                            {
                                errs.Add("entities[" + i + "].value 非法/缺失");
                            }
                        }
                        i++;
                    }
                }
            }

            if (root.TryGetProperty("ambiguities", out var ambs))
            {
                if (ambs.ValueKind != JsonValueKind.Array)
                {
                    errs.Add("ambiguities 类型错: 期望 array");
                }
                else
                {
                    var i = 0;
                    foreach (var a in ambs.EnumerateArray())
                    {
                        if (a.ValueKind != JsonValueKind.Object)
                        {
                            errs.Add("ambiguities[" + i + "] 类型错");
                        }
                        else
                        {
                            if (!a.TryGetProperty("span", out var sp) || sp.ValueKind != JsonValueKind.String)
                            {
                                errs.Add("ambiguities[" + i + "] 缺子字段 span");
                            }
                            if (!a.TryGetProperty("issue", out var isu) || isu.ValueKind != JsonValueKind.String)
                            {
                                errs.Add("ambiguities[" + i + "] 缺子字段 issue");
                            }
                            if (!a.TryGetProperty("options", out var op) || !IsStringArray(op))
                            {
                                errs.Add("ambiguities[" + i + "] 缺子字段 options");
                            }
                        }
                        i++;
                    }
                }
            }

            if (root.TryGetProperty("refusal", out var rf) && rf.ValueKind != JsonValueKind.Null)
            {
                if (rf.ValueKind != JsonValueKind.Object)
                {
                    errs.Add("refusal 类型错: 期望 object|null");
                }
                else
                {
                    if (!rf.TryGetProperty("reason", out var r1) || r1.ValueKind != JsonValueKind.String)
                    {
                        errs.Add("refusal 缺子字段 reason");
                    }
                    if (!rf.TryGetProperty("category", out var r2) || r2.ValueKind != JsonValueKind.String)
                    {
                        errs.Add("refusal 缺子字段 category");
                    }
                }
            }

            // plan 结构级语用约束
            var seen = new List<string>();
            var hasPlan = false;
            if (root.TryGetProperty("plan", out var plan) && plan.ValueKind == JsonValueKind.Array)
            {
                var i = 0;
                foreach (var st in plan.EnumerateArray())
                {
                    hasPlan = true;
                    if (st.ValueKind != JsonValueKind.Object)
                    {
                        errs.Add("plan[" + i + "] 类型错");
                        i++;
                        continue;
                    }
                    foreach (var k in new[] { "id", "tool", "args", "depends_on" })
                    {
                        if (!st.TryGetProperty(k, out _))
                        {
                            errs.Add("plan[" + i + "] 缺字段 " + k);
                        }
                    }
                    var tool = st.TryGetProperty("tool", out var tl) && tl.ValueKind == JsonValueKind.String ? tl.GetString() : null;
                    if (!InEnum(tool, ToolEnum))
                    {
                        errs.Add("plan[" + i + "].tool 非法");
                    }
                    if (st.TryGetProperty("args", out var args) && args.ValueKind != JsonValueKind.Object)
                    {
                        errs.Add("plan[" + i + "].args 类型错: 期望 object");
                    }
                    if (tool == "write_file")
                    {
                        var hasPath = args.ValueKind == JsonValueKind.Object && args.TryGetProperty("path", out var p) && p.ValueKind == JsonValueKind.String && !string.IsNullOrEmpty(p.GetString());
                        var hasContent = args.ValueKind == JsonValueKind.Object && args.TryGetProperty("content", out _);
                        if (!hasPath || !hasContent)
                        {
                            errs.Add("plan[" + i + "] write_file 需 args.path 与 args.content");
                        }
                    }
                    if (tool == "run")
                    {
                        var hasCmd = args.ValueKind == JsonValueKind.Object && args.TryGetProperty("cmd", out var c) && c.ValueKind == JsonValueKind.String && !string.IsNullOrEmpty(c.GetString());
                        if (!hasCmd)
                        {
                            errs.Add("plan[" + i + "] run 需 args.cmd");
                        }
                    }
                    if (st.TryGetProperty("depends_on", out var dep) && dep.ValueKind == JsonValueKind.Array)
                    {
                        foreach (var d in dep.EnumerateArray())
                        {
                            var ds = d.ValueKind == JsonValueKind.String ? d.GetString() : null;
                            if (ds is null || !seen.Contains(ds))
                            {
                                errs.Add("plan[" + i + "].depends_on 引用未出现的 id");
                            }
                        }
                    }
                    var id = st.TryGetProperty("id", out var idEl) && idEl.ValueKind == JsonValueKind.String ? idEl.GetString() : null;
                    if (id is not null && seen.Contains(id))
                    {
                        errs.Add("plan id 重复: " + id);
                    }
                    if (id is not null)
                    {
                        seen.Add(id);
                    }
                    i++;
                }
            }

            var intent = root.TryGetProperty("intent", out var it2) && it2.ValueKind == JsonValueKind.String ? it2.GetString() : null;
            if (intent == "code_task" && !hasPlan)
            {
                errs.Add("intent=code_task 但 plan 为空");
            }
            var hasGap = (root.TryGetProperty("missing_slots", out var ms) && ms.ValueKind == JsonValueKind.Array && ms.GetArrayLength() > 0)
                         || (root.TryGetProperty("ambiguities", out var am) && am.ValueKind == JsonValueKind.Array && am.GetArrayLength() > 0);
            if (hasGap && (intent == "code_task" || intent == "ops_task") && hasPlan)
            {
                errs.Add("既有缺失/歧义又给 plan ⇒ 语义冲突（禁猜）");
            }
            if (root.TryGetProperty("refusal", out var rfPin) && rfPin.ValueKind == JsonValueKind.Object && hasPlan)
            {
                errs.Add("refusal≠null 与 plan 非空互斥");
            }
        }

        return errs;
    }

    /// <summary>解析为「精准语义」（校验不过 ⇒ 返回 null，错误经 errors 带出）。</summary>
    public static Semantics? TryParse(string json, out IReadOnlyList<string> errors)
    {
        errors = Validate(json);
        if (errors.Count > 0)
        {
            return null;
        }
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        var entities = new List<Entity>();
        foreach (var e in root.GetProperty("entities").EnumerateArray())
        {
            entities.Add(new Entity(e.GetProperty("kind").GetString() ?? string.Empty, e.GetProperty("value").GetString() ?? string.Empty));
        }
        var ambiguities = new List<Ambiguity>();
        foreach (var a in root.GetProperty("ambiguities").EnumerateArray())
        {
            var opts = new List<string>();
            foreach (var o in a.GetProperty("options").EnumerateArray())
            {
                opts.Add(o.GetString() ?? string.Empty);
            }
            ambiguities.Add(new Ambiguity(a.GetProperty("span").GetString() ?? string.Empty, a.GetProperty("issue").GetString() ?? string.Empty, opts));
        }
        var plan = new List<PlanStep>();
        foreach (var s in root.GetProperty("plan").EnumerateArray())
        {
            var args = s.GetProperty("args");
            var deps = new List<string>();
            foreach (var d in s.GetProperty("depends_on").EnumerateArray())
            {
                deps.Add(d.GetString() ?? string.Empty);
            }
            plan.Add(new PlanStep(
                s.GetProperty("id").GetString() ?? string.Empty,
                s.GetProperty("tool").GetString() ?? string.Empty,
                args.TryGetProperty("path", out var p) ? p.GetString() ?? string.Empty : string.Empty,
                args.TryGetProperty("content", out var c) ? c.GetString() ?? string.Empty : string.Empty,
                args.TryGetProperty("cmd", out var cmd) ? cmd.GetString() ?? string.Empty : string.Empty,
                args.TryGetProperty("expect_stdout", out var ex) ? ex.GetString() ?? string.Empty : string.Empty,
                deps));
        }
        RefusalInfo? refusal = null;
        if (root.TryGetProperty("refusal", out var rf) && rf.ValueKind == JsonValueKind.Object)
        {
            refusal = new RefusalInfo(rf.GetProperty("reason").GetString() ?? string.Empty, rf.GetProperty("category").GetString() ?? string.Empty);
        }
        return new Semantics(
            root.GetProperty("schema_version").GetString() ?? string.Empty,
            root.GetProperty("intent").GetString() ?? string.Empty,
            root.GetProperty("confidence").GetDouble(),
            entities,
            ReadStrings(root, "constraints"),
            ReadStrings(root, "missing_slots"),
            ambiguities,
            plan,
            ReadStrings(root, "done_when"),
            refusal);
    }

    private static IReadOnlyList<string> ReadStrings(JsonElement root, string key)
    {
        var list = new List<string>();
        if (root.TryGetProperty(key, out var el) && el.ValueKind == JsonValueKind.Array)
        {
            foreach (var it in el.EnumerateArray())
            {
                list.Add(it.GetString() ?? string.Empty);
            }
        }
        return list;
    }
}
