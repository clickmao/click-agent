namespace agent.core;


/// <summary>
/// 问询服务契约 —— 所有"需要用户决定/提供才能继续"的阻塞式交互。
/// 实现方必须等待回复 (真实用户或主 agent 代答) 后才返回;
/// 返回值必须带 PromptAnswerSource 标明实际回答者。
/// </summary>
public interface IUserPromptService
{
    /// <summary>
    /// 凭据问询: 等待回复。Authority 恒为 RealUserOnly —— 主 agent 无权代答。
    /// 用户拒绝/超时返回 null, 调用方必须走声明的降级路径。
    /// </summary>
    Task<Dictionary<string, string>?> RequestCredentialsAsync(
        CredentialRequest request, CancellationToken ct = default);

    /// <summary>
    /// 敏感操作审批: 按 Origin.Authority 与托管级别路由 ——
    /// 主 agent 代答 (MainAgentDelegate) 或升级到真实用户 (RealUser)。
    /// </summary>
    Task<OperationApprovalResult> RequestOperationApprovalAsync(
        SensitiveOperationRequest request, CancellationToken ct = default);

    /// <summary>当前托管级别 (来自配置 Agent:Supervision)</summary>
    SupervisionLevel Supervision { get; }

    /// <summary>
    /// agent 间问询静默 (v7.13): true 时 MainAgentAllowed 的问询不打印到控制台,
    /// 由主 agent 静默代答 (空值占位 + 审计), 用户界面零打扰。凭据/敏感项不受此开关影响。
    /// </summary>
    bool SilentInterAgent { get; set; }
}
