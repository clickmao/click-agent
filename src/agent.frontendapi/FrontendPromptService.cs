using agent.core;

namespace agent.frontendapi;

/// <summary>
/// v0.19 P1 ask 域 (R357) / R375 (exp2 P0) 重构: IUserPromptService 的前端实现。
/// 出站: 经 FrontendEventHub 发**标准信封** {v,type:event,event:ask,payload:{ask_id,service,purpose,
/// timeout_s,questions:[{key,display,required,sensitive,data_type,multi_select,default_value,options[]}]}};
/// 入站: 路由 ask.reply / ask.cancel → Complete(askId, answers)。
/// 语义铁律: 拒绝/超时/取消一律返回 null (调用方走降级, 绝不伪造答案); 关闭必有 ask_closed 事件与原因。
/// </summary>
public sealed class FrontendPromptService : IUserPromptService, IAskReplySink, IApprovalReplySink
{
    private readonly Func<string, Task> _emitEnvelope;   // 事件出站 (已序列化信封行)
    private readonly int _timeoutSeconds;

    private sealed class Pending
    {
        public TaskCompletionSource<Dictionary<string, string>?> Tcs =
            new(TaskCreationOptions.RunContinuationsAsynchronously);
        public required string RequestId;
        public bool Superseded;
    }

    /// <summary>等待中的审批 (R510)。与 asks 分开登记: 审批与凭据问询是两条独立通道, 不互相覆盖。</summary>
    private sealed class PendingApproval
    {
        public TaskCompletionSource<(bool Approved, string? Reason)> Tcs =
            new(TaskCreationOptions.RunContinuationsAsynchronously);
        public required string ApprovalId;
        public bool Superseded;
    }

    private Pending? _pending;
    private PendingApproval? _pendingApproval;
    private readonly object _lock = new();

    /// <summary>已答 ask_id 缓存 (幂等重放: 同 id 重复提交不二次投递, 也不误判 unknown)。</summary>
    private readonly HashSet<string> _answered = new(StringComparer.Ordinal);
    private readonly Queue<string> _answeredOrder = new();
    private const int AnsweredCacheLimit = 32;

    /// <summary>已答 approval_id 缓存 (同口径幂等)。</summary>
    private readonly HashSet<string> _answeredApprovals = new(StringComparer.Ordinal);
    private readonly Queue<string> _answeredApprovalOrder = new();

    public FrontendPromptService(Func<string, Task> emitEnvelope, int timeoutSeconds = 300)
    {
        _emitEnvelope = emitEnvelope;
        _timeoutSeconds = timeoutSeconds;
    }

    public SupervisionLevel Supervision => SupervisionLevel.Standard;

    public bool SilentInterAgent { get; set; }

    public async Task<Dictionary<string, string>?> RequestCredentialsAsync(
        CredentialRequest request, CancellationToken ct = default)
    {
        var reqId = "ask-" + Guid.NewGuid().ToString("N")[..8];
        var pending = new Pending { RequestId = reqId };
        string? supersededId = null;
        lock (_lock)
        {
            if (_pending is not null)
            {
                _pending.Superseded = true;
                supersededId = _pending.RequestId;
                _pending.Tcs.TrySetResult(null); // 上一问未答即被覆盖 → 视为放弃 (诚实语义)
            }
            _pending = pending;
        }
        if (supersededId is not null)
            await _emitEnvelope(AskEnvelope.BuildClosed(supersededId, "superseded")).ConfigureAwait(false);

        var timeoutSeconds = request.TimeoutSeconds is > 0 ? request.TimeoutSeconds.Value! : _timeoutSeconds;
        var questions = BuildQuestions(request);
        await _emitEnvelope(AskEnvelope.BuildAsk(
            reqId, request.ServiceName, request.Purpose, timeoutSeconds, questions.Count, questions))
            .ConfigureAwait(false);

        try
        {
            var answers = await pending.Tcs.Task.WaitAsync(TimeSpan.FromSeconds(timeoutSeconds), ct)
                .ConfigureAwait(false);
            await _emitEnvelope(AskEnvelope.BuildClosed(reqId, answers is null ? "cancelled" : "answered"))
                .ConfigureAwait(false);
            return answers;
        }
        catch (TimeoutException)
        {
            await _emitEnvelope(AskEnvelope.BuildClosed(reqId, "timeout")).ConfigureAwait(false);
            return null; // 超时 = 放弃 (V2 走降级)
        }
        catch (OperationCanceledException)
        {
            await _emitEnvelope(AskEnvelope.BuildClosed(reqId, "cancelled")).ConfigureAwait(false);
            return null;
        }
        finally
        {
            lock (_lock) { if (_pending == pending) _pending = null; }
        }
    }

    /// <summary>
    /// R510: 审批通道真实现 (R357 起为保守拒绝占位 —— 「P2」欠账)。
    /// 语义: 发 approval.requested 事件 → 等 approval.respond → 每个请求必发 approval.responded 收口。
    /// 拒绝/超时/取消/被新审批覆盖 **一律不批准** (fail-closed); 超时按 _timeoutSeconds (默认 300s)。
    /// </summary>
    public async Task<OperationApprovalResult> RequestOperationApprovalAsync(
        SensitiveOperationRequest request, CancellationToken ct = default)
    {
        var approvalId = "apr-" + Guid.NewGuid().ToString("N")[..8];
        var pending = new PendingApproval { ApprovalId = approvalId };
        string? supersededId = null;
        lock (_lock)
        {
            if (_pendingApproval is not null)
            {
                _pendingApproval.Superseded = true;
                supersededId = _pendingApproval.ApprovalId;
                _pendingApproval.Tcs.TrySetResult((false, "superseded_by_new_approval")); // 覆盖 ⇒ 放弃 (诚实语义)
            }
            _pendingApproval = pending;
        }
        if (supersededId is not null)
            await _emitEnvelope(ApprovalEnvelope.BuildResponded(
                supersededId, approved: false, nameof(PromptAnswerSource.Denied), "superseded_by_new_approval"))
                .ConfigureAwait(false);

        var timeoutSeconds = _timeoutSeconds > 0 ? _timeoutSeconds : 300;
        await _emitEnvelope(ApprovalEnvelope.BuildRequested(
            approvalId,
            request.Kind.ToString(),
            request.Summary ?? string.Empty,
            request.Details ?? string.Empty,
            request.Initiator ?? string.Empty,
            timeoutSeconds)).ConfigureAwait(false);

        try
        {
            var (approved, reason) = await pending.Tcs.Task
                .WaitAsync(TimeSpan.FromSeconds(timeoutSeconds), ct).ConfigureAwait(false);
            await _emitEnvelope(ApprovalEnvelope.BuildResponded(
                approvalId, approved,
                approved ? nameof(PromptAnswerSource.RealUser) : nameof(PromptAnswerSource.Denied),
                reason ?? string.Empty)).ConfigureAwait(false);
            return new OperationApprovalResult
            {
                Approved = approved,
                AnsweredBy = approved ? PromptAnswerSource.RealUser : PromptAnswerSource.Denied,
                Reason = reason,
            };
        }
        catch (TimeoutException)
        {
            await _emitEnvelope(ApprovalEnvelope.BuildResponded(
                approvalId, approved: false, nameof(PromptAnswerSource.Timeout), "timeout")).ConfigureAwait(false);
            return new OperationApprovalResult
            {
                Approved = false,
                AnsweredBy = PromptAnswerSource.Timeout,
                Reason = "timeout",
            };
        }
        catch (OperationCanceledException)
        {
            await _emitEnvelope(ApprovalEnvelope.BuildResponded(
                approvalId, approved: false, nameof(PromptAnswerSource.Denied), "cancelled")).ConfigureAwait(false);
            return new OperationApprovalResult
            {
                Approved = false,
                AnsweredBy = PromptAnswerSource.Denied,
                Reason = "cancelled",
            };
        }
        finally
        {
            lock (_lock) { if (ReferenceEquals(_pendingApproval, pending)) _pendingApproval = null; }
        }
    }

    /// <summary>approval.respond 消费点 (幂等: 同 approval_id 重复提交不二次投递, 也不误判 unknown)。</summary>
    public ApprovalReplyOutcome CompleteApproval(string approvalId, bool approved, string? reason)
    {
        PendingApproval? p;
        lock (_lock)
        {
            p = _pendingApproval;
            if (p is null || p.ApprovalId != approvalId)
                return _answeredApprovals.Contains(approvalId)
                    ? ApprovalReplyOutcome.AlreadyAnswered
                    : ApprovalReplyOutcome.UnknownApproval;
            RememberApproval(approvalId);
        }
        return p.Tcs.TrySetResult((approved, reason)) ? ApprovalReplyOutcome.Applied : ApprovalReplyOutcome.AlreadyAnswered;
    }

    /// <summary>ask.reply / ask.cancel 消费点 (P1-6 幂等: 同 ask_id 重复提交不二次投递)。</summary>
    public AskReplyOutcome Complete(string askId, Dictionary<string, string>? answers)
    {
        Pending? p;
        lock (_lock)
        {
            p = _pending;
            if (p is null || p.RequestId != askId)
                return _answered.Contains(askId) ? AskReplyOutcome.AlreadyAnswered : AskReplyOutcome.UnknownAsk;
            Remember(askId);
        }
        return p.Tcs.TrySetResult(answers) ? AskReplyOutcome.Answered : AskReplyOutcome.AlreadyAnswered;
    }

    private void Remember(string askId)
    {
        if (_answered.Add(askId)) _answeredOrder.Enqueue(askId);
        while (_answeredOrder.Count > AnsweredCacheLimit)
            _answered.Remove(_answeredOrder.Dequeue());
    }

    private void RememberApproval(string approvalId)
    {
        if (_answeredApprovals.Add(approvalId)) _answeredApprovalOrder.Enqueue(approvalId);
        while (_answeredApprovalOrder.Count > AnsweredCacheLimit)
            _answeredApprovals.Remove(_answeredApprovalOrder.Dequeue());
    }

    /// <summary>条目 → 通道题面: 选项/类型必须结构化下发 (前端渲染菜单), 不再只拼文本。</summary>
    internal static List<AskQuestion> BuildQuestions(CredentialRequest request)
    {
        var list = new List<AskQuestion>(request.Items.Count);
        foreach (var i in request.Items)
        {
            var dt = string.IsNullOrWhiteSpace(i.DataType) ? InferDataType(i) : i.DataType!;
            var multi = i.MultiSelect || string.Equals(dt, "multi_choice", StringComparison.OrdinalIgnoreCase);
            var options = i.Choices.Select(c => new AskOption(c.Value, c.Label, c.Recommended)).ToList();
            list.Add(new AskQuestion(i.Key, i.DisplayName, i.Required, i.Sensitive, dt, multi, options, i.DefaultValue));
        }
        return list;
    }

    private static string InferDataType(CredentialItem i)
    {
        if (i.Sensitive) return "text";
        if (i.Choices.Count > 0) return i.MultiSelect ? "multi_choice" : "choice";
        return "text";
    }
}
