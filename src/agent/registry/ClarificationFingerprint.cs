using System.Text.Json.Serialization;
using agent.intent;
using agent.core;

namespace agent.registry;


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
