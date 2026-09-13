namespace agent.frontendapi;

/// <summary>ask.reply / ask.cancel 的消费面 (由 FrontendPromptService 实现; 路由层只依赖该接口)。</summary>
public interface IAskReplySink
{
    AskReplyOutcome Complete(string askId, Dictionary<string, string>? answers);
}

/// <summary>
/// R375 (exp2 P0-1): 前端事件出站枢纽 —— 进程内**唯一**出站口。
/// PromptService 用 EmitAsync 发信封; FrontendApiServer 挂接实际 TCP 连接推送 (AttachServer)。
/// 未挂接时不阻塞调用方 (记 Dropped/LastError 供诊断, 不伪造送达)。
/// </summary>
public sealed class FrontendEventHub
{
    private Func<string, Task>? _sender;
    private volatile IAskReplySink? _askSink;
    private int _emitted;
    private int _dropped;

    /// <summary>已送达事件数 (挂接后成功推送)。</summary>
    public int Emitted => Volatile.Read(ref _emitted);

    /// <summary>未挂接/推送失败而丢弃的事件数。</summary>
    public int Dropped => Volatile.Read(ref _dropped);

    /// <summary>最近一次推送失败原因 (诊断; null = 无失败)。</summary>
    public string? LastError { get; private set; }

    public bool ServerAttached => _sender is not null;

    public IAskReplySink? AskSink => _askSink;

    public void AttachServer(Func<string, Task> sender) => _sender = sender;

    public void AttachAsk(IAskReplySink sink) => _askSink = sink;

    public async Task EmitAsync(string envelopeLine)
    {
        var sender = _sender;
        if (sender is null)
        {
            Interlocked.Increment(ref _dropped);
            LastError = "server_not_attached";
            return;
        }
        try
        {
            await sender(envelopeLine).ConfigureAwait(false);
            Interlocked.Increment(ref _emitted);
        }
        catch (Exception ex)
        {
            Interlocked.Increment(ref _dropped);
            LastError = ex.Message;
        }
    }
}

public enum AskReplyOutcome
{
    /// <summary>答案已交给等待方 (含 cancel → null)。</summary>
    Answered,

    /// <summary>ask_id 未知 (过期/伪造/已被清理) —— 不静默接受。</summary>
    UnknownAsk,

    /// <summary>该 ask_id 已答过 (幂等重放) —— 不重复投递答案。</summary>
    AlreadyAnswered,
}
