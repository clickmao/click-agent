namespace agent.userinteraction;


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
