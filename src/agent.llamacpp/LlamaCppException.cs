using System.Globalization;

namespace agent.llamacpp;


/// <summary>
/// 后端不可用 / 启动失败 / 协议失败 —— 显式失败, 不做静默兜底
/// (端口化纪律: 无设备负控必须能让调用方区分「没接」与「接错」)。
/// </summary>
public sealed class LlamaCppException : Exception
{
    public const string ProviderUnavailable = "provider_unavailable";
    public const string StartFailed = "server_start_failed";
    public const string StartTimeout = "server_start_timeout";
    public const string HttpError = "http_error";
    public const string MalformedResponse = "malformed_response";

    /// <summary>闸门拒收: prompt 不是由模型元数据模板渲染出来的（手拼 prompt）。</summary>
    public const string PromptNotTemplated = "prompt_not_templated";

    /// <summary>闸门拒收: 渲染产物为空（模板未生效 / messages 为空）。</summary>
    public const string PromptEmpty = "prompt_empty";

    /// <summary>闸门拒收: 渲染产物字面包含模型 BOS/EOS 文本（tokenizer 会再添加一次 ⇒ 双 BOS）。</summary>
    public const string PromptLiteralSpecialToken = "prompt_literal_special_token";

    public string Code { get; }

    public LlamaCppException(string code, string message, Exception? inner = null) : base(message, inner) => Code = code;
}
