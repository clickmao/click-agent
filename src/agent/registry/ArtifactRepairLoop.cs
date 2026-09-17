using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using agent.config;
using agent.templates;

namespace agent.registry;

/// <summary>
/// R374 (D3) 运行结果回流闭环: 机器校验失败 → 失败输出回灌模型 → 有界修复 → **复检**。
///
/// 关键设计 (与真机铁证对齐):
///  - 复检判据不是"模型说修好了", 而是**重新走一遍落盘+机器校验**, 且必须出现
///    与失败产物不同的新文件并通过校验 (同路径 = 内容未变 = 没修)。
///  - 修复轮必须带 `Intent=code_generation`: 首轮预算策略按意图给足输出预算,
///    否则修复脚本会被推理吃满预算再次截断 (R373 铁证)。
///  - 诚实边界: 修不好则**保留原文**并在 telemetry `artifact_feedback` 里记 fixed=false。
/// </summary>
public sealed class ArtifactRepairLoop
{
    private readonly ResponseSegmentRouter _router;
    private readonly ILLMCaller _caller;
    private readonly Func<bool> _gate;

    public ArtifactRepairLoop(ResponseSegmentRouter router, ILLMCaller caller, Func<bool>? gate = null)
    {
        _router = router;
        _caller = caller;
        // 快照闸门 (同 PythonArtifactPlugin.runGate 的理由: 避免同进程别的用例改 env 造成行为漂移)
        var on = ArtifactRepairPolicy.IsEnabled();
        _gate = gate ?? (() => on);
    }

    public async Task<ArtifactRepairResult> RunAsync(string content, CancellationToken ct = default)
    {
        var checks = _router.DrainArtifactChecks();
        if (checks.Count == 0)
            return new ArtifactRepairResult(content, false, false, 0, "none", "本轮无产物校验结论");
        if (!_gate())
            return new ArtifactRepairResult(content, false, false, 0, "none", "回流修复被闸门关闭");

        var target = checks.FirstOrDefault(ArtifactRepairPolicy.IsRepairable);
        if (target is null)
            return new ArtifactRepairResult(content, false, false, 0, "none", $"本产物全部通过 ({checks.Count} 项)");

        var kind = target.ErrorKind;
        var started = Environment.TickCount64;
        var prompt = new Prompt
        {
            Intent = "code_generation",
            // 复用主链同一份代码任务系统提示 (含输出纪律第 9 条围栏要求) → 单一来源, 防纪律漂移。
            SystemPrompt = IntentPromptTemplates.GetSystemPrompt("code_generation")
                + "\n\n本轮是**修复轮**：依据机器校验的失败事实修正脚本，不要复述或解释原脚本。",
            UserMessage = ArtifactRepairPolicy.BuildPrompt(target),
            EstimatedTokens = 2000,
        };

        LLMResponse? resp = null;
        var fixedOk = false;
        var detail = string.Empty;
        var outContent = content;
        try
        {
            resp = await _caller.CallAsync(prompt, ct).ConfigureAwait(false);
        }
        catch (OperationCanceledException) { throw; }
        catch (Exception ex) { detail = $"修复调用异常: {ex.Message}"; }

        if (resp is not null)
        {
            if (resp.Success && !string.IsNullOrWhiteSpace(resp.Content))
            {
                outContent = await _router.ProcessAsync(resp.Content, ct).ConfigureAwait(false);
                var after = _router.DrainArtifactChecks();
                // 复检铁律: 必须出现"新路径且通过"的产物; 同路径 = 内容未变 = 没修好。
                var good = after.FirstOrDefault(a =>
                    a.Passed && !string.Equals(a.Path, target.Path, StringComparison.Ordinal));
                fixedOk = good is not null;
                detail = good is not null
                    ? $"复检通过: {good.Path}"
                    : after.Count == 0
                        ? "修复轮未产出新产物 (无围栏代码段)"
                        : after.All(a => string.Equals(a.Path, target.Path, StringComparison.Ordinal))
                            ? "修复轮内容未变 (同产物路径 → 未产出新代码)"
                            : $"修复后仍未通过 (类别={after[0].ErrorKind})";
            }
            else if (string.IsNullOrWhiteSpace(detail))
            {
                detail = $"修复调用失败: {resp.Error}";
            }
        }

        AgentTelemetry.Emit("artifact_feedback", "artifact-repair",
            ("attempts", 1), ("fixed", fixedOk), ("error_kind", kind),
            ("compile_valid", target.CompileValid), ("run_exit", target.RunExitCode),
            ("budget_intent", "code_generation"), ("ms", Environment.TickCount64 - started),
            ("tokens", resp?.TokensUsed ?? 0), ("detail", ArtifactRepairPolicy.Head(detail, 200)));

        return new ArtifactRepairResult(fixedOk ? outContent : content, true, fixedOk, 1, kind, detail);
    }
}
