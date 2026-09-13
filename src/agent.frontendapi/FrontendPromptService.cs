using agent.core;
using agent.userinteraction;

namespace agent.frontendapi;

/// <summary>
/// v0.19 P1 ask 域 (R357) / R375 (exp2 P0) 重构: IUserPromptService 的前端实现。
/// 出站: 经 FrontendEventHub 发**标准信封** {v,type:event,event:ask,payload:{ask_id,service,purpose,
/// timeout_s,questions:[{key,display,required,sensitive,data_type,multi_select,default_value,options[]}]}};
/// 入站: 路由 ask.reply / ask.cancel → Complete(askId, answers)。
/// 语义铁律: 拒绝/超时/取消一律返回 null (调用方走降级, 绝不伪造答案); 关闭必有 ask_closed 事件与原因。
/// </summary>
public sealed class FrontendPromptService : IUserPromptService, IAskReplySink
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

    private Pending? _pending;
    private readonly object _lock = new();

    /// <summary>已答 ask_id 缓存 (幂等重放: 同 id 重复提交不二次投递, 也不误判 unknown)。</summary>
    private readonly HashSet<string> _answered = new(StringComparer.Ordinal);
    private readonly Queue<string> _answeredOrder = new();
    private const int AnsweredCacheLimit = 32;

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
