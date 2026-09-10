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
    /// <summary>v0.18.0 (R339): V2 前置特判的指令 (TryRoute 之前被 V2 拦截层处理, router 只落地) —
    /// 一致性审计测试引用此集, 豁免"Known 无 switch 臂"检查 (防隐式魔法)。</summary>
    public static readonly string[] PreRoutedCommands =
    {
        "/model", "/balance", "/official-key", "/log",  // 注释: V2 拦截层特判, router 落地 (v7.15)
    };

    /// <summary>已知指令全集 (审计/UI 用; 含 PreRouted)。</summary>
    public static IReadOnlyCollection<string> KnownCommands => Known;

    private static readonly HashSet<string> Known = new(StringComparer.OrdinalIgnoreCase)
    {
        "/model", "/balance",  // v7.15 模型队列: 切换/查询 (V2 拦截层特判, router 落地)
        "/official-key",  // v7.15 需求1: 官方通道 key 注入 (⚠ 指令名代拟 — 用户未定名; 内存态)
        "/log",  // v7.15 日志四通道: /log dump → MemoryLogBuffer 存档文件 (JSON 行)
        "/stop", "/continue", "/pause", "/status", "/reset",
        "/skills", "/skills-only", "/skills-exclude",  // v0.16.0-c/b: skills 查询/动态 whitelist/blacklist (V2 特判渲染)
        "/staged", "/approve", "/reject", "/cleanup",  // v0.17.1 (R335): 离线变更审批 (V2 特判渲染)
        "/activity",  // v0.17.2-a (R336): 活动 agent/任务查询 (V2 特判渲染)
        "/llm-service", // v0.20.2 (R345): llm-manager/worker 状态观测 (V2 特判渲染)
        "/schedule-run",  // v0.17.2-b/c (R337): 条件定时执行 py 插件脚本 (V2 特判渲染)
        "/git",  // v0.18.0 G1 (R338): git 操作 status/diff/commit/push (凭据卫生: 一次性 URL 不落 config)
        "/help",  // v0.11.0 R86: 帮助菜单本地应答 — 原未注册送 LLM 浪费一轮
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
            "/help" => new LocalCommandResult
            {
                Handled = true, Command = "help", Argument = arg,
                Reply = "📖 本地命令: /status /session <uid> [n] /plan /stop /reset /model /balance /log dump /official-key /help — 其余输入直接对话。",
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
            // v0.16.0-c/b: skills 查询与动态过滤 — Handled=true, V2 特判渲染 (需 SkillRegistry 访问)
            "/skills" => new LocalCommandResult
            {
                Handled = true, Command = "skills",
            },
            "/skills-only" => new LocalCommandResult
            {
                Handled = true, Command = "skills-only", Argument = arg,
            },
            "/skills-exclude" => new LocalCommandResult
            {
                Handled = true, Command = "skills-exclude", Argument = arg,
            },
            // v0.17.1: staged approval — Handled=true, V2 特判渲染 (需 StagedFileStore/ApprovalController)
            "/staged" => new LocalCommandResult
            {
                Handled = true, Command = "staged", Argument = arg,
            },
            "/approve" => new LocalCommandResult
            {
                Handled = true, Command = "approve", Argument = arg,
            },
            "/reject" => new LocalCommandResult
            {
                Handled = true, Command = "reject", Argument = arg,
            },
            "/cleanup" => new LocalCommandResult
            {
                Handled = true, Command = "cleanup", Argument = arg,
            },
            "/activity" => new LocalCommandResult
            {
                Handled = true, Command = "activity",
            },
            // v0.20.2: llm-manager/worker 状态 (V2 特判渲染, 需 LlmServiceStatus)
            "/llm-service" => new LocalCommandResult
            {
                Handled = true, Command = "llm-service",
            },
            // v0.17.2-b/c: 条件定时执行 py 插件脚本 (V2 特判渲染, 需 ScriptPluginRunner/ConditionalScriptScheduler)
            "/schedule-run" => new LocalCommandResult
            {
                Handled = true, Command = "schedule-run", Argument = arg,
            },
            "/git" => new LocalCommandResult
            {
                Handled = true, Command = "git", Argument = arg,
            },
            _ => NotCommand,
        };
    }

    private static readonly LocalCommandResult NotCommand = new() { Handled = false };
}
