namespace agent.userinteraction;


/// <summary>
/// 托管级别 —— 决定敏感操作问询策略 (凭据问询不受此影响, 永远必须真实用户回答):
/// Full = 全托管, 敏感操作按策略自动批准并记录审计;
/// Standard = 删除/执行进程/系统配置问询, 创建/网络放行;
/// Strict = 所有敏感操作都问询。
/// </summary>
public enum SupervisionLevel
{
    /// <summary>全托管: 敏感操作自动批准并记录审计日志</summary>
    Full,

    /// <summary>标准: 创建/网络放行, 删除/执行进程/系统配置问询</summary>
    Standard,

    /// <summary>严格: 所有敏感操作都问询</summary>
    Strict,
}
