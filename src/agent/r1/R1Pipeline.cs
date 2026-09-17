using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using agent.contract;
using agent.templates;

namespace agent.r1;

/// <summary>
/// R1 管道总装（用户令 2026-09-17：结构化 prompt ⇄ 远程 LLM ⇄ 结构化结果 ⇒ 精准语义 ⇒ 管道）：
///
///   前缀恒定自检 → 结构化调用 → 契约校验 → (至多 N 轮**契约**修复) → 语义闸 → 计划执行
///   → (实测不过 ⇒ 至多 M 轮**执行证据回灌**修复) → 台账
///
/// **结构量（R533）**：本管道发出的 prompt 一律置 <see cref="Prompt.StructuredSurface"/> ⇒
/// 模型侧无工具面、无动作环、无纪律尾块 ⇒ 实发 system 逐字节 = 恒定前缀 pin。
///
/// fail-closed：前缀漂移不起调用（rc=6）；契约不过不执行（rc=4）；闸 halt 不执行（rc=2/3）；
/// 实测不过先回灌修复；仍不过时按「产物是否齐」二分（R536）：计划跑完 ⇒ rc=8 self_test_unmet
/// （自测期望是模型自述，产物在盘），计划没跑完 ⇒ rc=5 —— **产物已落盘且 steps 原样带上**（不吞证据、不谎报成功）。
/// 与 CLAUDE-Fable-5.1 动因③「状态外置：模型只产契约，执行在管道」对齐：模型无工具面，工具面只在本类下游。
/// </summary>
public static class R1Pipeline
{
    public const string SessionTag = "r1-oneshot";

    public static async Task<R1RunResult> RunAsync(ILLMCaller caller, string taskText, R1Options opt, CancellationToken ct)
    {
        var prefixChars = StructuredPrompt.Prefix.Length;
        var prefixSha = StructuredPrompt.PrefixSha256();
        var taskSha = R1Hash.OfText(taskText ?? string.Empty);
        var roleChars = opt.RoleNote is null ? 0 : opt.RoleNote.Length;

        if (prefixChars != StructuredPrompt.PrefixChars || prefixSha != StructuredPrompt.PrefixSha256Pinned)
        {
            return new R1RunResult(6, "prefix_drift",
                "常量前缀漂移 (chars=" + prefixChars + " sha=" + prefixSha + ") ⇒ fail-closed 不起调用",
                string.Empty, R1CallStats.Empty, prefixChars, prefixSha, taskSha, null, roleChars, null,
                new List<StepOutcome>());
        }

        var calls = 0;
        var promptTokens = 0;
        var completionTokens = 0;
        int? cacheHit = null;
        int? cacheMiss = null;
        var repairs = 0;      // 契约修复轮
        var execRepairs = 0;  // 执行证据回灌修复轮
        string? repairNote = null;
        var raw = string.Empty;

        while (true)
        {
            Semantics? sem = null;
            IReadOnlyList<string> errors = new List<string>();

            while (true)
            {
                var prompt = new Prompt
                {
                    SystemPrompt = StructuredPrompt.Prefix,
                    UserMessage = R1RoleMount.AppendTo(
                        StructuredPrompt.BuildUserMessage(taskText ?? string.Empty, repairNote), opt.RoleNote),
                    SessionId = SessionTag,
                    TurnIndex = 1,
                    Intent = "code_task",
                    // R533: 结构量 —— 结构化前端 ⇒ 模型无工具面 / 无动作环 / 无纪律尾块。
                    StructuredSurface = true,
                };

                var resp = await caller.CallAsync(prompt, ct).ConfigureAwait(false);
                calls++;
                promptTokens += resp.PromptTokens;
                completionTokens += resp.CompletionTokens;
                if (resp.CacheHitTokens.HasValue)
                {
                    cacheHit = resp.CacheHitTokens;
                }
                if (resp.CacheMissTokens.HasValue)
                {
                    cacheMiss = resp.CacheMissTokens;
                }
                raw = resp.Content ?? string.Empty;

                if (!resp.Success)
                {
                    var statsT = new R1CallStats(calls, promptTokens, completionTokens, cacheHit, cacheMiss, repairs, execRepairs);
                    var fail = new R1RunResult(6, "llm_transport",
                        "调用失败: " + (resp.Error ?? "(no error)") + " ⇒ fail-closed 不执行",
                        raw, statsT, prefixChars, prefixSha, taskSha, null, roleChars, null, new List<StepOutcome>());
                    R1Transcript.Write(fail, opt, taskText ?? string.Empty);
                    return fail;
                }

                errors = StructuredContract.Validate(raw);
                if (errors.Count == 0)
                {
                    sem = StructuredContract.TryParse(raw, out var parseErrors);
                    errors = parseErrors;
                }
                if (sem is not null && errors.Count == 0)
                {
                    break;
                }

                sem = null;
                if (repairs >= opt.MaxRepair)
                {
                    break;
                }
                repairs++;
                repairNote = StructuredPrompt.RepairMessage(errors);
            }

            var statsAll = new R1CallStats(calls, promptTokens, completionTokens, cacheHit, cacheMiss, repairs, execRepairs);

            if (sem is null)
            {
                var bad = new R1RunResult(4, "contract",
                    "契约未过 (errors=" + errors.Count + "): " + (errors.Count > 0 ? errors[0] : "(空)"),
                    raw, statsAll, prefixChars, prefixSha, taskSha, null, roleChars, null, new List<StepOutcome>());
                R1Transcript.Write(bad, opt, taskText ?? string.Empty);
                return bad;
            }

            var gate = SemanticsPipeline.Gate(sem, opt.SandboxRoot);
            if (gate.Halted)
            {
                var halted = new R1RunResult(gate.Rc, gate.Stage, gate.Reason, raw, statsAll,
                    prefixChars, prefixSha, taskSha, sem, roleChars, null, new List<StepOutcome>());
                R1Transcript.Write(halted, opt, taskText ?? string.Empty);
                return halted;
            }

            if (sem.Plan.Count == 0)
            {
                var noExec = new R1RunResult(0, gate.Stage, gate.Reason + " (plan 空 ⇒ 不执行)", raw, statsAll,
                    prefixChars, prefixSha, taskSha, sem, roleChars, null, new List<StepOutcome>());
                R1Transcript.Write(noExec, opt, taskText ?? string.Empty);
                return noExec;
            }

            var exec = await PlanExecutor.RunAsync(sem.Plan, opt, ct).ConfigureAwait(false);
            if (exec.Rc == 0)
            {
                var done = new R1RunResult(0, "done", exec.Reason, raw, statsAll,
                    prefixChars, prefixSha, taskSha, sem, roleChars, opt.TranscriptPath, exec.Steps);
                R1Transcript.Write(done, opt, taskText ?? string.Empty);
                return done;
            }

            if (execRepairs >= opt.MaxExecRepair)
            {
                // R533: 不再「产物已落盘却直接停机」—— 先回灌真证据重发起; 预算耗尽才停机,
                // steps 原样带上 (产物在盘上, 判分器可继续核), 阶段名标 _exhausted 可机检。
                //
                // R536: 停机还要分**两类**——「计划自测期望」是**模型自述**（预测），「执行器实测」才是证据；
                //   两者冲突且**计划已跑完**（无剩余步骤 ⇒ 产物齐）⇒ rc=8 self_test_unmet:
                //   既不算链成功、也不算链失败, 两个数都可见（reply 带标记 + 台账 steps_executed/plan_steps_total）。
                //   其余情形（执行 rc≠0、或计划没跑完 ⇒ 产物不齐）⇒ 保留 rc=5「链未达成」。
                var planComplete = exec.Steps.Count >= sem.Plan.Count;
                if (exec.Stage == "expect_stdout" && planComplete)
                {
                    var unmet = new R1RunResult(8, "self_test_unmet",
                        exec.Reason + "（计划已跑完 " + exec.Steps.Count + "/" + sem.Plan.Count
                        + " 步, 产物在盘 ⇒ 记自测期望未达成, 不判链失败: 期望是模型自述, 判分以执行器实测/外部用例为准）",
                        raw + "\nR1_SELF_TEST_UNMET {\"steps_executed\":" + exec.Steps.Count
                        + ",\"plan_steps_total\":" + sem.Plan.Count + ",\"detail\":\"expect_stdout 不符\"}",
                        statsAll, prefixChars, prefixSha, taskSha, sem, roleChars, opt.TranscriptPath, exec.Steps);
                    R1Transcript.Write(unmet, opt, taskText ?? string.Empty);
                    return unmet;
                }
                var stage = execRepairs > 0 ? exec.Stage + "_exhausted" : exec.Stage;
                var stuck = new R1RunResult(exec.Rc, stage, exec.Reason, raw, statsAll,
                    prefixChars, prefixSha, taskSha, sem, roleChars, opt.TranscriptPath, exec.Steps);
                R1Transcript.Write(stuck, opt, taskText ?? string.Empty);
                return stuck;
            }

            execRepairs++;
            repairNote = StructuredPrompt.ExecRepairMessage(ExecEvidence(exec));
        }
    }

    /// <summary>
    /// 执行证据（R533）：只取**执行器实测**产物（rc / stdout 尾 / stderr 尾），不取模型自述。
    /// </summary>
    private static IReadOnlyList<string> ExecEvidence(PlanExecutorResult exec)
    {
        var lines = new List<string> { exec.Reason };
        foreach (var s in exec.Steps)
        {
            if (s.Tool == "run")
            {
                lines.Add("步骤 " + s.Id + " (" + s.Tool + ") 实测 rc=" + s.Rc
                    + " stdout尾=`" + s.StdoutTail + "` stderr尾=`" + s.StderrTail + "`");
            }
        }
        lines.Add("要求: 修正产生该实测结果的那一步（通常是 run 步骤的实现或参数），期望值不动。");
        return lines;
    }
}
