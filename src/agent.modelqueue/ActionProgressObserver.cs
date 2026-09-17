namespace agent.modelqueue;

/// <summary>
/// R510: 动作环「步进」观察面 —— 一次工具执行的事实 (步号/工具/成败/耗时)。
/// 只带事实字段, 不带任何展示文案 (文案面由出站方决定, 避免第二处实现)。
/// </summary>
public readonly record struct ActionStepProgress(int StepIndex, string Tool, bool Ok, long ElapsedMs);

/// <summary>
/// R510: 动作环步进上报 —— 前端 task.progress 事件的**数据源** (R509 只登记不发射, 此处补上真实发射面)。
///
/// 设计约束 (为什么是 AsyncLocal 而不是全局静态槽):
///  1) 宿主进程可能同时跑多个会话 (chat.send 并发), 全局槽会把 A 会话的步进发到 B 会话的任务上;
///     AsyncLocal 由调用方在 ProcessAsync **之前**绑定, 动作环内的 await 链自然继承同一流 ⇒ 归属精确。
///  2) 未绑定 (REPL/one-shot/单测) ⇒ 零开销、零副作用: 现有行为逐字节不变。
///  3) 出站面异常**不得**中断主链 (动作环是主链); 但也不静默 —— Failed/LastError 供诊断 (与 FrontendEventHub 同口径)。
/// </summary>
public static class ActionProgressObserver
{
    private static readonly AsyncLocal<Func<ActionStepProgress, Task>?> _sink = new();
    private static int _reported;
    private static int _failed;
    private static string? _lastError;

    /// <summary>已上报步数 (未绑定时恒 0 ⇒ 可做「零开销」负控读数)。</summary>
    public static int Reported => System.Threading.Volatile.Read(ref _reported);

    /// <summary>出站面失败次数。</summary>
    public static int Failed => System.Threading.Volatile.Read(ref _failed);

    /// <summary>最近一次失败原因 (null = 无失败)。</summary>
    public static string? LastError => _lastError;

    /// <summary>当前上下文是否已绑定出站面。</summary>
    public static bool Bound => _sink.Value is not null;

    /// <summary>
    /// 绑定出站面 (作用域 = 当前异步流)。返回的 IDisposable 必须 Dispose (恢复上一绑定)。
    /// 允许嵌套: 内层覆盖外层, Dispose 后回退 (不丢外层)。
    /// </summary>
    public static IDisposable Bind(Func<ActionStepProgress, Task> sink)
    {
        ArgumentNullException.ThrowIfNull(sink);
        var prev = _sink.Value;
        _sink.Value = sink;
        return new Scope(prev);
    }

    /// <summary>上报一步。未绑定 = 立即返回 (不计数); 失败 = 计数 + 记 LastError, 不抛出。</summary>
    public static async Task ReportAsync(ActionStepProgress step)
    {
        var sink = _sink.Value;
        if (sink is null) return;
        Interlocked.Increment(ref _reported);
        try
        {
            await sink(step).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            Interlocked.Increment(ref _failed);
            _lastError = ex.GetType().Name + ": " + ex.Message;
        }
    }

    /// <summary>测试用: 清空上下文绑定与计数 (静态状态不得跨用例泄漏)。</summary>
    internal static void ResetForTests()
    {
        _sink.Value = null;
        Interlocked.Exchange(ref _reported, 0);
        Interlocked.Exchange(ref _failed, 0);
        _lastError = null;
    }

    private sealed class Scope : IDisposable
    {
        private readonly Func<ActionStepProgress, Task>? _prev;
        private int _disposed;
        public Scope(Func<ActionStepProgress, Task>? prev) => _prev = prev;
        public void Dispose()
        {
            if (Interlocked.Exchange(ref _disposed, 1) == 1) return;
            _sink.Value = _prev;
        }
    }
}
