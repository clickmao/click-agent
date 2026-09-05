namespace agent.registry;

/// <summary>
/// 非 LLM 本地强制指令 (v7.11): /stop /continue /pause /status /reset。
/// 在进入意图识别/LLM 之前拦截 — 强制指令不消耗 token、不经过模型判断。
/// </summary>
public class LocalCommandResult
{
    /// <summary>true = 已作为命令处理 (调用方短路返回, 不进 LLM)</summary>
    public bool Handled { get; init; }

    public string Command { get; init; } = string.Empty;

    /// <summary>命令参数 (/stop plan-id 里的 plan-id)</summary>
    public string? Argument { get; init; }

    /// <summary>给用户的执行反馈 (不进模型)</summary>
    public string Reply { get; init; } = string.Empty;
}

/// <summary>
/// 本地命令路由器: 前缀匹配, O(1) 判定。
/// /stop 语义联动 TaskPlanRun 取消 — 停止指令永远生效, 不需要问询 (工业规则)。
/// </summary>
public static class LocalCommandRouter
{
    private static readonly HashSet<string> Known = new(StringComparer.OrdinalIgnoreCase)
    {
        "/model", "/balance",  // v7.15 模型队列: 切换/查询 (V2 拦截层特判, router 落地)
        "/log",  // v7.15 日志四通道: /log dump → MemoryLogBuffer 存档文件 (JSON 行)
        "/stop", "/continue", "/pause", "/status", "/reset",
    };

    /// <summary>尝试拦截。非命令 (null/不以 / 开头/未知命令) → Handled=false 正常进管线。</summary>
    public static LocalCommandResult TryRoute(string? input)
    {
        if (string.IsNullOrWhiteSpace(input))
            return NotCommand;

        var trimmed = input.Trim();
        var parts = trimmed.Split(' ', 2, StringSplitOptions.RemoveEmptyEntries);
        var cmd = parts[0];

        if (!cmd.StartsWith('/') || !Known.Contains(cmd))
            return NotCommand;

        var arg = parts.Length > 1 ? parts[1].Trim() : null;
        return cmd.ToLowerInvariant() switch
        {
            "/stop" => new LocalCommandResult
            {
                Handled = true, Command = "stop", Argument = arg,
                Reply = "⛔ 已停止当前任务计划; 未完成子任务标记为 Skipped。",
            },
            "/pause" => new LocalCommandResult
            {
                Handled = true, Command = "pause", Argument = arg,
                Reply = "⏸ 已暂停; /continue 恢复。",
            },
            "/continue" => new LocalCommandResult
            {
                Handled = true, Command = "continue", Argument = arg,
                Reply = "▶ 继续执行。",
            },
            "/status" => new LocalCommandResult
            {
                Handled = true, Command = "status",
                Reply = "📊 状态查询已受理。",
            },
            "/reset" => new LocalCommandResult
            {
                Handled = true, Command = "reset",
                Reply = "🔄 会话已重置。",
            },
            _ => NotCommand,
        };
    }

    private static readonly LocalCommandResult NotCommand = new() { Handled = false };
}
