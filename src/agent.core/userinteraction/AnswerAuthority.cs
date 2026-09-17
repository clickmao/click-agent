namespace agent.userinteraction;


/// <summary>
/// 回答权威模型:
/// RealUserOnly —— 凭据(API Key)、不可逆操作, 主 agent 无权代答, 必须等真实用户;
/// MainAgentAllowed —— 作用域内的策略性决策, 主 agent 可按托管级别代答(记录在案)。
/// </summary>
public enum AnswerAuthority
{
    /// <summary>仅真实用户可答 (主 agent 绝不能编造/自动填充)</summary>
    RealUserOnly,

    /// <summary>主 agent 可按托管级别策略代答</summary>
    MainAgentAllowed,
}
