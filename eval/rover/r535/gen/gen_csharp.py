#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 /tmp/fable-r1 的 R1 原型（Python）机械搬进仓内 C#（AOT/零反射），
保证 prompt 前缀**逐字节同源**：前缀字面量由 r1prompt.PREFIX 直接生成，长度与 sha 作为钉子写进常量，
测试再回验 —— 任何手工漂移都会红。
"""
import io
import os
import sys

sys.path.insert(0, "/tmp/fable-r1")
import contract
import r1prompt

REPO = "/home/agentuser/AgentFramework"
OUT = os.path.join(REPO, "src/agent/contract")
TESTS = os.path.join(REPO, "src/agent.tests")


def verbatim(s):
    return '@"' + s.replace('"', '""') + '"'


PREFIX_V = verbatim(r1prompt.PREFIX)
SCHEMA_V = verbatim(contract.render_schema_text())
SHA = r1prompt.prefix_sha()
NCHARS = len(r1prompt.PREFIX)


def _enum_fragments(spec):
    """递归收集 schema 里声明的**所有**枚举（含嵌套 kind/tool），渲染形式与 render_schema_text 一致。"""
    out = []
    if isinstance(spec, dict):
        for k, v in (spec.get("properties") or {}).items():
            if isinstance(v, dict) and v.get("enum"):
                out.append("%s ∈ %s" % (k, "|".join(v["enum"])))
            out.extend(_enum_fragments(v))
        out.extend(_enum_fragments(spec.get("items")))
    return sorted(set(out))


ENUM_FRAGS = _enum_fragments(contract.SCHEMA)


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return len(text.encode("utf-8"))


FILES = {}

FILES["Entity.cs"] = """namespace agent.contract;

/// <summary>R1 结构化契约 · 实体项（请求原文里出现的具体路径/符号/命令/取值/语言）。</summary>
public sealed record Entity(string Kind, string Value);
"""

FILES["Ambiguity.cs"] = """using System.Collections.Generic;

namespace agent.contract;

/// <summary>R1 结构化契约 · 歧义项：原文片段 + 问题 + 2-4 个互斥选项。非空 ⇒ 管道必须停下要澄清。</summary>
public sealed record Ambiguity(string Span, string Issue, IReadOnlyList<string> Options);
"""

FILES["PlanStep.cs"] = """using System.Collections.Generic;

namespace agent.contract;

/// <summary>R1 结构化契约 · 计划步骤（DAG 节点）。write_file 用 Path/Content；run 用 Cmd/ExpectStdout。</summary>
public sealed record PlanStep(
    string Id,
    string Tool,
    string Path,
    string Content,
    string Cmd,
    string ExpectStdout,
    IReadOnlyList<string> DependsOn);
"""

FILES["RefusalInfo.cs"] = """namespace agent.contract;

/// <summary>R1 结构化契约 · 拒答信息（硬闸命中时唯一允许的推进方式）。</summary>
public sealed record RefusalInfo(string Reason, string Category);
"""

FILES["Semantics.cs"] = """using System.Collections.Generic;

namespace agent.contract;

/// <summary>R1 「精准语义」：下游管道**直接消费**的字段集合（唯一真源 = StructuredContract）。</summary>
public sealed record Semantics(
    string SchemaVersion,
    string Intent,
    double Confidence,
    IReadOnlyList<Entity> Entities,
    IReadOnlyList<string> Constraints,
    IReadOnlyList<string> MissingSlots,
    IReadOnlyList<Ambiguity> Ambiguities,
    IReadOnlyList<PlanStep> Plan,
    IReadOnlyList<string> DoneWhen,
    RefusalInfo? Refusal);
"""

FILES["PipelineOutcome.cs"] = """namespace agent.contract;

/// <summary>R1 管道判定：rc 编码分支（0=可推进/无需执行, 2=缺信息要澄清, 3=硬闸拒答, 4=计划非法, 5=执行未达期望）。</summary>
public sealed record PipelineOutcome(int Rc, string Stage, string Reason, bool Halted);
"""

FILES["StructuredPrompt.cs"] = """using System.Security.Cryptography;
using System.Text;

namespace agent.contract;

/// <summary>
/// R1 结构化 prompt —— 抽自 Claude-Fable-5.1 泄露 system 的设计动因（见 docs/reports/fable51-design-rationale.md）。
///
/// 铁律（R1-①）：本常量前缀**逐字节恒定** —— 无日期、无用户态、无会话材料；
/// 随调用变化的一切只出现在 user 轮（BuildUserMessage）。
/// 前缀字面量由原型机械生成，PrefixChars / PrefixSha256Pinned 是钉子：手工改字必被 StructuredContractTests 判红。
/// </summary>
public static class StructuredPrompt
{
    public const string Version = "r1.0";

    /// <summary>前缀字符数钉子（与原型 /tmp/fable-r1/r1prompt.py 同源）。</summary>
    public const int PrefixChars = __NCHARS__;

    /// <summary>前缀 UTF-8 sha256 钉子（小写 hex）。</summary>
    public const string PrefixSha256Pinned = "__SHA__";

    public const string Prefix = __PREFIX__;

    public static string PrefixSha256()
    {
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(Prefix));
        var sb = new StringBuilder(64);
        foreach (var b in bytes)
        {
            sb.Append(b.ToString("x2"));
        }
        return sb.ToString();
    }

    /// <summary>user 轮 = 尾部易变块（任务正文 + 可选修复指令）。前缀不动。</summary>
    public static string BuildUserMessage(string taskText, string? repairNote = null)
    {
        var user = "<task>\\n" + (taskText ?? string.Empty).Trim() + "\\n</task>";
        if (!string.IsNullOrEmpty(repairNote))
        {
            user += "\\n\\n<repair>\\n" + repairNote + "\\n</repair>";
        }
        return user;
    }

    /// <summary>修复环指令（契约不过时注入；与原型 contract.repair_message 同义）。</summary>
    public static string RepairMessage(System.Collections.Generic.IReadOnlyList<string> errors)
    {
        var sb = new StringBuilder();
        sb.Append("上一次输出未通过契约校验，逐条修正后**只输出**修正后的 JSON（不要解释、不要 markdown 围栏）：");
        foreach (var e in errors)
        {
            sb.Append("\\n- ").Append(e);
        }
        return sb.ToString();
    }

    /// <summary>
    /// 执行证据回灌 (R533): 计划步骤**已真实执行**但实测与期望不符时的修复指令。
    /// 与 <see cref="RepairMessage"/> 的区别: 那里是**契约**不过 (结构错), 这里是**真跑证据**不过 (行为错) ——
    /// 证据一律取自执行器实测 (rc/stdout/stderr), 禁模型自述; 并明令不得改写期望值来迁就现状。
    /// </summary>
    public static string ExecRepairMessage(System.Collections.Generic.IReadOnlyList<string> evidence)
    {
        var sb = new StringBuilder();
        sb.Append("[exec_repair] 上一次计划的步骤已真实执行，实测结果与期望不符。依据下列**实测证据**修正，"
            + "只输出修正后的 JSON（不要解释、不要 markdown 围栏）：不得删除验收步骤，"
            + "不得改写期望值来迁就现状，不得用自然语言宣称完成。");
        foreach (var e in evidence)
        {
            sb.Append("\\n- ").Append(e);
        }
        return sb.ToString();
    }
}
""".replace("__NCHARS__", str(NCHARS)).replace("__SHA__", SHA).replace("__PREFIX__", PREFIX_V)

FILES["StructuredContract.cs"] = """using System.Collections.Generic;
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
    public const string SchemaText = __SCHEMA__;

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
""".replace("__SCHEMA__", SCHEMA_V)

FILES["SemanticsPipeline.cs"] = """using System.Collections.Generic;
using System.IO;

namespace agent.contract;

/// <summary>
/// R1 管道准入闸（抽自 Claude-Fable-5.1 动因②「安全在每个能力边界再断言」）。
/// 闸序固定、fail-closed：硬闸 → 语义完整 → 非执行类 → 计划合法性 → 可执行。
/// 判定写在 Stage/Rc 上，不靠 grep 锚。
/// </summary>
public static class SemanticsPipeline
{
    private static readonly string[] Banned =
    {
        "sudo", "rm -rf /", "curl ", "wget ", "pip install", "apt-get", "git push",
        "chmod 777", "mkfs", "dd if=",
    };

    public static PipelineOutcome Gate(Semantics sem, string sandboxRoot)
    {
        if (sem.Refusal is not null)
        {
            return new PipelineOutcome(3, "hard_gate", "模型判定应拒答: " + sem.Refusal.Reason, true);
        }
        if (sem.MissingSlots.Count > 0 || sem.Ambiguities.Count > 0)
        {
            return new PipelineOutcome(2, "semantics_incomplete", "缺信息/有歧义 ⇒ 停下澄清", true);
        }
        if (sem.Intent != "code_task" && sem.Intent != "ops_task")
        {
            return new PipelineOutcome(0, "non_exec", "intent=" + sem.Intent + " 无需执行（信息类）", false);
        }

        var seen = new List<string>();
        foreach (var st in sem.Plan)
        {
            if (st.Tool != "write_file" && st.Tool != "run" && st.Tool != "none")
            {
                return new PipelineOutcome(4, "plan", "非白名单工具: " + st.Tool, true);
            }
            foreach (var d in st.DependsOn)
            {
                if (!seen.Contains(d))
                {
                    return new PipelineOutcome(4, "plan", "depends_on 引用不存在/后置: " + d + " (step " + st.Id + ")", true);
                }
            }
            if (st.Tool == "write_file")
            {
                var scope = ScopeError(st.Path, sandboxRoot);
                if (scope is not null)
                {
                    return new PipelineOutcome(4, "scope", scope, true);
                }
            }
            if (st.Tool == "run")
            {
                foreach (var b in Banned)
                {
                    if (st.Cmd.Contains(b, System.StringComparison.Ordinal))
                    {
                        return new PipelineOutcome(4, "plan", "命令含禁用片段 " + b, true);
                    }
                }
            }
            seen.Add(st.Id);
        }
        return new PipelineOutcome(0, "ready", "计划合法，可执行", false);
    }

    private static string? ScopeError(string path, string sandboxRoot)
    {
        if (string.IsNullOrEmpty(path))
        {
            return "空路径";
        }
        if (Path.IsPathRooted(path))
        {
            return "拒绝绝对路径: " + path;
        }
        var full = Path.GetFullPath(Path.Combine(sandboxRoot, path));
        var root = Path.GetFullPath(sandboxRoot);
        var sep = Path.DirectorySeparatorChar;
        if (full != root && !full.StartsWith(root + sep, System.StringComparison.Ordinal))
        {
            return "路径逃出沙箱: " + path;
        }
        return null;
    }
}
"""

TESTS_SRC = """using System;
using System.Collections.Generic;
using System.IO;
using agent.contract;
using Xunit;

namespace agent.tests;

/// <summary>
/// R1 结构化契约 / prompt / 管道闸的守卫测试。
/// 作用面：把「前缀逐字节恒定 + 契约与校验器同源 + 闸序 fail-closed」变成可机检的不变式，
/// 任何手工漂移（改前缀文字、改 schema 只改一边、放松闸）都会红。
/// </summary>
public sealed class StructuredContractTests
{
    private const string Kadane = "{\\"schema_version\\":\\"r1.0\\",\\"intent\\":\\"code_task\\",\\"confidence\\":0.9,"
        + "\\"entities\\":[{\\"kind\\":\\"path\\",\\"value\\":\\"sols/kadane.py\\"}],\\"constraints\\":[\\"只用标准库\\"],"
        + "\\"missing_slots\\":[],\\"ambiguities\\":[],\\"done_when\\":[\\"s2 的 stdout == 6\\"],\\"refusal\\":null,"
        + "\\"plan\\":[{\\"id\\":\\"s1\\",\\"tool\\":\\"write_file\\",\\"args\\":{\\"path\\":\\"sols/kadane.py\\",\\"content\\":\\"print(1)\\"},\\"depends_on\\":[]},"
        + "{\\"id\\":\\"s2\\",\\"tool\\":\\"run\\",\\"args\\":{\\"cmd\\":\\"echo 6 | python3 sols/kadane.py\\",\\"expect_stdout\\":\\"6\\"},\\"depends_on\\":[\\"s1\\"]}]}";

    private const string Ambiguous = "{\\"schema_version\\":\\"r1.0\\",\\"intent\\":\\"question\\",\\"confidence\\":0.85,\\"entities\\":[],"
        + "\\"constraints\\":[],\\"missing_slots\\":[\\"缺指代对象\\"],\\"ambiguities\\":[{\\"span\\":\\"把它改好\\",\\"issue\\":\\"指代不明\\",\\"options\\":[\\"上一个产物\\",\\"仓内文件\\"]}],"
        + "\\"plan\\":[],\\"done_when\\":[],\\"refusal\\":null}";

    private static Semantics Parse(string json)
    {
        var sem = StructuredContract.TryParse(json, out var errs);
        Assert.True(errs.Count == 0, string.Join(" | ", errs));
        Assert.NotNull(sem);
        return sem!;
    }

    [Fact]
    public void Prefix_Is_ByteStable_And_Pinned()
    {
        Assert.Equal(StructuredPrompt.PrefixChars, StructuredPrompt.Prefix.Length);
        Assert.Equal(StructuredPrompt.PrefixSha256Pinned, StructuredPrompt.PrefixSha256());
        Assert.Equal(StructuredContract.SchemaVersion, StructuredPrompt.Version);
    }

    [Fact]
    public void Prefix_Blocks_Appear_In_Fixed_Order()
    {
        string[] blocks = { "<role>", "<output_contract>", "<hard_gates>", "<semantics_dictionary>", "<tool_menu>", "<environment>", "<examples>" };
        var last = -1;
        foreach (var b in blocks)
        {
            var idx = StructuredPrompt.Prefix.IndexOf(b, StringComparison.Ordinal);
            Assert.True(idx > last, "块序错: " + b);
            last = idx;
        }
    }

    [Fact]
    public void Prefix_Carries_No_Volatile_Facts()
    {
        // 动因①：前缀里不得出现日期/会话材料 —— 这是前缀缓存能命中的前提。
        Assert.DoesNotContain("current date", StructuredPrompt.Prefix, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("2026", StructuredPrompt.Prefix, StringComparison.Ordinal);
        Assert.DoesNotContain("data/activity", StructuredPrompt.Prefix, StringComparison.Ordinal);
    }

    [Fact]
    public void Contract_And_Prompt_Are_Same_Source()
    {
        // 动因⑥：schema 一处定义 ⇒ 渲染进 prompt 的那段必须逐字出现在前缀里。
        Assert.Contains(StructuredContract.SchemaText, StructuredPrompt.Prefix, StringComparison.Ordinal);
        Assert.Contains("refusal", StructuredContract.SchemaText, StringComparison.Ordinal);
    }

    [Fact]
    public void Contract_Renders_Every_Enum_Declared_In_Schema()
    {
        // R535 缺陷回归闸（动因⑥的**渲染方向**）：schema 声明的每个 enum（含嵌套 entities[].kind 与 plan[].tool）
        // 必须逐字渲染进契约段与前缀 —— 否则模型只能自造取值（R535 实测抓到 kind="expected_stdout"），
        // 而校验器按 enum 杀 ⇒ 契约与校验器不同源、管道 fail-closed 空转。
        // 下面是**机械生成**的枚举片段表（gen_csharp.py 从 SCHEMA 递归抽, 禁手工维护）。
        foreach (var frag in new[] { __ENUM_FRAGS__ })
        {
            Assert.Contains(frag, StructuredContract.SchemaText, StringComparison.Ordinal);
            Assert.Contains(frag, StructuredPrompt.Prefix, StringComparison.Ordinal);
        }

        // 负控：把片段从契约段里抹掉 ⇒ 上面那条断言必红（证明断言不是空转）。
        var mutated = StructuredContract.SchemaText.Replace("kind ∈ path|symbol|command|value|language", string.Empty, StringComparison.Ordinal);
        Assert.DoesNotContain("kind ∈ path|symbol|command|value|language", mutated, StringComparison.Ordinal);
    }

    [Fact]
    public void Validate_Accepts_Real_Kadane_Shape()
    {
        Assert.Empty(StructuredContract.Validate(Kadane));
        var sem = Parse(Kadane);
        Assert.Equal("code_task", sem.Intent);
        Assert.Equal(2, sem.Plan.Count);
        Assert.Equal("s1", sem.Plan[0].Id);
        Assert.Equal("print(1)", sem.Plan[0].Content);
        Assert.Equal("6", sem.Plan[1].ExpectStdout);
    }

    [Fact]
    public void Validate_Turns_Red_On_Negatives()
    {
        // ①置信越界 + plan 空
        Assert.NotEmpty(StructuredContract.Validate("{\\"schema_version\\":\\"r1.0\\",\\"intent\\":\\"code_task\\",\\"confidence\\":1.2,"
            + "\\"entities\\":[],\\"constraints\\":[],\\"missing_slots\\":[],\\"ambiguities\\":[],\\"plan\\":[],\\"done_when\\":[],\\"refusal\\":null}"));
        // ②悬空依赖
        Assert.NotEmpty(StructuredContract.Validate("{\\"schema_version\\":\\"r1.0\\",\\"intent\\":\\"code_task\\",\\"confidence\\":0.9,"
            + "\\"entities\\":[],\\"constraints\\":[],\\"missing_slots\\":[],\\"ambiguities\\":[],\\"done_when\\":[],\\"refusal\\":null,"
            + "\\"plan\\":[{\\"id\\":\\"s1\\",\\"tool\\":\\"write_file\\",\\"args\\":{\\"path\\":\\"a.py\\",\\"content\\":\\"x\\"},\\"depends_on\\":[\\"s9\\"]}]}"));
        // ③refusal 缺子字段 category（原型曾放行的同源漂移）
        Assert.NotEmpty(StructuredContract.Validate("{\\"schema_version\\":\\"r1.0\\",\\"intent\\":\\"refusal\\",\\"confidence\\":0.9,"
            + "\\"entities\\":[],\\"constraints\\":[],\\"missing_slots\\":[],\\"ambiguities\\":[],\\"plan\\":[],\\"done_when\\":[],"
            + "\\"refusal\\":{\\"reason\\":\\"凭据外传\\"}}"));
        // ④既有缺失又给 plan ⇒ 语义冲突
        Assert.NotEmpty(StructuredContract.Validate("{\\"schema_version\\":\\"r1.0\\",\\"intent\\":\\"code_task\\",\\"confidence\\":0.9,"
            + "\\"entities\\":[],\\"constraints\\":[],\\"missing_slots\\":[\\"缺路径\\"],\\"ambiguities\\":[],\\"done_when\\":[],\\"refusal\\":null,"
            + "\\"plan\\":[{\\"id\\":\\"s1\\",\\"tool\\":\\"run\\",\\"args\\":{\\"cmd\\":\\"echo hi\\"},\\"depends_on\\":[]}]}"));
        // ⑤非法 JSON
        Assert.NotEmpty(StructuredContract.Validate("not json"));
        // ⑥refusal + plan 非空
        Assert.NotEmpty(StructuredContract.Validate("{\\"schema_version\\":\\"r1.0\\",\\"intent\\":\\"refusal\\",\\"confidence\\":0.9,"
            + "\\"entities\\":[],\\"constraints\\":[],\\"missing_slots\\":[],\\"ambiguities\\":[],\\"done_when\\":[],"
            + "\\"refusal\\":{\\"reason\\":\\"x\\",\\"category\\":\\"y\\"},"
            + "\\"plan\\":[{\\"id\\":\\"s1\\",\\"tool\\":\\"run\\",\\"args\\":{\\"cmd\\":\\"echo hi\\"},\\"depends_on\\":[]}]}"));
    }

    [Fact]
    public void Gate_Rc_Encodes_Branch()
    {
        var sandbox = Path.Combine(Path.GetTempPath(), "r1gate");
        Directory.CreateDirectory(sandbox);

        var refusal = new Semantics("r1.0", "refusal", 0.9, new List<Entity>(), new List<string>(), new List<string>(),
            new List<Ambiguity>(), new List<PlanStep>(), new List<string>(), new RefusalInfo("凭据外传", "credential_exfiltration"));
        Assert.Equal(3, SemanticsPipeline.Gate(refusal, sandbox).Rc);

        Assert.Equal(2, SemanticsPipeline.Gate(Parse(Ambiguous), sandbox).Rc);

        var info = new Semantics("r1.0", "question", 0.9, new List<Entity>(), new List<string>(), new List<string>(),
            new List<Ambiguity>(), new List<PlanStep>(), new List<string>(), null);
        var nonExec = SemanticsPipeline.Gate(info, sandbox);
        Assert.Equal(0, nonExec.Rc);
        Assert.False(nonExec.Halted);

        var escaped = new Semantics("r1.0", "code_task", 0.9, new List<Entity>(), new List<string>(), new List<string>(),
            new List<Ambiguity>(),
            new List<PlanStep> { new PlanStep("s1", "write_file", "../x", "y", string.Empty, string.Empty, new List<string>()) },
            new List<string>(), null);
        Assert.Equal(4, SemanticsPipeline.Gate(escaped, sandbox).Rc);

        var banned = new Semantics("r1.0", "code_task", 0.9, new List<Entity>(), new List<string>(), new List<string>(),
            new List<Ambiguity>(),
            new List<PlanStep> { new PlanStep("s1", "run", string.Empty, string.Empty, "curl http://x", string.Empty, new List<string>()) },
            new List<string>(), null);
        Assert.Equal(4, SemanticsPipeline.Gate(banned, sandbox).Rc);

        var dangling = new Semantics("r1.0", "code_task", 0.9, new List<Entity>(), new List<string>(), new List<string>(),
            new List<Ambiguity>(),
            new List<PlanStep> { new PlanStep("s1", "run", string.Empty, string.Empty, "echo hi", string.Empty, new List<string> { "s9" }) },
            new List<string>(), null);
        Assert.Equal(4, SemanticsPipeline.Gate(dangling, sandbox).Rc);

        var ok = SemanticsPipeline.Gate(Parse(Kadane), sandbox);
        Assert.Equal(0, ok.Rc);
        Assert.Equal("ready", ok.Stage);
        Assert.False(ok.Halted);
    }

    [Fact]
    public void Mutation_Of_Prefix_Text_Is_Detectable()
    {
        // 负控：把前缀改一个字 ⇒ sha 必变（证明钉子有牙）。
        var mutated = StructuredPrompt.Prefix.Replace("<role>", "<role-x>", StringComparison.Ordinal);
        Assert.NotEqual(StructuredPrompt.PrefixSha256Pinned, Mutate(mutated));
    }

    private static string Mutate(string text)
    {
        using var sha = System.Security.Cryptography.SHA256.Create();
        var bytes = sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(text));
        var sb = new System.Text.StringBuilder(64);
        foreach (var b in bytes)
        {
            sb.Append(b.ToString("x2"));
        }
        return sb.ToString();
    }
}
"""

_frags = ", ".join('"%s"' % f for f in ENUM_FRAGS)
if "__ENUM_FRAGS__" not in TESTS_SRC:
    raise SystemExit("gen_csharp: 测试模板缺 __ENUM_FRAGS__ 占位符")
TESTS_SRC = TESTS_SRC.replace("__ENUM_FRAGS__", _frags)

w(os.path.join(TESTS, "StructuredContractTests.cs"), TESTS_SRC)
print("tests ->", os.path.join(TESTS, "StructuredContractTests.cs"))

total = 0
for name, text in FILES.items():
    if text is None:
        continue
    total += w(os.path.join(OUT, name), text)
print("生成 %d 文件, %d bytes -> %s" % (len(FILES), total, OUT))
print("prefix chars=%d sha=%s" % (NCHARS, SHA))
