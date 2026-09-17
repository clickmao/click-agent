namespace agent.core;

/// <summary>
/// 问询来源标识 —— 记录问题由谁发起、嵌套深度。
/// 关键规则: subagent 发起的问题不等于"必须问真实用户";
/// 主 agent 可按 AnswerAuthority 代答(策略性决策), 但凭据类永远只有真实用户能答。
/// </summary>
public class PromptOrigin
{
    /// <summary>发起方 agent 标识 ("main" = 主 agent, 其他 = subagent id)</summary>
    public string AskedByAgentId { get; set; } = "main";

    /// <summary>发起嵌套深度 (0 = 主 agent, 1+ = subagent 层级)。
    /// 深度过大的问询强制升级到真实用户, 防止 agent 层级间互相代答形成闭环。</summary>
    public int AskingDepth { get; set; }

    /// <summary>谁有权回答这个问题</summary>
    public AnswerAuthority Authority { get; set; } = AnswerAuthority.RealUserOnly;

    /// <summary>主 agent 代答的默认深度上限 (超过则强制问真实用户)</summary>
    public const int MaxDelegationDepth = 2;

    public static PromptOrigin Main() => new() { AskedByAgentId = "main", AskingDepth = 0 };

    public static PromptOrigin FromSubagent(string agentId, int depth) =>
        new() { AskedByAgentId = agentId, AskingDepth = Math.Max(1, depth) };
}
