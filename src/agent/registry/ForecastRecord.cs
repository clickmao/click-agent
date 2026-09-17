using System.Text.Json;

namespace agent.registry;

/// <summary>
/// 下轮任务预估 (v7.11): 任务循环完成后生成, 落本地文件;
/// 关闭程序后, 下次对话通过读回预估来指示 LLM 用户本轮输入倾向。
/// 每个主/子 agent 独立一份 — 按 AgentRegistry UID 隔离在工作目录下。
/// </summary>
public class ForecastRecord
{
    /// <summary>所属 agent UID (隔离键)</summary>
    public string AgentUid { get; set; } = string.Empty;

    /// <summary>本轮任务摘要 (供下轮延续判断)</summary>
    public string TaskSummary { get; set; } = string.Empty;

    /// <summary>本轮主意图 (agent.intent 常量)</summary>
    public string LastIntent { get; set; } = string.Empty;

    /// <summary>下轮输入倾向 (规则推断, 非编造)</summary>
    public string Tendency { get; set; } = string.Empty;

    /// <summary>延续提示 (拼进 prompt header 的一句话)</summary>
    public string ContinuationHint { get; set; } = string.Empty;

    /// <summary>本轮是否像任务的中间态 (用户大概率会继续)</summary>
    public bool LikelyContinues { get; set; }

    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

    /// <summary>累计完成的轮次 (同一 agent 的会话计数)</summary>
    public int TurnCount { get; set; }
}
