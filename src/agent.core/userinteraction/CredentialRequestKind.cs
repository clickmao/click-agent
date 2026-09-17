namespace agent.userinteraction;


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
