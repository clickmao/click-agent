using agent.session;
using Microsoft.Extensions.Logging;

namespace agent.subagent;


/// <summary>隔离任务执行结果 (I.4 输出边界: 带标记返回主对话, 不混入主任务计划)。</summary>
public sealed class IsolatedTaskResult
{
    public string IsolatedSessionId { get; set; } = string.Empty;

    /// <summary>用户原话 (无关新提问)</summary>
    public string TaskText { get; set; } = string.Empty;

    /// <summary>隔离 agent 回答</summary>
    public string? Answer { get; set; }

    public bool Success { get; set; }

    public string? Error { get; set; }

    /// <summary>执行耗时毫秒</summary>
    public long ElapsedMs { get; set; }

    /// <summary>判定审计 (无关分与理由)</summary>
    public string RelevanceReason { get; set; } = string.Empty;
}
