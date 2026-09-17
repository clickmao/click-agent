namespace agent.frontendapi;

/// <summary>
/// R375 (exp2 P0-1): 前端事件出站枢纽 —— 进程内**唯一**出站口。
/// PromptService 用 EmitAsync 发信封; FrontendApiServer 挂接实际 TCP 连接推送 (AttachServer)。
/// 未挂接时不阻塞调用方 (记 Dropped/LastError 供诊断, 不伪造送达)。
/// </summary>
public sealed class FrontendEventHub
{
    private Func<string, Task>? _sender;
    private volatile IAskReplySink? _askSink;
    private volatile IApprovalReplySink? _approvalSink;
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

    /// <summary>R510: 审批应答面 (未挂接 ⇒ 路由层回 channel_unavailable, 不伪造批准)。</summary>
    public IApprovalReplySink? ApprovalSink => _approvalSink;

    public void AttachServer(Func<string, Task> sender) => _sender = sender;

    public void AttachAsk(IAskReplySink sink) => _askSink = sink;

    public void AttachApproval(IApprovalReplySink sink) => _approvalSink = sink;

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
