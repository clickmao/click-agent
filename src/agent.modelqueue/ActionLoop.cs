using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;

/// <summary>
/// R456 动作环 (Action Loop) —— 链机制修复: 声明面 / 解析面 / 执行面 / 回灌面。
/// 背景 (R455 源码级诊断, docs/reports/agent-chain-diagnosis-r455.md):
///   远端请求**无 tools 字段**、全仓**无人解析 tool_calls** ⇒ 模型只能以纯文本「承诺/澄清」,
///   可执行任务在链上无出口 ⇒ 用户轮数↑ 而产物 0 (R455 套件实测 0/4 产物, 计划 P1)。
/// 设计约束 (承重):
///   C1 机制非补丁: 不出现任何「用户话术关键词 → 动作」的分支; 出口 = 协议字段 (tools/tool_calls)。
///   C2 缓存前缀单调: 每步只在**尾部**追加 (assistant(tool_calls) → tool(...)), 前缀 system/context/history/user 不变。
///   C3 AOT: 零反射 —— 手写 Utf8JsonWriter 序列化; 解析复用既有 source-gen DTO。
///   C4 端口化: 执行面 = <see cref="IActionPort"/> (可替换); 本文件不含任何文件/进程 IO。
/// </summary>
public sealed class ActionToolCall
{
    public string Id { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    /// <summary>function.arguments 原文 (JSON 字符串体; 非法 JSON 也原样保留, 由执行面判定)。</summary>
    public string ArgumentsJson { get; set; } = "{}";
}

/// <summary>动作环审计记录 (每工具调用一条; 由执行面填充)。</summary>
public sealed class ActionCallRecord
{
    public int Step { get; set; }
    public string Tool { get; set; } = string.Empty;
    public bool Ok { get; set; }
    public int ExitCode { get; set; }
    public long ElapsedMs { get; set; }
    public int OutputBytes { get; set; }
    public string ArgsSha8 { get; set; } = string.Empty;
}

/// <summary>执行面结果 (有界文本回灌)。</summary>
public sealed class ActionExecutionResult
{
    public bool Ok { get; set; }
    public string Output { get; set; } = string.Empty;
    public int ExitCode { get; set; }
    public long ElapsedMs { get; set; }

    /// <summary>回灌给模型的**有界**文本 (始终非空 —— 空回灌会让模型误判「无结果」而重复调用)。</summary>
    public string Render(int maxBytes)
    {
        var head = Ok ? "ok" : "error";
        var body = Output ?? string.Empty;
        if (body.Length > maxBytes) body = body.Substring(0, maxBytes) + "\n...[truncated]";
        var sb = new StringBuilder();
        sb.Append('[').Append(head).Append(" rc=").Append(ExitCode).Append(" ms=").Append(ElapsedMs).Append("]\n");
        sb.Append(body.Length == 0 ? "(empty output)" : body);
        return sb.ToString();
    }
}

/// <summary>
/// 执行面端口 (R456 端口化纪律): 唯一允许产生文件/进程副作用的边界。
/// 替换实现 (沙箱/远程/回放) 不得改变链上其余部分。
/// </summary>
public interface IActionPort
{
    string Name { get; }
    /// <summary>R462: 会话工作区根 (供回灌面做「召回-现实一致性」机检); 无工作区概念的实现返回 null。</summary>
    string? WorkspaceRoot => null;
    Task<ActionExecutionResult> ExecuteAsync(ActionToolCall call, CancellationToken ct);
}

/// <summary>回灌消息 (追加在 user 之后, 保缓存前缀不变)。</summary>
public sealed class QueuePostUserMessage
{
    public string Role { get; set; } = "assistant";
    public string Content { get; set; } = string.Empty;
    /// <summary>assistant 消息的 tool_calls (role=assistant 时非空)。</summary>
    public List<ActionToolCall>? ToolCalls { get; set; }
    /// <summary>tool 消息对应的 id (role=tool 时非空)。</summary>
    public string? ToolCallId { get; set; }

    public static QueuePostUserMessage AssistantToolCalls(List<ActionToolCall> calls)
        => new() { Role = "assistant", Content = string.Empty, ToolCalls = calls };

    public static QueuePostUserMessage ToolResult(string id, string content)
        => new() { Role = "tool", Content = content, ToolCallId = id };
}

/// <summary>动作环终态 (KPI 归因: 步数/工具数/是否收敛)。</summary>
public sealed class ActionLoopOutcome
{
    public int Steps { get; set; }
    public int ToolCalls { get; set; }
    public int Executed { get; set; }
    public bool Converged { get; set; }
    public bool MaxStepsHit { get; set; }

    /// <summary>R508: 步数预算被自动续期的次数 (0 = 未续期)。</summary>
    public int BudgetExtensions { get; set; }
    public string LastError { get; set; } = string.Empty;
    public List<ActionCallRecord> Records { get; } = new();
}

/// <summary>声明面: 工具 JSON (OpenAI function-calling 形态, 手写常量 —— 无反射、无生成)。</summary>
public static class ActionToolDecl
{
    public const string ListDir = "list_dir";
    public const string ReadFile = "read_file";
    public const string WriteFile = "write_file";
    public const string RunCommand = "run_command";

    /// <summary>R511: 删除类工具 (破坏性 ⇒ 执行面必须过人工审批门; 无审批通道 ⇒ fail-closed 拒绝)。</summary>
    public const string DeleteFile = "delete_file";

    /// <summary>工具名白名单 (声明面与执行面同源; 执行面拒绝表外名称)。</summary>
    public static readonly string[] Names = { ListDir, ReadFile, WriteFile, RunCommand, DeleteFile };

    public static bool IsDeclared(string name)
    {
        foreach (var n in Names)
            if (string.Equals(n, name, StringComparison.Ordinal)) return true;
        return false;
    }

    /// <summary>
    /// 声明文本。字段稳定 ⇒ 每次调用逐字节相同 (缓存前缀不动, R377 红线 ≥97%)。
    /// </summary>
    public static readonly string ToolsJson =
        """
        [{"type":"function","function":{"name":"list_dir","description":"列出工作区目录条目(相对路径/大小/类型)","parameters":{"type":"object","properties":{"path":{"type":"string","description":"相对工作区根的目录路径, 省略=根"}},"required":[]}}},
        {"type":"function","function":{"name":"read_file","description":"读取工作区文本文件","parameters":{"type":"object","properties":{"path":{"type":"string","description":"相对工作区根的文件路径"},"max_bytes":{"type":"integer","description":"最大字节数(默认8192)"}},"required":["path"]}}},
        {"type":"function","function":{"name":"write_file","description":"写入/覆盖工作区文本文件","parameters":{"type":"object","properties":{"path":{"type":"string","description":"相对工作区根的文件路径"},"content":{"type":"string","description":"文件内容"}},"required":["path","content"]}}},
        {"type":"function","function":{"name":"run_command","description":"在工作区根执行一条命令并返回 stdout/stderr/退出码","parameters":{"type":"object","properties":{"command":{"type":"string","description":"命令原文"},"timeout_ms":{"type":"integer","description":"超时毫秒(默认120000, 上限600000)"}},"required":["command"]}}},
        {"type":"function","function":{"name":"delete_file","description":"删除工作区内的文件或目录(需人工审批; 未接入审批通道时一律拒绝)","parameters":{"type":"object","properties":{"path":{"type":"string","description":"相对工作区根的文件/目录路径"}},"required":["path"]}}}]
        """;
}

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
                await ActionProgressObserver.ReportAsync(
                    new ActionStepProgress(outcome.Steps, tc.Name ?? string.Empty, res.Ok, res.ElapsedMs))
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
