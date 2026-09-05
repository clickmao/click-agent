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

/// <summary>
/// 问询指纹: 把一次问询规范化为可复用的"模式键"。
/// 指纹只由 问题意图词 + 数据类型 构成 — 刻意排除本次具体输入值/凭据, 防"偏好"退化成"缓存"。
/// </summary>
public static class ClarificationFingerprint
{
    /// <summary>意图语义词表: 参数名/问题 → 语义类别 (同一类别即"类似问题")</summary>
    private static readonly (string[] Words, string Category)[] SemanticCategories =
    [
        (["路径", "文件", "目录", "path", "file", "directory", "保存到", "输出到"], "path"),
        (["数量", "多少", "几个", "次数", "count", "limit", "条数"], "quantity"),
        (["日期", "时间", "date", "time", "截止", "开始", "结束"], "datetime"),
        (["格式", "format", "类型", "type", "编码"], "format"),
        (["语言", "language", "翻译", "lang"], "language"),
        (["确认", "是否", "要不要", "启用", "禁用", "enable", "disable"], "confirm"),
        (["来源", "数据源", "哪个", "source", "基于"], "source"),
        (["目标", "对象", "指向", "target"], "target"),
        (["名字", "名称", "命名", "name", "标题", "title"], "naming"),
        (["地址", "url", "链接", "endpoint", "host"], "endpoint"),
    ];

    /// <summary>从问询条目构指纹 (规范化: 小写、去数字/引号)</summary>
    public static string Build(string question, string parameterName, PromptDataType dataType)
    {
        var text = $"{parameterName} {question}".ToLowerInvariant();
        // 去掉具体值痕迹 (数字/引号内容) — 指纹是"问的是什么类型的事", 不是"问了什么值"
        text = System.Text.RegularExpressions.Regex.Replace(text, @"""[^""]*""|'[^']*'|「[^」]*」|\d+", " ");
        var category = SemanticCategories.FirstOrDefault(sc => sc.Words.Any(w => text.Contains(w))).Category
            ?? dataType switch
            {
                PromptDataType.Path => "path",
                PromptDataType.Choice or PromptDataType.MultiChoice => "choice",
                PromptDataType.Date or PromptDataType.Time or PromptDataType.DateTime => "datetime",
                PromptDataType.Boolean => "confirm",
                PromptDataType.Number or PromptDataType.Integer => "quantity",
                PromptDataType.Url or PromptDataType.Email => "endpoint",
                _ => "general",
            };
        return $"{category}:{dataType.ToString().ToLowerInvariant()}";
    }

    /// <summary>
    /// 从用户答案提取"偏好模式" (规范化特征 — 绝不存原值)。
    /// 返回 null = 该答案不入偏好 (敏感/一次性/无模式)。
    /// </summary>
    public static string? ExtractPattern(PromptDataType dataType, string normalizedAnswer)
    {
        var v = normalizedAnswer.Trim();
        if (v.Length == 0)
            return null;

        return dataType switch
        {
            // 路径: 绝对/相对 + 扩展名族
            PromptDataType.Path => v.StartsWith('/') || v.StartsWith('~') || (v.Length > 1 && v[1] == ':')
                ? "absolute"
                : "relative",
            // 布尔: 倾向
            PromptDataType.Boolean => v == "true" ? "prefer-yes" : "prefer-no",
            // 数字: 量级 (不记具体数)
            PromptDataType.Number or PromptDataType.Integer => Math.Abs(double.TryParse(v, out var n) ? n : 0) switch
            {
                >= 1000 => "magnitude:large",
                >= 10 => "magnitude:medium",
                _ => "magnitude:small",
            },
            // 日期: 风格
            PromptDataType.Date or PromptDataType.DateTime => v.Contains('T') ? "iso-datetime" : "iso-date",
            // URL/邮箱: 域特征过细, 不记 (易引入隐私) — 一次性特征不入库
            PromptDataType.Url or PromptDataType.Email => null,
            // 自由文本: 无稳定模式
            PromptDataType.String or PromptDataType.Multiline or PromptDataType.CodeExpression => null,
            _ => "answered",
        };
    }
}

/// <summary>
/// 偏好库 JSON 契约 (source-gen, AOT 安全)。
/// </summary>
[JsonSerializable(typeof(List<ClarificationPreference>))]
[JsonSourceGenerationOptions(WriteIndented = true, PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase)]
internal sealed partial class ClarificationPreferenceJsonContext : System.Text.Json.Serialization.JsonSerializerContext
{
}
