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
///   → (实测不过 ⇒ 至多 M 轮**执行证据回灌**修复) → 产物侧公开用例独立回放 (R544, 默认关)
///   → 台账
///
/// **R600 · 修复环「带现状」（默认开）**：回灌修复轮的 user 轮随附**管道自己写入的盘上产物原文**
/// （<see cref="ArtifactCarryover"/>）—— 本管道无状态（模型只产契约、执行在管道），不带现状 ⇒
/// 修复实为「盲修」（模型须凭记忆重写整份计划）。轴 = AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER。
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

    public static async Task<R1RunResult> RunAsync(ILLMCaller caller, string taskText, R1Options opt, CancellationToken ct, SupplementInbox? supplements = null)
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
        // R550 · 探针证据回灌修复轮（独立预算, 默认关）。轴关 ⇒ 恒 0 ⇒ 逐位等于旧行为。
        var probeRepairs = 0;
        // R600 · 修复环「带现状」打点（机械可判：治疗档 >0, 对照档 ==0）。
        var carryoverRounds = 0;
        var carryoverFiles = 0;
        var carryoverChars = 0;
        string? repairNote = null;
        var raw = string.Empty;

        // R544 · 产物侧自检的**输入面**：题面公开用例的机械抽取（一次性，与调用无关）。
        // 开关关闭或抽不出 ⇒ probeSet 为 null ⇒ 探针不参与，链逐位等于旧行为（零回归）。
        PublicExampleSet? probeSet = null;
        if (opt.PublicSelfCheck && PublicExampleExtractor.TryExtract(taskText, out var extracted, out _))
        {
            probeSet = extracted;
        }

        // R546 · 早停轴（**默认关**）: 产物公开用例回放**已经**判定产物在多条题面用例上不符
        //   (pfail ≥ 阈值) 时,「再要一次远端调用做回灌修复」的边际价值被质疑 ⇒ 做成单变量可证伪。
        //   轴开 ⇒ 跳过该次修复调用、直接走**既有**终端分类(rc/stage 语义不变, correctness_asserted 不变);
        //   关闭(0) ⇒ 逐位等于旧行为(零回归由同一批臂的 off 列 + 既有单测钉住)。
        var earlyStopSkips = 0;

        while (true)
        {
            Semantics? sem = null;
            IReadOnlyList<string> errors = new List<string>();

            while (true)
            {
                // 时机锚①: 本步骤开跑前, 从台账取该插的补充 (低于阈值的不插, 继续等更匹配的步骤)。
                var injectedSupplements = supplements is null ? (IReadOnlyList<string>)Array.Empty<string>() : supplements.SelectFor(taskText);
                if (injectedSupplements.Count > 0 && supplements is not null)
                {
                    supplements.MarkConsumed(injectedSupplements);
                }
                var prompt = new Prompt
                {
                    SystemPrompt = StructuredPrompt.Prefix,
                    UserMessage = R1RoleMount.AppendTo(
                        StructuredPrompt.BuildUserMessage(taskText ?? string.Empty, repairNote, injectedSupplements), opt.RoleNote),
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

                // 时机锚②: 远端返回后收割用户在运行中补充进来的信息 (随下一次调用进入 user 轮可变区)。
                supplements?.Harvest();

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

            // R610 (RF0004.2 · M3 第一刀): 动作候选 = 远端**只做声明** ⇒ 由本地机械裁选器逐条裁定。
            //   轴关(显式 off) ⇒ 不解析 ⇒ 台账不出现候选字段(与旧台账逐字节同)。
            //   本轴只落「声明/采纳/拒绝」三个**机制面**计数; 裁定本身不改变 rc/stage（能力面由后续窗集轮判）。
            var ac = ActionCandidates.IsEnabled() ? ActionCandidates.Select(raw) : ActionCandidates.Empty;

            var gate = SemanticsPipeline.Gate(sem, opt.SandboxRoot);
            if (gate.Halted)
            {
                var halted = new R1RunResult(gate.Rc, gate.Stage, gate.Reason, raw, statsAll,
                    prefixChars, prefixSha, taskSha, sem, roleChars, null, new List<StepOutcome>(),
                    ActionCandidatesDeclared: ac.Declared, ActionCandidatesAccepted: ac.Accepted,
                    ActionCandidatesRejected: ac.Rejected);
                R1Transcript.Write(halted, opt, taskText ?? string.Empty);
                return halted;
            }

            if (sem.Plan.Count == 0)
            {
                var noExec = new R1RunResult(0, gate.Stage, gate.Reason + " (plan 空 ⇒ 不执行)", raw, statsAll,
                    prefixChars, prefixSha, taskSha, sem, roleChars, null, new List<StepOutcome>(),
                    ActionCandidatesDeclared: ac.Declared, ActionCandidatesAccepted: ac.Accepted,
                    ActionCandidatesRejected: ac.Rejected);
                R1Transcript.Write(noExec, opt, taskText ?? string.Empty);
                return noExec;
            }

            var exec = await PlanExecutor.RunAsync(sem.Plan, opt, ct).ConfigureAwait(false);

            // R544 · 产物侧独立自检（用户审计口径的机件化）: **rc=0 只是链路自述跑通, 不是产物正确**
            //   （R542 实测: rc=0 的 4 个 r1 臂产物仅 43–55/58）。
            // R545 · 触发面修正（R544 预注册 J1 被同窗实测**证伪** ⇒ 宣称收窄 + 修法，见 reports/r545）:
            //   旧触发面 `exec.Rc==0` **结构性不可达** —— R544 的 3 个 on 臂里 2 个在**计划执行阶段**就
            //   rc=5/8（模型自撰 expect_stdout 不符），根本没走到回放点 ⇒ 机制等于没挂到多数臂上。
            //   新触发面 = **全部「产物已在盘」的出口**（rc 0/5/8 皆可）：「产物在盘」的判据是**机械的** ——
            //   执行器 Steps 里出现过 write_file（唯一落盘工具）即成立，与链自报 rc 无关。
            //   零写盘（契约 rc=4 / 闸拒答 rc=2,3 / 空计划 / 首步 run 即失败）⇒ 探针**不跑**，显式记
            //   reason=no_artifacts_on_disk（缺项不得冒充零失败；该分支 rc 与关闭态逐位相同）。
            //   证据优先级（R545）：探针跑过且**失败** ⇒ 它比「模型自撰的期望」更硬 ⇒ 以它回灌
            //   （[public_probe] 优先于 [exec_repair]）；探针跑过且**全过**但链仍未达成 ⇒ 回报里明说
            //   「必要非充分」，禁据公开面收尾，主证据仍取执行器实测。
            var probe = opt.PublicSelfCheck && probeSet is not null
                ? (ArtifactsOnDisk(exec)
                    ? await PublicExampleProbe.RunAsync(probeSet, opt.SandboxRoot, opt.StepTimeoutSeconds, ct, exec.Rc)
                        .ConfigureAwait(false)
                    : PublicProbeResult.Skipped("no_artifacts_on_disk", exec.Rc))
                : null;

            if (probe is not null && probe.Ran && probe.Failed > 0)
            {
                // R546: 早停判据是**机械的**(探针自产计数 ≥ 阈值), 在链内、起臂前已入代码 ⇒ 非事后补记。
                var earlyStop = opt.EarlyStopPfail > 0 && probe.Failed >= opt.EarlyStopPfail;
                if (earlyStop)
                {
                    earlyStopSkips++;
                    raw += "\nR1_EARLY_STOP {\"pfail\":" + probe.Failed + ",\"threshold\":" + opt.EarlyStopPfail
                        + ",\"repair_skipped\":1,\"calls_saved\":1,\"trigger\":\"public_probe\"}";
                }
                // R550: 探针失败证据（题面公开用例回放, **非模型自述**）驱动的修复自成预算:
                //   轴关(0) ⇒ 条件退化为 `execRepairs < MaxExecRepair` ⇒ 与旧行为逐位同（零回归）;
                //   轴开(>0) ⇒ 探针那次修复不再挤占执行回灌预算 ⇒ 客观证据与实测证据各得其一。
                else if (probeRepairs < opt.MaxProbeRepair || execRepairs < opt.MaxExecRepair)
                {
                    if (probeRepairs < opt.MaxProbeRepair)
                    {
                        probeRepairs++;
                    }
                    else
                    {
                        execRepairs++;
                    }
                    repairNote = WithArtifacts(StructuredPrompt.PublicProbeRepairMessage(probe.Failures),
                        opt, exec.Steps, ref carryoverRounds, ref carryoverFiles, ref carryoverChars);
                    continue;
                }

                if (exec.Rc == 0)
                {
                    var budgetClause = earlyStopSkips > 0
                        ? "早停轴开(pfail≥" + opt.EarlyStopPfail + ", 实测 pfail=" + probe.Failed
                          + ") ⇒ 主动跳过回灌修复调用(省 1 次远端请求), 预算 " + opt.MaxExecRepair + " 未动;"
                        : "执行回灌修复预算 " + opt.MaxExecRepair + " 已用尽;";
                    var probeUnmet = new R1RunResult(8, "public_probe_unmet",
                        "题面公开用例回放未过 " + probe.Failed + "/" + probe.Total
                        + " 例（期望取自题面、与隐藏用例判分器同语义），" + budgetClause
                        + " ⇒ 成对报「回放未达成 ∧ 产物可疑」: rc=8 不作正确性证据 (correctness_asserted=0);"
                        + " 首例: " + (probe.Failures.Count > 0 ? probe.Failures[0] : "(无)"),
                        raw + "\nR1_PUBLIC_PROBE " + probe.MarkerJson(), statsAll,
                        prefixChars, prefixSha, taskSha, sem, roleChars, opt.TranscriptPath, exec.Steps, probe,
                        opt.EarlyStopPfail, earlyStopSkips, probeRepairs, carryoverRounds, carryoverChars,
                    ActionCandidatesDeclared: ac.Declared, ActionCandidatesAccepted: ac.Accepted,
                    ActionCandidatesRejected: ac.Rejected);
                    R1Transcript.Write(probeUnmet, opt, taskText ?? string.Empty);
                    return probeUnmet;
                }
                // exec.Rc != 0: 链自己已经报了未达成 ⇒ **保留链的分类**（rc/stage），探针只作为
                // 「必要非充分」的补充面随行（ran/total/failed 落台账）；探针**只降级自述成功**，
                // 不覆盖既有的失败分类 —— 否则 rc 语义会在两列间错位。
            }

            if (exec.Rc == 0)
            {
                var reason = probe is not null && probe.Ran
                    ? exec.Reason + " + 题面公开用例回放 " + probe.Total + "/" + probe.Total + " 过（管道自产证据）"
                    : exec.Reason;
                var done = new R1RunResult(0, "done", reason,
                    raw + (probe is not null ? "\nR1_PUBLIC_PROBE " + probe.MarkerJson() : string.Empty), statsAll,
                    prefixChars, prefixSha, taskSha, sem, roleChars, opt.TranscriptPath, exec.Steps, probe,
                    opt.EarlyStopPfail, earlyStopSkips, probeRepairs, carryoverRounds, carryoverChars,
                    ActionCandidatesDeclared: ac.Declared, ActionCandidatesAccepted: ac.Accepted,
                    ActionCandidatesRejected: ac.Rejected);
                R1Transcript.Write(done, opt, taskText ?? string.Empty);
                return done;
            }

            if (execRepairs >= opt.MaxExecRepair || earlyStopSkips > 0)
            {
                // R533: 不再「产物已落盘却直接停机」—— 先回灌真证据重发起; 预算耗尽才停机,
                // steps 原样带上 (产物在盘上, 判分器可继续核), 阶段名标 _exhausted 可机检。
                //
                // R536: 停机还要分**两类**——「计划自测期望」是**模型自述**（预测），「执行器实测」才是证据；
                //   两者冲突且**计划已跑完**（无剩余步骤 ⇒ 产物齐）⇒ rc=8 self_test_unmet:
                //   既不算链成功、也不算链失败, 两个数都可见（reply 带标记 + 台账 steps_executed/plan_steps_total）。
                //   其余情形（执行 rc≠0、或计划没跑完 ⇒ 产物不齐）⇒ 保留 rc=5「链未达成」。
                var planComplete = exec.Steps.Count >= sem.Plan.Count;
                var probeMarker = probe is not null ? "\nR1_PUBLIC_PROBE " + probe.MarkerJson() : string.Empty;
                if (exec.Stage == "expect_stdout" && planComplete)
                {
                    var unmet = new R1RunResult(8, "self_test_unmet",
                        exec.Reason + "（计划已跑完 " + exec.Steps.Count + "/" + sem.Plan.Count
                        + " 步, 产物在盘 ⇒ 成对报「自测未达成 ∧ 产物可疑」: 期望是模型自述, 判分以执行器实测/外部用例为准;"
                        + " rc=8 不作正确性证据 (correctness_asserted=0), 产物对错只能由外部门禁/隐藏用例判）"
                        + (probe is not null && probe.Ran ? "; 题面公开用例回放 " + (probe.Total - probe.Failed) + "/" + probe.Total + " 过（同一面, 不改变本分类）" : string.Empty),
                        raw + "\nR1_SELF_TEST_UNMET {\"steps_executed\":" + exec.Steps.Count
                        + ",\"plan_steps_total\":" + sem.Plan.Count + ",\"detail\":\"expect_stdout 不符\""
                        + ",\"artifact\":\"suspect\",\"correctness_asserted\":0}" + probeMarker,
                        statsAll, prefixChars, prefixSha, taskSha, sem, roleChars, opt.TranscriptPath, exec.Steps, probe,
                        opt.EarlyStopPfail, earlyStopSkips, probeRepairs, carryoverRounds, carryoverChars,
                    ActionCandidatesDeclared: ac.Declared, ActionCandidatesAccepted: ac.Accepted,
                    ActionCandidatesRejected: ac.Rejected);
                    R1Transcript.Write(unmet, opt, taskText ?? string.Empty);
                    return unmet;
                }
                var stage = (execRepairs > 0 || probeRepairs > 0) ? exec.Stage + "_exhausted" : exec.Stage;
                var stuck = new R1RunResult(exec.Rc, stage, exec.Reason, raw + probeMarker, statsAll,
                    prefixChars, prefixSha, taskSha, sem, roleChars, opt.TranscriptPath, exec.Steps, probe,
                    opt.EarlyStopPfail, earlyStopSkips, probeRepairs, carryoverRounds, carryoverChars,
                    ActionCandidatesDeclared: ac.Declared, ActionCandidatesAccepted: ac.Accepted,
                    ActionCandidatesRejected: ac.Rejected);
                R1Transcript.Write(stuck, opt, taskText ?? string.Empty);
                return stuck;
            }

            execRepairs++;
            var evidence = ExecEvidence(exec);
            if (probe is not null && probe.Ran && probe.Failed == 0)
            {
                var withProbe = new List<string> { StructuredPrompt.PublicProbePassedNote(probe.Total) };
                withProbe.AddRange(evidence);
                evidence = withProbe;
            }
            repairNote = WithArtifacts(StructuredPrompt.ExecRepairMessage(evidence),
                opt, exec.Steps, ref carryoverRounds, ref carryoverFiles, ref carryoverChars);
        }
    }

    /// <summary>
    /// R600 · 修复环「带现状」：把**盘上产物原文**随附进修复指令（轴关 ⇒ 原样返回 = 逐位等于旧行为）。
    /// 只做字节搬运（见 <see cref="ArtifactCarryover"/>）；累计轮数/字符数进台账字段
    /// （artifact_carryover_rounds/chars），使「机制是否真挂上」可机械判（治疗档 >0 / 对照档缺席）。
    /// </summary>
    private static string WithArtifacts(string repairNote, R1Options opt, IReadOnlyList<StepOutcome> steps,
        ref int rounds, ref int files, ref int chars)
    {
        if (!opt.ArtifactCarryoverEnabled)
        {
            return repairNote;
        }
        var carry = ArtifactCarryover.Render(opt.SandboxRoot, steps);
        if (carry.Count == 0)
        {
            return repairNote;
        }
        foreach (var ln in carry)
        {
            if (ln.StartsWith("--- ", StringComparison.Ordinal) && !ln.StartsWith("--- end", StringComparison.Ordinal))
            {
                files++;
            }
        }
        var text = string.Join("\n", carry);
        rounds++;
        chars += text.Length;
        return repairNote + "\n\n" + text;
    }

    /// <summary>
    /// 「产物已在盘」的**机械**判据（R545）：执行器 Steps 里出现过 write_file（唯一落盘工具）即成立。
    /// 与链自报 rc 无关 —— 计划一步没写盘（契约/闸拒答/空计划/首步 run 即失败）⇒ 无产物可回放。
    /// </summary>
    private static bool ArtifactsOnDisk(PlanExecutorResult exec)
    {
        foreach (var s in exec.Steps)
        {
            if (s.Tool == "write_file")
            {
                return true;
            }
        }
        return false;
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
