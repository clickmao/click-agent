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

/// <summary>
/// 日志路由器 (v7.15 L.2.1): 四位 flags 一条路径判定 —
///   console → Console.WriteLine
///   chatbox_thinking / chatbox_output → 生成 FrontendDirective/分片推送 (推送通道未实装前写入缓存, CLI 可见可测)
///   file → MemoryLogBuffer (CLI 存档) 
/// flags 来源: 构造注入全局默认 (config/base/logging.yaml); 每条日志可临时覆盖。
/// </summary>
public sealed class LogRouter
{
    private readonly LogFlags _defaultFlags;
    private readonly MemoryLogBuffer _buffer;
    private readonly TextWriter? _console;
    private readonly string? _sessionId;

    /// <summary>chatbox 分片推送暂存 (推送通道未实装 — 测试/CLI 经 Snapshot 验证; L.6 ⚠ 待宿主定传输通道)</summary>
    public List<FrontendDirective> Directives { get; } = new();

    private int _thinkingSeq;
    private readonly object _seqLock = new();

    public LogRouter(LogFlags defaultFlags, MemoryLogBuffer buffer, TextWriter? console = null, string? sessionId = null)
    {
        _defaultFlags = defaultFlags;
        _buffer = buffer;
        _console = console;
        _sessionId = sessionId;
    }

    /// <summary>L.6 定案: chatbox 推送通道出口 (CLI=ConsoleChatboxSink; websocket 宿主注入各自实现)</summary>
    public IChatboxSink? ChatboxSink { get; set; }

    /// <summary>v0.11.0 统一命令出口 (可选注入): thinking/输出指令同步走 @cmd 行协议 — 与 IChatboxSink 并行 (前端二选一解析)</summary>
    public agent.io.AgentCommandWriter? CommandWriter { get; set; }

    /// <summary>推送: sink 出口 + 缓存 (缓存保证 /log dump 与测试可回放); sink 异常吞掉 — 推送永不打断主链</summary>
    private void PushDirective(FrontendDirective directive)
    {
        Directives.Add(directive);
        try
        {
            ChatboxSink?.Push(directive);
        }
        catch
        {
            // 推送失败只影响前端显示 (第三方 sink 未守约时双重防御)
        }
        // v0.11.0: 同一指令镜像到统一命令通道 (@cmd 行协议 — AgentCommandIO 工具类, 前端 AgentCommandReader 读取)
        try
        {
            if (CommandWriter is not null)
                CommandWriter.Send(MapToCommand(directive));
        }
        catch
        {
            // 命令通道失败同 sink — 不打断主链
        }
    }

    /// <summary>FrontendDirective → 统一命令映射 (thinking_page_switch/thinking_end/output_append; 其余忽略 — 前向兼容)。</summary>
    private static agent.io.AgentCommand MapToCommand(FrontendDirective d)
    {
        var name = d.Type switch
        {
            "thinking_page_switch" => agent.io.AgentCommandNames.ThinkingPageSwitch,
            "thinking_end" => agent.io.AgentCommandNames.ThinkingEnd,
            "output_append" => agent.io.AgentCommandNames.OutputAppend,
            _ => d.Type,
        };
        return new agent.io.AgentCommand(name, new Dictionary<string, string>
        {
            ["seq"] = d.Seq.ToString(System.Globalization.CultureInfo.InvariantCulture),
            ["session"] = d.SessionId ?? string.Empty,
            ["summary_length"] = d.SummaryLength.ToString(System.Globalization.CultureInfo.InvariantCulture),
        });
    }

    /// <summary>写一条日志 (四 flag 在同一条路径上完成)</summary>
    public void Write(
        string module, string level, LogChannel channel, string msg,
        LogFlags? flagsOverride = null, string? contentFingerprint = null, int contentLength = 0)
    {
        var flags = flagsOverride ?? _defaultFlags;
        var entry = new LogEntry
        {
            Ts = DateTime.UtcNow.ToString("o", System.Globalization.CultureInfo.InvariantCulture),
            Level = level,
            Channel = channel.ToString().ToLowerInvariant(),
            Module = module,
            Msg = msg,
            SessionId = _sessionId,
            Seq = channel == LogChannel.Thinking ? NextSeq() : 0,
            ContentLength = contentLength,
            ContentHash = contentFingerprint ?? string.Empty,
        };

        // ── 单路径四分支: 同一个 entry, flags 决定路由 ──
        if (flags.Console)
            (_console ?? Console.Out).WriteLine(
                $"[{entry.Ts}] {entry.Level} {entry.Channel} {entry.Module}: {entry.Msg}");

        if (flags.File)
            _buffer.Add(entry);

        if (channel == LogChannel.Thinking && flags.ChatboxThinking)
        {
            // 指令 1 (首轮发 switch 由 ThinkingStreamScope 负责); 分片持续可推送
            PushDirective(new FrontendDirective
            {
                Type = "thinking_page_switch",
                SessionId = _sessionId,
                Seq = entry.Seq,
            });
        }

        if (channel == LogChannel.Output && flags.ChatboxOutput)
        {
            // 输出页内容 (前端接线后直达 chatbox; 现阶段缓存可测)
            PushDirective(new FrontendDirective
            {
                Type = "output_append",
                SessionId = _sessionId,
                Seq = entry.Seq,
            });
        }
    }

    /// <summary>缓存快照转发 (/log dump 存档用)</summary>
    public List<LogEntry> SnapshotEntries() => _buffer.Snapshot();

    /// <summary>指令 2: 思考结束 (前端关闭思考步骤显示并折叠)</summary>
    public void EmitThinkingEnd(int summaryLength)
    {
        PushDirective(new FrontendDirective
        {
            Type = "thinking_end",
            SessionId = _sessionId,
            SummaryLength = summaryLength,
        });
    }

    private int NextSeq()
    {
        lock (_seqLock)
        {
            return ++_thinkingSeq;
        }
    }
}
