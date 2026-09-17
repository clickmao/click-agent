namespace agent.core;


/// <summary>回答来源 —— 审计与程序底层路由的关键 flag</summary>
public enum PromptAnswerSource
{
    /// <summary>真实用户亲自回答</summary>
    RealUser,

    /// <summary>主 agent 按策略代答 (subagent 的问题被主 agent 决策)</summary>
    MainAgentDelegate,

    /// <summary>全托管策略自动批准</summary>
    AutoApproved,

    /// <summary>用户/主 agent 拒绝</summary>
    Denied,

    /// <summary>超时未答</summary>
    Timeout,
}
