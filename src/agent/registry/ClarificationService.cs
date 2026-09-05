using agent.intent;
using agent.userinteraction;

namespace agent.registry;

/// <summary>
/// 问询节点与问询服务打通 (v7.11): TaskPlan 的 Clarification 节点
/// → IUserPromptService (凭据/审批) 的实际交互执行器。
/// Authority=RealUserOnly → RequestCredentialsAsync (真实用户, 主 agent 不代答);
/// Authority=MainAgentAllowed → 按 SupervisionLevel 决定代答或问用户。
/// </summary>
public class ClarificationService
{
    private readonly IUserPromptService _prompts;

    public ClarificationService(IUserPromptService prompts) => _prompts = prompts;

    /// <summary>
    /// 执行一个澄清条目: 向用户/主 agent 要答案, 回填参数槽。
    /// 返回 false = 用户拒绝或超时 (节点保持等待, 不伪造答案)。
    /// </summary>
    public async Task<bool> ResolveAsync(TaskPlan plan, ClarificationItem item, CancellationToken ct = default)
    {
        if (item.Authority == "RealUserOnly")
        {
            // 敏感参数 (API Key 等): 只有真实用户能答
            var request = new CredentialRequest
            {
                Kind = MapKind(item.Kind),
                ServiceName = "task-plan",
                Purpose = item.Question,
                Items =
                {
                    new CredentialItem
                    {
                        Key = item.ParameterName,
                        DisplayName = item.ParameterName,
                        Required = true,
                        Sensitive = item.Kind == ClarificationKinds.ApiKey,
                    },
                },
            };
            var answers = await _prompts.RequestCredentialsAsync(request, ct);
            if (answers == null || !answers.TryGetValue(item.ParameterName, out var value))
                return false;

            TaskPlanBuilder.ApplyClarificationAnswer(plan, item.NodeId, item.ParameterName, value);
            return true;
        }

        // 非敏感参数: 全托管 (Full) 由主 agent 用推荐值代答并记录; 其余问用户
        if (_prompts.Supervision == SupervisionLevel.Full && item.SuggestedValues.Count > 0)
        {
            TaskPlanBuilder.ApplyClarificationAnswer(plan, item.NodeId, item.ParameterName, item.SuggestedValues[0]);
            return true;
        }

        // Standard/Strict: 非敏感也走真实用户 (无代答凭据风险, 但参数影响执行结果)
        var req = new CredentialRequest
        {
            Kind = CredentialRequestKind.ApiKeyAndEndpoint,
            ServiceName = "task-plan",
            Purpose = item.Question,
            Items =
            {
                new CredentialItem
                {
                    Key = item.ParameterName,
                    DisplayName = item.ParameterName,
                    Required = true,
                    Sensitive = false,
                },
            },
        };
        var resp = await _prompts.RequestCredentialsAsync(req, ct);
        if (resp == null || !resp.TryGetValue(item.ParameterName, out var v))
            return false;

        TaskPlanBuilder.ApplyClarificationAnswer(plan, item.NodeId, item.ParameterName, v);
        return true;
    }

    private static CredentialRequestKind MapKind(string kind) => kind switch
    {
        ClarificationKinds.ApiKey => CredentialRequestKind.ApiKey,
        ClarificationKinds.Endpoint => CredentialRequestKind.Endpoint,
        ClarificationKinds.ExternalToolPath => CredentialRequestKind.ExternalToolPath,
        _ => CredentialRequestKind.ApiKeyAndEndpoint,
    };
}
