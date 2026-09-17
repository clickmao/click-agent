using System.Text.Json.Serialization;
using agent.intent;
using agent.userinteraction;

namespace agent.registry;

/// <summary>
/// 问询偏好库 (v7.13, 用户钦定): 记录用户在某类问询中的"偏好" —
/// 不是本次问询的凭据, 也不是用户输入的原值 — 供下次类似问题复用。
///
/// 铁律:
///   ① 凭据绝不入偏好 (Kind=ApiKey / Sensitive=true 的回答一条不记);
///   ② 不存原始答案 — 存规范化后的"模式特征" (choice→选项偏好序, path→绝对/相对, number→量级, bool→倾向);
///   ③ 指纹 = 规范化问询模式 (意图+参数语义+数据类型), 同指纹才复用 — 防跨类污染;
///   ④ JSON source-gen 序列化 (AOT 零反射)。
/// </summary>
public sealed class ClarificationPreference
{
    /// <summary>问询指纹: 规范化后的问询模式 (见 ClarificationFingerprint.Build)</summary>
    public string Fingerprint { get; set; } = string.Empty;

    /// <summary>数据类型名 (序列化用字符串 — AOT 无反射枚举转换)</summary>
    public string DataTypeName { get; set; } = nameof(PromptDataType.String);

    /// <summary>数据类型 (同类型才可比; 非序列化属性)</summary>
    [JsonIgnore]
    public PromptDataType DataType
    {
        get => Enum.TryParse<PromptDataType>(DataTypeName, out var t) ? t : PromptDataType.String;
        set => DataTypeName = value.ToString();
    }

    /// <summary>偏好特征 (规范化, 非原值): 如 "absolute-path" / "choice:第2项" / "bool:true" / "magnitude:small"</summary>
    public string PreferredPattern { get; set; } = string.Empty;

    /// <summary>Choice 类型: 完整的选项偏好序 (被选过的选项前移 — 只记顺序, 不记原文入档值)</summary>
    public List<string> ChoiceOrder { get; set; } = new();

    /// <summary>命中次数 (复用次数越多权重越高)</summary>
    public int HitCount { get; set; }

    /// <summary>最近更新 (UTC ticks)</summary>
    public long UpdatedAt { get; set; }
}
