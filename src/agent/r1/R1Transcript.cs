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
