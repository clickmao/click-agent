namespace agent.userinteraction;

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

/// <summary>操作审批结果</summary>
public class OperationApprovalResult
{
    public bool Approved { get; init; }
    public PromptAnswerSource AnsweredBy { get; init; }
    public string? Reason { get; init; }
}

/// <summary>
/// 凭据/配置问询请求 —— 服务需要 API Key、端点等运行要素而配置缺失时,
/// 主动向用户说明用途并请求提供。
/// </summary>
public class CredentialRequest
{
    /// <summary>请求 ID</summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();

    /// <summary>问询类型 flag —— 程序底层按类型路由处理/记录/审计</summary>
    public CredentialRequestKind Kind { get; set; }

    /// <summary>服务标识 (如 "bocha" / "searxng" / "openai")</summary>
    public string ServiceName { get; set; } = string.Empty;

    /// <summary>
    /// 问询作用说明 (给用户看): 为什么需要、用在哪个环节、不提供会怎样。
    /// 必须具体, 禁止"需要配置 XXX"这种无上下文的提示。
    /// </summary>
    public string Purpose { get; set; } = string.Empty;

    /// <summary>请求的具体条目 (Key / 端点 / 其他)</summary>
    public List<CredentialItem> Items { get; set; } = new();

    /// <summary>已知/推荐的默认值, 用户可直接采用或改填</summary>
    public string? SuggestedValue { get; set; }

    /// <summary>不提供时的降级行为说明 (如 "将跳过此源, 使用 Bing CN 兜底")</summary>
    public string? FallbackNote { get; set; }

    /// <summary>问询来源 (谁在等这个答案)</summary>
    public PromptOrigin Origin { get; set; } = PromptOrigin.Main();
}

/// <summary>凭据问询中的单个条目</summary>
public class CredentialItem
{
    /// <summary>条目键 (如 "apiKey" / "endpoint"), 与配置键对应</summary>
    public string Key { get; set; } = string.Empty;

    /// <summary>给用户看的条目名 (如 "API Key")</summary>
    public string DisplayName { get; set; } = string.Empty;

    /// <summary>是否必须 (false = 可留空跳过)</summary>
    public bool Required { get; set; } = true;

    /// <summary>是否敏感值 (输入时打码, 存储时仅入本地凭据文件)</summary>
    public bool Sensitive { get; set; }
}

/// <summary>问询类型 flag</summary>
public enum CredentialRequestKind
{
    /// <summary>API Key 等凭据缺失</summary>
    ApiKey,

    /// <summary>服务端点/地址未知</summary>
    Endpoint,

    /// <summary>凭据 + 端点都缺</summary>
    ApiKeyAndEndpoint,

    /// <summary>外部程序路径未知 (如 webreaper CLI)</summary>
    ExternalToolPath,
}

/// <summary>
/// 敏感操作问询请求 —— 非全托管模式下, 删除文件、执行外部程序等
/// 不可逆或影响系统的操作必须先获得批准。
/// </summary>
public class SensitiveOperationRequest
{
    /// <summary>请求 ID</summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();

    /// <summary>操作类型 flag</summary>
    public SensitiveOperationKind Kind { get; set; }

    /// <summary>操作摘要 (给用户看, 一句话)</summary>
    public string Summary { get; set; } = string.Empty;

    /// <summary>完整细节: 目标路径/命令行/影响范围</summary>
    public string Details { get; set; } = string.Empty;

    /// <summary>发起方组件</summary>
    public string Initiator { get; set; } = string.Empty;

    /// <summary>问询来源 (哪个 agent 层级在等这个批准)</summary>
    public PromptOrigin Origin { get; set; } = PromptOrigin.Main();
}

/// <summary>敏感操作类型 flag</summary>
public enum SensitiveOperationKind
{
    /// <summary>创建文件/目录</summary>
    CreateFile,

    /// <summary>删除文件/目录 (不可逆)</summary>
    DeleteFile,

    /// <summary>修改/覆盖既有文件</summary>
    ModifyFile,

    /// <summary>执行外部程序/进程</summary>
    ExecuteProcess,

    /// <summary>网络请求到非白名单地址</summary>
    ExternalNetwork,

    /// <summary>写入系统配置 (env/全局配置)</summary>
    SystemConfig,
}

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
}
