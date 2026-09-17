namespace agent.intent;


/// <summary>澄清类型 flag 常量 (序列化友好; 凭据类沿用 CredentialRequestKind 语义字符串)</summary>
public static class ClarificationKinds
{
    public const string MissingParameter = "missing_parameter";
    public const string ApiKey = "api_key";
    public const string Endpoint = "endpoint";
    public const string ExternalToolPath = "external_tool_path";
    public const string AmbiguousIntent = "ambiguous_intent";
}
