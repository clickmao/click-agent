using System;
using System.Collections.Generic;
using System.Text.Json;
using agent.contract;
using agent.modelqueue;

namespace agent.r1;

/// <summary>
/// R618（RF0004.2 · M3 第二刀）—— **采纳候选 ⇒ 执行面**的机械映射器。
///
/// 动因（Fable 5.1 动因 5/6「工具准入判据」「主体 = 机械件」的下半句）:
///   第一刀已让远端**只做声明**、本地机械裁选；但「执行面读谁」仍是旧的 `plan` ⇒ 编排决策
///   事实上还停在远端自由文本里。本类把**采纳集**搬成执行面节点（窄腰 = `write_file` / `run`），
///   使「执行什么」与「声明什么」同源。
///
/// 铁律（逐条机检）:
///   ① 轴 <c>AGENTFRAMEWORK_R1_ACTION_EXEC</c> **默认 off** ⇒ 轴关时执行面原样读 `plan`，
///      且台账不出现任何新字段 ⇒ 与旧行为**逐字节同**（零回归可机检）。
///   ② **不另立工具表**: 工具名同源于 <see cref="ActionToolDecl"/>；参数键同源于候选 `args` 原文。
///   ③ **不静默丢**: 窄腰装不下的工具（`read_file`/`list_dir`/`delete_file`）与坏参数逐条进
///      <see cref="Mapping.Reasons"/> 并计 <see cref="Mapping.Unmapped"/>（缺项可见 ≠ 0）。
///   ④ 自述期望面（`expect_stdout`）**不另造**：由 `plan` 里 (工具, 参数) 逐字相等的节点**继承**
///      （实测 R617 参考面: `write_file` 118/118 命中、`run_command` 78/83 命中）⇒ 自检面不因换载体而消失；
///      继承数落 <see cref="Mapping.ExpectInherited"/>，使「换载体丢了自检」可机检（而非靠叙述）。
/// </summary>
public static class ActionExecPlan
{
    /// <summary>轴: 缺省 off（未放行的产品分支不动 ⇒ 只有显式开才改行为）。</summary>
    public const string EnvKey = "AGENTFRAMEWORK_R1_ACTION_EXEC";

    public static bool IsEnabled()
    {
        var v = Environment.GetEnvironmentVariable(EnvKey);
        if (string.IsNullOrWhiteSpace(v))
        {
            return false;
        }
        v = v.Trim();
        return v.Equals("1", StringComparison.Ordinal)
               || v.Equals("on", StringComparison.OrdinalIgnoreCase)
               || v.Equals("true", StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>映射结果（计数与原因都可机检 ⇒ 不是「搬了多少条」而是「逐条判定了什么」）。</summary>
    public sealed record Mapping(
        IReadOnlyList<PlanStep> Steps,
        int Unmapped,
        int ExpectInherited,
        IReadOnlyList<string> Reasons);

    public static readonly Mapping Empty =
        new(new List<PlanStep>(), 0, 0, new List<string>());

    /// <summary>
    /// 采纳集 ⇒ 执行面节点。`plan` 只用于**继承自述期望值**（不用于取动作）。
    /// 窄腰之外的声明工具按「无执行面节点」单列（不是失败，也不是静默丢）。
    /// </summary>
    public static Mapping Build(IReadOnlyList<AcceptedAction>? actions, IReadOnlyList<PlanStep>? plan)
    {
        if (actions is null || actions.Count == 0)
        {
            return Empty;
        }
        var steps = new List<PlanStep>();
        var reasons = new List<string>();
        var unmapped = 0;
        var inherited = 0;
        var planList = plan ?? (IReadOnlyList<PlanStep>)Array.Empty<PlanStep>();

        foreach (var a in actions)
        {
            if (string.IsNullOrEmpty(a.Id))
            {
                unmapped++;
                reasons.Add("missing_id");
                continue;
            }
            if (string.IsNullOrEmpty(a.ArgsJson))
            {
                unmapped++;
                reasons.Add("missing_args:" + a.Id);
                continue;
            }

            JsonDocument doc;
            try
            {
                doc = JsonDocument.Parse(a.ArgsJson);
            }
            catch (JsonException)
            {
                unmapped++;
                reasons.Add("args_not_json:" + a.Id);
                continue;
            }

            using (doc)
            {
                var args = doc.RootElement;
                if (args.ValueKind != JsonValueKind.Object)
                {
                    unmapped++;
                    reasons.Add("args_not_object:" + a.Id);
                    continue;
                }

                if (a.Tool == ActionToolDecl.WriteFile)
                {
                    var path = Str(args, "path");
                    if (path.Length == 0
                        || !args.TryGetProperty("content", out var content)
                        || content.ValueKind != JsonValueKind.String)
                    {
                        unmapped++;
                        reasons.Add("write_file_missing_arg:" + a.Id);
                        continue;
                    }
                    var exp = InheritExpect(planList, "write_file", path, string.Empty);
                    if (exp is not null)
                    {
                        inherited++;
                    }
                    steps.Add(new PlanStep(a.Id, "write_file", path, content.GetString() ?? string.Empty,
                        string.Empty, exp ?? string.Empty, Array.Empty<string>()));
                    continue;
                }

                if (a.Tool == ActionToolDecl.RunCommand)
                {
                    var cmd = Str(args, "command");
                    if (cmd.Length == 0)
                    {
                        unmapped++;
                        reasons.Add("run_command_missing_arg:" + a.Id);
                        continue;
                    }
                    var exp = InheritExpect(planList, "run", string.Empty, cmd);
                    if (exp is not null)
                    {
                        inherited++;
                    }
                    steps.Add(new PlanStep(a.Id, "run", string.Empty, string.Empty,
                        cmd, exp ?? string.Empty, Array.Empty<string>()));
                    continue;
                }

                // 窄腰（write_file/run）之外的白名单工具: 本仓 R1 执行面**没有**对应节点
                //   ⇒ 单列，禁静默丢（第三刀 = 信息类工具的「回执走尾部载体」才处理它们）。
                unmapped++;
                reasons.Add("no_exec_face:" + a.Tool);
            }
        }

        return new Mapping(steps, unmapped, inherited, reasons);
    }

    /// <summary>
    /// 自述期望值继承: 工具**与**动作参数逐字相等的 `plan` 节点 ⇒ 取它的 expect_stdout（空则视为无）。
    /// 只读 `plan`，不取动作 ⇒ 「执行什么」仍只来自采纳集。
    /// </summary>
    private static string? InheritExpect(IReadOnlyList<PlanStep> plan, string tool, string path, string cmd)
    {
        foreach (var st in plan)
        {
            if (!string.Equals(st.Tool, tool, StringComparison.Ordinal))
            {
                continue;
            }
            if (tool == "write_file")
            {
                if (string.Equals(st.Path, path, StringComparison.Ordinal) && st.ExpectStdout.Length > 0)
                {
                    return st.ExpectStdout;
                }
            }
            else if (string.Equals(st.Cmd, cmd, StringComparison.Ordinal) && st.ExpectStdout.Length > 0)
            {
                return st.ExpectStdout;
            }
        }
        return null;
    }

    private static string Str(JsonElement o, string key)
    {
        return o.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.String
            ? (v.GetString() ?? string.Empty)
            : string.Empty;
    }
}
