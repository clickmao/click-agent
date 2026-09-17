namespace agent.logging;


/// <summary>
/// CLI 日志缓存 (L.2.1): 环形缓冲 (上限 2000 条) — CLI 本身也处理到日志缓存内, /log dump 时存档到文件。
/// 线程安全: lock 保护 (C# 线程安全模式)。
/// </summary>
public sealed class MemoryLogBuffer
{
    private readonly object _lock = new();
    private readonly Queue<LogEntry> _entries = new();
    private readonly int _capacity;

    public MemoryLogBuffer(int capacity = 2000) => _capacity = capacity;

    public void Add(LogEntry entry)
    {
        lock (_lock)
        {
            if (_entries.Count >= _capacity)
                _entries.Dequeue();
            _entries.Enqueue(entry);
        }
    }

    /// <summary>快照 (存档用 — 返回时间序副本)</summary>
    public List<LogEntry> Snapshot()
    {
        lock (_lock)
        {
            return _entries.ToList();
        }
    }

    public int Count
    {
        get { lock (_lock) return _entries.Count; }
    }
}
