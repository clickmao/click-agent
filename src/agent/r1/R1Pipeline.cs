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
///   前缀恒定自检 → 单次结构化调用 → 契约校验 → (至多 N 轮修复) → 语义闸 → 计划执行 → 台账
///
/// fail-closed 三条：前缀漂移不起调用（rc=6）；契约不过不执行（rc=4）；闸有 halt 不执行（rc=2/3/4）。
/// 与 CLAUDE-Fable-5.1 动因③「状态外置：模型只产契约，执行在管道」对齐 —— 模型无工具面，工具面只在本类下游。
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
        var repairs = 0;
        string? repairNote = null;
        Semantics? sem = null;
        IReadOnlyList<string> errors = new List<string>();
        var raw = string.Empty;

        for (var round = 0; round <= opt.MaxRepair; round++)
        {
            var prompt = new Prompt
            {
                SystemPrompt = StructuredPrompt.Prefix,
                UserMessage = R1RoleMount.AppendTo(StructuredPrompt.BuildUserMessage(taskText ?? string.Empty, repairNote), opt.RoleNote),
                SessionId = SessionTag,
                TurnIndex = 1,
                Intent = "code_task",
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
                var stats = new R1CallStats(calls, promptTokens, completionTokens, cacheHit, cacheMiss, repairs);
                var fail = new R1RunResult(6, "llm_transport",
                    "调用失败: " + (resp.Error ?? "(no error)") + " ⇒ fail-closed 不执行",
                    raw, stats, prefixChars, prefixSha, taskSha, null, roleChars, null, new List<StepOutcome>());
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
            if (round >= opt.MaxRepair)
            {
                break;
            }
            repairs++;
            repairNote = StructuredPrompt.RepairMessage(errors);
        }

        var statsAll = new R1CallStats(calls, promptTokens, completionTokens, cacheHit, cacheMiss, repairs);

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
        var done = new R1RunResult(exec.Rc, exec.Rc == 0 ? "done" : exec.Stage, exec.Reason, raw, statsAll,
            prefixChars, prefixSha, taskSha, sem, roleChars, opt.TranscriptPath, exec.Steps);
        R1Transcript.Write(done, opt, taskText ?? string.Empty);
        return done;
    }
}
