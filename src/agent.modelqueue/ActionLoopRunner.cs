using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;

/// <summary>
/// 动作环宿主: 调用 → 若有 tool_calls 则执行 → 回灌 → 再调用, 直到无 tool_calls 或触顶。
/// 所有外部效应都经 <see cref="IActionPort"/>; 本类只做协议编排。
/// </summary>
public static class ActionLoopRunner
{
    public const int DefaultMaxSteps = 6;

    /// <summary>R508: 项目级任务 (多文件 + 自测闭环) 常超过固定步数上限 ⇒ 有实质进展时按此续期。</summary>
    public const int StepExtendBy = 6;

    /// <summary>R508: 续期硬顶 (与 env 上限同值域)。</summary>
    public const int StepCeiling = 32;

    /// <summary>env 显式给定步数 ⇒ 视为用户硬上限: 不自动续期 (既有语义/证据可复现)。</summary>
    public static bool StepsOverriddenFromEnv()
    {
        var v = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_ACTION_MAX_STEPS");
        return int.TryParse(v, out var n) && n > 0 && n <= 32;
    }

    /// <summary>
    /// R508 结论: 「长预算增益」在项目级题上**被证伪**（默认自适应臂 32 步用满 ⇒ 11/12 且 token ×5;
    /// 显式短预算臂 3 步 ⇒ 12/12）⇒ 自适应预算**默认关闭**, 仅显式 env=1/on/true 时启用。
    /// </summary>
    public static bool AdaptiveBudgetEnabled()
    {
        var v = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_ACTION_ADAPTIVE_BUDGET");
        if (string.IsNullOrWhiteSpace(v)) return false;
        v = v.Trim();
        return !(v.Equals("off", StringComparison.OrdinalIgnoreCase)
                 || v.Equals("0", StringComparison.Ordinal)
                 || v.Equals("false", StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>开关 (env AGENTFRAMEWORK_ACTION_LOOP): off/0/false = 关; 其余(含未设) = 开。</summary>
    public static bool IsEnabled()
    {
        var v = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_ACTION_LOOP");
        if (string.IsNullOrWhiteSpace(v)) return true;
        v = v.Trim();
        return !(v.Equals("off", StringComparison.OrdinalIgnoreCase)
                 || v.Equals("0", StringComparison.Ordinal)
                 || v.Equals("false", StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>回灌文本上限 (单工具结果, 硬顶)。</summary>
    public const int MaxToolResultBytes = 8192;

    /// <summary>
    /// R524: 单工具结果回灌**缺省**上限 (字符)。实测对照 (R522 五调用 dump): codex 每步回执仅 105–253 字符
    /// ("Process exited with code 0" 级), 5 轮上下文只涨 1,757 tok; 我方回执 204/290/1,289 字符 ⇒ 上下文几乎不涨
    /// 的形状要求把回执压到摘要量级。需要全文时由 agent 显式再取 (显式 ≠ 默认灌)。
    /// </summary>
    public const int DefaultToolResultChars = 600;

    /// <summary>缺省回灌上限 (env AGENTFRAMEWORK_ACTION_RESULT_CHARS 可调, 上不超硬顶)。</summary>
    public static int ToolResultCharCap()
    {
        var v = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_ACTION_RESULT_CHARS");
        if (int.TryParse(v, out var n) && n > 0) return Math.Min(n, MaxToolResultBytes);
        return DefaultToolResultChars;
    }

    /// <summary>步骤上限 (env AGENTFRAMEWORK_ACTION_MAX_STEPS; 非法/≤0 → 默认)。</summary>
    public static int MaxSteps()
    {
        var v = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_ACTION_MAX_STEPS");
        if (int.TryParse(v, out var n) && n > 0 && n <= 32) return n;
        return DefaultMaxSteps;
    }

    /// <summary>克隆 prompt 并挂上回灌尾部 (前缀逐字节不变 ⇒ 缓存前缀单调增长)。</summary>
    internal static QueuePrompt Clone(QueuePrompt src, List<QueuePostUserMessage> postUser)
    {
        var copy = new QueuePrompt
        {
            SystemPrompt = src.SystemPrompt,
            ContextPrompt = src.ContextPrompt,
            UserMessage = src.UserMessage,
            EstimatedTokens = src.EstimatedTokens,
            SessionId = src.SessionId,
            TurnIndex = src.TurnIndex,
            ReasoningEffort = src.ReasoningEffort,
            ToolsJson = src.ToolsJson,
            Intent = src.Intent,
            // R495: 台账挂载块必须随 Clone 透传 —— 否则动作环内第二次及以后的远端调用会把挂载丢掉
            // (打点说挂了、实发面没挂 = R490/R494 同一类脱钩缺陷)。
            Mount = src.Mount,
            // R494: 隔离通道标记必须随 Clone 透传 —— 否则环内第二次及以后的调用会丢掉通道轴判据
            // (与 R490 的 replay_trimmed 同一类缺陷: 打点/判据与实发面脱钩)。
            IsolatedChannel = src.IsolatedChannel,
            // R490: 计数器必须随 Clone 透传 —— 否则经动作环的每一次远端调用都会把
            // 「剪裁了 N 条本地模板答复」打点成 0 (R490 T 臂首跑实测踩中: 请求体内模板串确已
            // 消失, 但 tool_decl_gate.replay_trimmed 恒 0) ⇒ 打点与实发面脱钩。
            ReplayTrimmedLocalTemplates = src.ReplayTrimmedLocalTemplates,
            // R491: 配对剪裁计数同因 (打点必须与实发面同寿命)
            ReplayTrimmedLocalUserTurns = src.ReplayTrimmedLocalUserTurns,
        };
        copy.History.AddRange(src.History);
        copy.ImageUrls.AddRange(src.ImageUrls);
        copy.PostUser.AddRange(postUser);
        return copy;
    }

    public static async Task<(QueueResponse Response, ActionLoopOutcome Outcome)> RunAsync(
        QueuePrompt prompt,
        Func<QueuePrompt, CancellationToken, Task<QueueResponse>> call,
        IActionPort port,
        int maxSteps,
        CancellationToken ct,
        Action<int, ActionToolCall, ActionExecutionResult>? onCall = null,
        bool? adaptiveBudget = null)
    {
        var outcome = new ActionLoopOutcome();
        var postUser = new List<QueuePostUserMessage>();
        var resp = await call(Clone(prompt, postUser), ct);
        // R508 步数预算自适应: 项目级任务(多文件+自测)常超固定上限。仅当「自上次续期以来确有成功工具调用」
        // 时按 StepExtendBy 续期, 硬顶 StepCeiling; 无进展即停 (不做死循环式烧钱)。env 显式给步数 = 用户硬上限, 不续期。
        var adaptive = adaptiveBudget ?? AdaptiveBudgetEnabled();
        var budget = maxSteps;
        var okAtLastExtend = 0;
        while (resp.Success && resp.ToolCalls is { Count: > 0 })
        {
            if (outcome.Steps >= budget)
            {
                var okNow = outcome.Records.Count(r => r.Ok);
                if (adaptive && okNow > okAtLastExtend && budget < StepCeiling)
                {
                    okAtLastExtend = okNow;
                    budget = Math.Min(budget + StepExtendBy, StepCeiling);
                    outcome.BudgetExtensions++;
                }
                else break;
            }
            outcome.Steps++;
            var calls = resp.ToolCalls!;
            outcome.ToolCalls += calls.Count;
            postUser.Add(QueuePostUserMessage.AssistantToolCalls(calls));
            foreach (var tc in calls)
            {
                ActionExecutionResult res;
                // R538: 条目面 started —— **执行前**发出 (前端可立刻显示 "正在运行 X", 对标 codex `• Working (Ns)`)。
                // 与步进共用一个通道/一个数据源 (同一 tc、同一步号); 未绑定观察者 ⇒ 零开销, 行为逐字节不变。
                var itemId = ActionItemText.ItemIdOf(tc.Id, outcome.Steps);
                var (itemKind, itemTitle, itemDetail) = ActionItemText.Describe(tc.Name, tc.ArgumentsJson);
                await ActionProgressObserver.ReportAsync(
                    new ActionStepProgress(outcome.Steps, tc.Name ?? string.Empty, false, 0)
                    {
                        Item = new ActionItemProgress(itemId, "started", itemKind, itemTitle, itemDetail,
                            string.Empty, 0, false, 0),
                    }).ConfigureAwait(false);
                try
                {
                    res = ActionToolDecl.IsDeclared(tc.Name)
                        ? await port.ExecuteAsync(tc, ct)
                        : new ActionExecutionResult { Ok = false, ExitCode = -1, Output = $"未声明的工具: {tc.Name}" };
                }
                catch (Exception ex)
                {
                    // 执行面异常不得中断主链: 作为失败结果回灌, 让模型自行改道
                    res = new ActionExecutionResult { Ok = false, ExitCode = -1, Output = "执行异常: " + ex.GetType().Name };
                    outcome.LastError = ex.GetType().Name;
                }
                outcome.Executed++;
                outcome.Records.Add(new ActionCallRecord
                {
                    Step = outcome.Steps,
                    Tool = tc.Name,
                    Ok = res.Ok,
                    ExitCode = res.ExitCode,
                    ElapsedMs = res.ElapsedMs,
                    OutputBytes = Encoding.UTF8.GetByteCount(res.Output ?? string.Empty),
                    ArgsSha8 = Sha8(tc.ArgumentsJson ?? string.Empty),
                });
                onCall?.Invoke(outcome.Steps, tc, res);
                // R510: 步进事件真发 —— 前端 task.progress 的**唯一**数据源 (未绑定观察者 ⇒ 零开销, 行为不变)。
                // 只报事实 (步号/工具/成败/耗时), 文案面不出现在这里 (避免第二处实现)。
                // R538: 同一次上报携带条目面 completed (输出尾/行数/截断/退出码) ⇒ item.completed 与 task.progress 同源同刻。
                var (outTail, outLines, outTruncated) = ActionItemText.Tail(res.Output);
                await ActionProgressObserver.ReportAsync(
                    new ActionStepProgress(outcome.Steps, tc.Name ?? string.Empty, res.Ok, res.ElapsedMs)
                    {
                        Item = new ActionItemProgress(itemId, "completed", itemKind, itemTitle, itemDetail,
                            outTail, outLines, outTruncated, res.ExitCode),
                    })
                    .ConfigureAwait(false);
                var rendered = res.Render(ToolResultCharCap());
                // R462 召回-现实一致性闸 (工具回灌面): 结果里引用的路径若当前工作区不存在 ⇒ 显式标 ✗,
                // 使「读了 A 文件, 里面说 B 文件已完成」这类陈旧引用在下游可见 (只打假 ⇒ 一致时零字节)。
                rendered = agent.core.RecallRealityGate.Verify(rendered, port.WorkspaceRoot, failOnly: true);
                postUser.Add(QueuePostUserMessage.ToolResult(tc.Id ?? string.Empty,
                    rendered + "\n" + LedgerLine(outcome)));
            }
            resp = await call(Clone(prompt, postUser), ct);
        }
        outcome.Converged = resp.Success && (resp.ToolCalls is null || resp.ToolCalls.Count == 0);
        outcome.MaxStepsHit = !outcome.Converged && resp.Success && resp.ToolCalls is { Count: > 0 };
        // R478: 环出口仍无正文 (max_steps 命中 / 上游只回工具调用) ⇒ 必须给**可见文案**, 禁静默空回复 (R457 铁律 ③)。
        // 定因只取协议字段; 文案与主链同源 (EmptyBodyDiagnosis) ⟹ 不新增第二处文案实现。
        if (resp.Success && string.IsNullOrWhiteSpace(resp.Content))
        {
            var exitCause = EmptyBodyDiagnosis.Classify(resp.FinishReason, resp.ToolCalls?.Count ?? 0, resp.ReasoningContent?.Length ?? 0);
            resp.ContentIsUserFacing = true;
            resp.Content = ModelQueueRouter.EmptyBodyBannerPrefix + EmptyBodyDiagnosis.Banner(exitCause, resp.FinishReason);
            resp.Error = outcome.MaxStepsHit ? "action_loop_max_steps_no_content" : "action_loop_empty_content";
        }
        return (resp, outcome);
    }

    /// <summary>R457 回灌事实台账: 让"本轮实际执行了什么"与模型自述可比对 (对齐断言式幻觉, 无关键字判据)。</summary>
    internal static string LedgerLine(ActionLoopOutcome o)
    {
        if (o.Records.Count == 0) return string.Empty;
        var sb = new StringBuilder("[本轮已执行] ");
        sb.Append(o.Executed).Append(" 次: ");
        for (int i = 0; i < o.Records.Count; i++)
        {
            if (i > 0) sb.Append(", ");
            var r = o.Records[i];
            sb.Append(r.Tool).Append("(rc=").Append(r.ExitCode).Append(")");
        }
        sb.Append("; 其中 write_file ").Append(o.Records.Count(r => r.Tool == "write_file"))
          .Append(" 次, run_command ").Append(o.Records.Count(r => r.Tool == "run_command"))
          .Append(" 次");
        return sb.ToString();
    }

    public static string Sha8(string text)
    {
        var bytes = Encoding.UTF8.GetBytes(text);
        var hash = System.Security.Cryptography.SHA256.HashData(bytes);
        var sb = new StringBuilder(8);
        for (var i = 0; i < 4; i++) sb.Append(hash[i].ToString("x2", System.Globalization.CultureInfo.InvariantCulture));
        return sb.ToString();
    }
}
