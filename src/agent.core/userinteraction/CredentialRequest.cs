namespace agent.core;


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

    /// <summary>R375 (exp2 P1-4): 问询超时秒数; null = 实现默认 (console 实现无超时)</summary>
    public int? TimeoutSeconds { get; set; }

    /// <summary>问询来源 (谁在等这个答案)</summary>
    public PromptOrigin Origin { get; set; } = PromptOrigin.Main();
}
