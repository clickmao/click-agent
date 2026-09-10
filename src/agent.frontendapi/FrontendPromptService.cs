using System.Text;
using System.Text.Json;
using agent.core;
using agent.userinteraction;

namespace agent.frontendapi;

/// <summary>
/// v0.19 P1 ask 域 (R357): IUserPromptService 的 TCP 实现 — EvidenceGate 批量问询经
/// 前端协议路由: chat.send 触发问询 → 服务端 emit "ask" 事件 → 前端 ask.reply 提交答案 →
/// RequestCredentialsAsync 的 TaskCompletionSource 完成, V2 管线继续。
/// 语义铁律: 用户拒绝/超时返回 null (调用方走降级路径, 不伪造答案)。
/// </summary>
public sealed class FrontendPromptService : IUserPromptService
{
    private readonly Func<object, Task> _emitEvent;           // 事件出站 (ask 信封)
    private readonly int _timeoutSeconds;

    private sealed class Pending
    {
        public TaskCompletionSource<Dictionary<string, string>?> Tcs =
            new(TaskCreationOptions.RunContinuationsAsynchronously);
        public required string RequestId;
    }

    private Pending? _pending;
    private readonly object _lock = new();

    public FrontendPromptService(Func<object, Task> emitEvent, int timeoutSeconds = 300)
    {
        _emitEvent = emitEvent;
        _timeoutSeconds = timeoutSeconds;
    }

    public SupervisionLevel Supervision => SupervisionLevel.Standard;

    public bool SilentInterAgent { get; set; }

    public async Task<Dictionary<string, string>?> RequestCredentialsAsync(
        CredentialRequest request, CancellationToken ct = default)
    {
        var reqId = "ask-" + Guid.NewGuid().ToString("N")[..8];
        var pending = new Pending { RequestId = reqId };
        lock (_lock)
        {
            _pending?.Tcs.TrySetResult(null); // 上一问未答即被覆盖 → 视为放弃 (诚实语义)
            _pending = pending;
        }

        // ask 事件: questions[] = items (key/display/required/sensitive)
        await _emitEvent(new
        {
            ev = "ask",
            ask_id = reqId,
            service = request.ServiceName,
            purpose = request.Purpose,
            questions = request.Items.Select(i => new
            {
                key = i.Key, display = i.DisplayName, required = i.Required, sensitive = i.Sensitive,
            }),
        }).ConfigureAwait(false);

        try
        {
            return await pending.Tcs.Task.WaitAsync(TimeSpan.FromSeconds(_timeoutSeconds), ct)
                .ConfigureAwait(false);
        }
        catch (TimeoutException)
        {
            return null; // 超时 = 放弃 (V2 走降级)
        }
        finally
        {
            lock (_lock) { if (_pending == pending) _pending = null; }
        }
    }

    public Task<OperationApprovalResult> RequestOperationApprovalAsync(
        SensitiveOperationRequest request, CancellationToken ct = default)
    {
        // ask 域 P1 范围: 审批类仍走既有通道 (前端协议化待 P2); 保守拒绝 (不伪造批准)
        return Task.FromResult(new OperationApprovalResult
        {
            Approved = false,
            AnsweredBy = PromptAnswerSource.Denied,
            Reason = "frontend ask 域未实现审批路由 (P2)",
        });
    }

    /// <summary>ask.reply 消费点: 前端提交 {ask_id, answers:{key:value}} 或 {ask_id, cancel:true}。</summary>
    public bool TryComplete(string askId, Dictionary<string, string>? answers)
    {
        Pending? p;
        lock (_lock)
        {
            p = _pending;
            if (p is null || p.RequestId != askId) return false;
        }
        return p.Tcs.TrySetResult(answers);
    }
}
