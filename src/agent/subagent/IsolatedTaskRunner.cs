using agent.session;
using Microsoft.Extensions.Logging;

namespace agent.subagent;

/// <summary>隔离任务执行结果 (I.4 输出边界: 带标记返回主对话, 不混入主任务计划)。</summary>
public sealed class IsolatedTaskResult
{
    public string IsolatedSessionId { get; set; } = string.Empty;

    /// <summary>用户原话 (无关新提问)</summary>
    public string TaskText { get; set; } = string.Empty;

    /// <summary>隔离 agent 回答</summary>
    public string? Answer { get; set; }

    public bool Success { get; set; }

    public string? Error { get; set; }

    /// <summary>执行耗时毫秒</summary>
    public long ElapsedMs { get; set; }

    /// <summary>判定审计 (无关分与理由)</summary>
    public string RelevanceReason { get; set; } = string.Empty;
}

/// <summary>
/// 隔离任务运行器 (v7.15 I.3):
/// 主 agent 任务循环中判定为无关的新提问 → 额外开隔离边界的子执行, 完成即销毁。
/// 隔离边界 (I.4):
///   会话 — 独立 SessionId (isolated-{guid}), 主会话历史不进入;
///   记忆 — 不写主 SessionMemory (隔离会话独立落盘, 结束后清除);
///   画像 — 一次性 Uid "isolated-agent-{guid}", 主 AgentProfile 不受影响;
///   问询 — 静默: 不注入 IUserPromptService, 低置信走保守执行不打断用户;
///   输出 — IsolatedTaskResult 带标记返回主对话。
/// 并发上限 2 (可配): 超限排队 (SemaphoreSlim)。
/// </summary>
public sealed class IsolatedTaskRunner
{
    private readonly ISessionManager _sessionManager;
    private readonly ILLMCallerForIsolated _llm;
    private readonly Microsoft.Extensions.Logging.ILogger _logger;
    private readonly SemaphoreSlim _concurrencyGate;

    public IsolatedTaskRunner(
        ISessionManager sessionManager,
        ILLMCallerForIsolated llm,
        Microsoft.Extensions.Logging.ILogger logger,
        int maxConcurrent = 2)
    {
        _sessionManager = sessionManager;
        _llm = llm;
        _logger = logger;
        _concurrencyGate = new SemaphoreSlim(maxConcurrent, maxConcurrent);
    }

    /// <summary>一次性 Uid (画像隔离: 主画像按真实 Uid 持久, 隔离 Uid 用完即弃)</summary>
    private static string NewIsolatedUid() => $"isolated-agent-{Guid.NewGuid():N}";

    /// <summary>
    /// 执行隔离任务 (调用方已完成无关判定)。
    /// 生命周期: 独立会话 → 无历史单轮 LLM → 回答返回 → 会话 End + 销毁。
    /// </summary>
    public async Task<IsolatedTaskResult> ExecuteAsync(
        string taskText, string relevanceReason, CancellationToken ct = default)
    {
        await _concurrencyGate.WaitAsync(ct);
        try
        {
            var sw = System.Diagnostics.Stopwatch.StartNew();
            var uid = NewIsolatedUid();
            var session = await _sessionManager.CreateSessionAsync(uid);
            try
            {
                // 隔离执行核心: 单轮无历史 LLM (空 system + 用户任务), 不进 V2 管道 (会话/记忆/画像全隔离)
                var prompt = new agent.templates.Prompt
                {
                    SystemPrompt = "你是一个一次性隔离子任务执行器。只回答给定的新任务本身, 不引用任何先前的对话上下文。",
                    ContextPrompt = string.Empty,
                    UserMessage = taskText,
                };
                var resp = await _llm.CallAsync(prompt, ct);
                sw.Stop();
                return new IsolatedTaskResult
                {
                    IsolatedSessionId = session.Id,
                    TaskText = taskText,
                    Answer = resp.Content,
                    Success = resp.Success,
                    Error = resp.Error,
                    ElapsedMs = sw.ElapsedMilliseconds,
                    RelevanceReason = relevanceReason,
                };
            }
            finally
            {
                // 销毁: 会话 End (I.4 资源边界 — 结束即销毁, 无残留)
                try { await _sessionManager.EndSessionAsync(session.Id); }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, "隔离会话 {SessionId} 结束失败 (不阻断结果返回)", session.Id);
                }
            }
        }
        finally
        {
            _concurrencyGate.Release();
        }
    }
}

/// <summary>隔离执行专用 LLM 端口 — 与主链 ILLMCaller 同签名; DI 绑定同一实现但隔离器绕过 V2 会话状态。</summary>
public interface ILLMCallerForIsolated
{
    Task<LLMResponse> CallAsync(agent.templates.Prompt prompt, CancellationToken ct = default);
}
