using System.IO;
using System.Text;

namespace agent.r1;

/// <summary>
/// R1 管道 · 落盘台账（机读 JSON；写侧 UTF8 无 BOM）。
/// 与 R1Json 同源手写 ⇒ AOT 下无反射序列化依赖。
/// stdout 另打一行 R1_STATS 标记：不依赖文件即可取读数（文件路径可用则同时落盘）。
/// </summary>
public static class R1Transcript
{
    public const string Schema = "r1-run/1";

    public static string Marker(R1RunResult r)
    {
        var sb = new StringBuilder("R1_STATS {");
        sb.Append("\"schema\":").Append(R1Json.Quote(Schema));
        sb.Append(",\"rc\":").Append(R1Json.Num(r.Rc));
        sb.Append(",\"stage\":").Append(R1Json.Quote(r.Stage));
        sb.Append(",\"calls\":").Append(R1Json.Num(r.Stats.Calls));
        sb.Append(",\"prompt_tokens\":").Append(R1Json.Num(r.Stats.PromptTokens));
        sb.Append(",\"completion_tokens\":").Append(R1Json.Num(r.Stats.CompletionTokens));
        sb.Append(",\"cache_hit_tokens\":").Append(R1Json.NumOrNull(r.Stats.CacheHitTokens));
        sb.Append(",\"cache_miss_tokens\":").Append(R1Json.NumOrNull(r.Stats.CacheMissTokens));
        sb.Append(",\"repair_rounds\":").Append(R1Json.Num(r.Stats.RepairRounds));
        sb.Append(",\"exec_repairs\":").Append(R1Json.Num(r.Stats.ExecRepairs));
        sb.Append(",\"prefix_chars\":").Append(R1Json.Num(r.PrefixChars));
        sb.Append(",\"prefix_sha256\":").Append(R1Json.Quote(r.PrefixSha256));
        sb.Append(",\"task_sha256\":").Append(R1Json.Quote(r.TaskSha256));
        sb.Append(",\"steps\":").Append(R1Json.Num(r.Steps.Count));
        sb.Append(",\"plan_steps_total\":").Append(R1Json.Num(r.Semantics is null ? 0 : r.Semantics.Plan.Count));
        sb.Append(",\"steps_executed\":").Append(R1Json.Num(r.Steps.Count));
        // R536: 自测期望未达成 ⇒ 独立可机读字段（不靠 rc 数字猜）；管道在首个不符处停机 ⇒ ≤1。
        sb.Append(",\"self_test_unmet\":").Append(R1Json.Num(SelfTestUnmet(r)));
        // R539: 成对报的机检锚 —— **只有 rc=0 才断言产物正确**；rc=8「自测未达成」与产物可疑成对出现，
        //   禁止把 rc=8 当正确性证据（判分器只吃这个字段与外部用例，不吃 rc 等值）。
        sb.Append(",\"correctness_asserted\":").Append(R1Json.Num(CorrectnessAsserted(r)));
        sb.Append(",\"role_note_chars\":").Append(R1Json.Num(r.RoleNoteChars));
        // R544: 产物侧公开用例回放（关闭/抽不出时不出现这两个字段 ⇒ 与旧台账逐字节同）。
        // R545: 加 reason 与 trigger_rc —— reason 让「没跑」的**原因**可机检（no_artifacts_on_disk 等），
        //   trigger_rc 让「触发面已覆盖 rc≠0 的产物在盘出口」可机检（ran=1 ∧ trigger_rc=5）。
        if (r.Probe is not null)
        {
            sb.Append(",\"public_probe_ran\":").Append(R1Json.Num(r.Probe.Ran ? 1 : 0));
            sb.Append(",\"public_probe_reason\":").Append(R1Json.Quote(r.Probe.Reason));
            sb.Append(",\"public_probe_total\":").Append(R1Json.Num(r.Probe.Total));
            sb.Append(",\"public_probe_failed\":").Append(R1Json.Num(r.Probe.Failed));
            sb.Append(",\"public_probe_trigger_rc\":").Append(R1Json.Num(r.Probe.TriggerRc));
        }
        // R546 早停轴：轴关(0) ⇒ 这两个字段不出现 ⇒ 与旧台账逐字节同（零回归由字段缺席机检）。
        if (r.EarlyStopThreshold > 0)
        {
            sb.Append(",\"early_stop_pfail\":").Append(R1Json.Num(r.EarlyStopThreshold));
            sb.Append(",\"early_stop_skipped\":").Append(R1Json.Num(r.EarlyStopSkipped));
        }
        // R550 探针修复独立预算轴：轴关 ⇒ ProbeRepairs 恒 0 ⇒ 字段不出现（与旧标记逐字节同）。
        //   标记面（stdout）不带 opt ⇒ 只在**实际用过**探针修复轮时出现；预算本身在 Render 面可见。
        if (r.ProbeRepairs > 0)
        {
            sb.Append(",\"probe_repairs\":").Append(R1Json.Num(r.ProbeRepairs));
        }
        // R600 修复环「带现状」轴：轴关 ⇒ 恒 0 ⇒ 字段不出现（与旧标记逐字节同）。
        if (r.ArtifactCarryoverRounds > 0)
        {
            sb.Append(",\"artifact_carryover_rounds\":").Append(R1Json.Num(r.ArtifactCarryoverRounds));
            sb.Append(",\"artifact_carryover_chars\":").Append(R1Json.Num(r.ArtifactCarryoverChars));
        }
        // R610 动作候选轴（AGENTFRAMEWORK_R1_ACTION_CANDIDATES，默认开）：声明数 0（含轴关）⇒
        //   三字段不出现 ⇒ 与旧标记逐字节同（零回归由字段缺席机检；R546/R550/R600 同一纪律）。
        if (r.ActionCandidatesDeclared > 0)
        {
            sb.Append(",\"action_candidates_declared\":").Append(R1Json.Num(r.ActionCandidatesDeclared));
            sb.Append(",\"action_candidates_accepted\":").Append(R1Json.Num(r.ActionCandidatesAccepted));
            sb.Append(",\"action_candidates_rejected\":").Append(R1Json.Num(r.ActionCandidatesRejected));
        }
        sb.Append("}");
        return sb.ToString();
    }

    public static string Render(R1RunResult r, R1Options opt, string taskText)
    {
        var sb = new StringBuilder(2048);
        sb.Append("{\n");
        sb.Append("  \"schema\": ").Append(R1Json.Quote(Schema)).Append(",\n");
        sb.Append("  \"tag\": ").Append(R1Json.Quote(opt.Tag)).Append(",\n");
        sb.Append("  \"sandbox\": ").Append(R1Json.Quote(opt.SandboxRoot)).Append(",\n");
        sb.Append("  \"task_sha256\": ").Append(R1Json.Quote(r.TaskSha256)).Append(",\n");
        sb.Append("  \"task_chars\": ").Append(R1Json.Num((taskText ?? string.Empty).Length)).Append(",\n");
        sb.Append("  \"prefix_chars\": ").Append(R1Json.Num(r.PrefixChars)).Append(",\n");
        sb.Append("  \"prefix_sha256\": ").Append(R1Json.Quote(r.PrefixSha256)).Append(",\n");
        sb.Append("  \"prefix_pinned\": ").Append(r.PrefixSha256 == agent.contract.StructuredPrompt.PrefixSha256Pinned ? "true" : "false").Append(",\n");
        sb.Append("  \"role_note_chars\": ").Append(R1Json.Num(r.RoleNoteChars)).Append(",\n");
        sb.Append("  \"max_repair\": ").Append(R1Json.Num(opt.MaxRepair)).Append(",\n");
        sb.Append("  \"max_exec_repair\": ").Append(R1Json.Num(opt.MaxExecRepair)).Append(",\n");
        if (r.EarlyStopThreshold > 0)
        {
            sb.Append("  \"early_stop_pfail\": ").Append(R1Json.Num(r.EarlyStopThreshold)).Append(",\n");
            sb.Append("  \"early_stop_skipped\": ").Append(R1Json.Num(r.EarlyStopSkipped)).Append(",\n");
        }
        if (opt.MaxProbeRepair > 0)
        {
            sb.Append("  \"probe_repair_budget\": ").Append(R1Json.Num(opt.MaxProbeRepair)).Append(",\n");
            sb.Append("  \"probe_repairs\": ").Append(R1Json.Num(r.ProbeRepairs)).Append(",\n");
        }
        // R600 修复环「带现状」轴：轴关且未用过 ⇒ 字段不出现 ⇒ 与旧台账逐字节同（零回归可机检）。
        if (r.ArtifactCarryoverRounds > 0 || opt.ArtifactCarryoverEnabled)
        {
            sb.Append("  \"artifact_carryover_enabled\": ").Append(opt.ArtifactCarryoverEnabled ? "1" : "0").Append(",\n");
            sb.Append("  \"artifact_carryover_rounds\": ").Append(R1Json.Num(r.ArtifactCarryoverRounds)).Append(",\n");
            sb.Append("  \"artifact_carryover_chars\": ").Append(R1Json.Num(r.ArtifactCarryoverChars)).Append(",\n");
        }
        // R610 动作候选轴：声明数 0（含轴关）⇒ 字段不出现 ⇒ 与旧台账逐字节同。
        if (r.ActionCandidatesDeclared > 0)
        {
            sb.Append("  \"action_candidates_declared\": ").Append(R1Json.Num(r.ActionCandidatesDeclared)).Append(",\n");
            sb.Append("  \"action_candidates_accepted\": ").Append(R1Json.Num(r.ActionCandidatesAccepted)).Append(",\n");
            sb.Append("  \"action_candidates_rejected\": ").Append(R1Json.Num(r.ActionCandidatesRejected)).Append(",\n");
        }
        sb.Append("  \"step_timeout_s\": ").Append(R1Json.Num(opt.StepTimeoutSeconds)).Append(",\n");
        sb.Append("  \"rc\": ").Append(R1Json.Num(r.Rc)).Append(",\n");
        sb.Append("  \"stage\": ").Append(R1Json.Quote(r.Stage)).Append(",\n");
        sb.Append("  \"reason\": ").Append(R1Json.Quote(r.Reason)).Append(",\n");
        sb.Append("  \"calls\": ").Append(R1Json.Num(r.Stats.Calls)).Append(",\n");
        sb.Append("  \"prompt_tokens\": ").Append(R1Json.Num(r.Stats.PromptTokens)).Append(",\n");
        sb.Append("  \"completion_tokens\": ").Append(R1Json.Num(r.Stats.CompletionTokens)).Append(",\n");
        sb.Append("  \"cache_hit_tokens\": ").Append(R1Json.NumOrNull(r.Stats.CacheHitTokens)).Append(",\n");
        sb.Append("  \"cache_miss_tokens\": ").Append(R1Json.NumOrNull(r.Stats.CacheMissTokens)).Append(",\n");
        sb.Append("  \"repair_rounds\": ").Append(R1Json.Num(r.Stats.RepairRounds)).Append(",\n");
        sb.Append("  \"exec_repairs\": ").Append(R1Json.Num(r.Stats.ExecRepairs)).Append(",\n");
        sb.Append("  \"plan_steps_total\": ").Append(R1Json.Num(r.Semantics is null ? 0 : r.Semantics.Plan.Count)).Append(",\n");
        sb.Append("  \"steps_executed\": ").Append(R1Json.Num(r.Steps.Count)).Append(",\n");
        sb.Append("  \"self_test_unmet\": ").Append(R1Json.Num(SelfTestUnmet(r))).Append(",\n");
        sb.Append("  \"correctness_asserted\": ").Append(R1Json.Num(CorrectnessAsserted(r))).Append(",\n");
        sb.Append("  \"public_probe_ran\": ").Append(r.Probe is null ? "null" : R1Json.Num(r.Probe.Ran ? 1 : 0)).Append(",\n");
        sb.Append("  \"public_probe_reason\": ").Append(r.Probe is null ? "null" : R1Json.Quote(r.Probe.Reason)).Append(",\n");
        sb.Append("  \"public_probe_total\": ").Append(r.Probe is null ? "null" : R1Json.Num(r.Probe.Total)).Append(",\n");
        sb.Append("  \"public_probe_failed\": ").Append(r.Probe is null ? "null" : R1Json.Num(r.Probe.Failed)).Append(",\n");
        sb.Append("  \"public_probe_trigger_rc\": ").Append(r.Probe is null ? "null" : R1Json.Num(r.Probe.TriggerRc)).Append(",\n");

        var sem = r.Semantics;
        sb.Append("  \"semantics\": ");
        if (sem is null)
        {
            sb.Append("null,\n");
        }
        else
        {
            sb.Append("{\"intent\": ").Append(R1Json.Quote(sem.Intent));
            sb.Append(", \"confidence\": ").Append(R1Json.Num(sem.Confidence));
            sb.Append(", \"missing_slots\": ").Append(StrArray(sem.MissingSlots));
            sb.Append(", \"ambiguities\": ").Append(R1Json.Num(sem.Ambiguities.Count));
            // R536: 多义不再停链 ⇒ 采用的解读（chosen）是**证据**：逐条落盘（span => chosen），可机检可追溯。
            sb.Append(", \"ambiguities_chosen\": ").Append(ChosenPairs(sem.Ambiguities));
            sb.Append(", \"refusal\": ").Append(sem.Refusal is null ? "null" : R1Json.Quote(sem.Refusal.Category + ": " + sem.Refusal.Reason));
            sb.Append(", \"done_when\": ").Append(StrArray(sem.DoneWhen));
            sb.Append("},\n");
        }

        sb.Append("  \"steps\": [");
        for (var i = 0; i < r.Steps.Count; i++)
        {
            var s = r.Steps[i];
            sb.Append(i == 0 ? "\n" : ",\n");
            sb.Append("    {\"id\": ").Append(R1Json.Quote(s.Id));
            sb.Append(", \"tool\": ").Append(R1Json.Quote(s.Tool));
            sb.Append(", \"rc\": ").Append(R1Json.Num(s.Rc));
            sb.Append(", \"path\": ").Append(R1Json.Quote(s.Path));
            sb.Append(", \"sha256\": ").Append(R1Json.Quote(s.Sha256));
            sb.Append(", \"bytes\": ").Append(R1Json.Num(s.Bytes));
            sb.Append(", \"elapsed_ms\": ").Append(R1Json.Num(s.ElapsedMs));
            sb.Append(", \"stdout_tail\": ").Append(R1Json.Quote(s.StdoutTail));
            sb.Append(", \"stderr_tail\": ").Append(R1Json.Quote(s.StderrTail));
            sb.Append("}");
        }
        sb.Append(r.Steps.Count == 0 ? "],\n" : "\n  ],\n");

        sb.Append("  \"artifacts\": [");
        var first = true;
        foreach (var s in r.Steps)
        {
            if (s.Tool != "write_file")
            {
                continue;
            }
            sb.Append(first ? "\n" : ",\n");
            first = false;
            sb.Append("    {\"path\": ").Append(R1Json.Quote(s.Path));
            sb.Append(", \"sha256\": ").Append(R1Json.Quote(s.Sha256));
            sb.Append(", \"bytes\": ").Append(R1Json.Num(s.Bytes));
            sb.Append("}");
        }
        sb.Append(first ? "]\n" : "\n  ]\n");
        sb.Append("}\n");
        return sb.ToString();
    }

    public static void Write(R1RunResult r, R1Options opt, string taskText)
    {
        if (string.IsNullOrWhiteSpace(opt.TranscriptPath))
        {
            return;
        }
        var path = Path.GetFullPath(opt.TranscriptPath);
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir))
        {
            Directory.CreateDirectory(dir);
        }
        File.WriteAllBytes(path, new UTF8Encoding(false).GetBytes(Render(r, opt, taskText)));
    }

    private static string StrArray(System.Collections.Generic.IReadOnlyList<string> items)
    {
        var sb = new StringBuilder("[");
        for (var i = 0; i < items.Count; i++)
        {
            sb.Append(i == 0 ? string.Empty : ", ").Append(R1Json.Quote(items[i]));
        }
        return sb.Append(']').ToString();
    }

    /// <summary>R536: 多义项的「片段 ⇒ 采用解读」逐条落盘（管道按 chosen 继续 ⇒ 该决策必须有痕）。</summary>
    private static string ChosenPairs(System.Collections.Generic.IReadOnlyList<agent.contract.Ambiguity> items)
    {
        var sb = new StringBuilder("[");
        for (var i = 0; i < items.Count; i++)
        {
            sb.Append(i == 0 ? string.Empty : ", ")
              .Append(R1Json.Quote(items[i].Span + " => " + items[i].Chosen));
        }
        return sb.Append(']').ToString();
    }

    /// <summary>R536: 「计划自测期望未达成」的步骤数（模型自述期望 vs 执行器实测冲突；≤1，首个不符即停机）。</summary>
    private static int SelfTestUnmet(R1RunResult r)
    {
        return r.Rc == 8 || r.Stage.StartsWith("expect_stdout", System.StringComparison.Ordinal) ? 1 : 0;
    }

    /// <summary>
    /// R539: 「本次运行是否断言了产物正确」。**只有 rc=0（链路达成）才为 1**；
    /// rc=8「自测未达成」与产物可疑成对出现 ⇒ correctness_asserted=0（判分器只吃本字段与外部用例，
    /// 禁把 rc 数字本身当正确性证据 —— 机检器 eval/rover/r539/rc8_evidence_guard.py）。
    /// </summary>
    public static int CorrectnessAsserted(R1RunResult r)
    {
        return r.Rc == 0 ? 1 : 0;
    }
}
