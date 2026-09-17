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
