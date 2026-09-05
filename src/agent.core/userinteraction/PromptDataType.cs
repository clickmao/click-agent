namespace agent.userinteraction;

/// <summary>
/// 问询数据类型 (v7.13): 用户回答必须满足的类型约束。
/// 覆盖常见问询面: 文本/数字/日期/选择/代码/路径/网络标识/布尔等。
/// 纯规则校验 — 校验耗时微秒级, 不调 LLM, 保证问询响应速度。
/// </summary>
public enum PromptDataType
{
    /// <summary>任意字符串 (默认)</summary>
    String,

    /// <summary>数字 (整数或小数, 支持负号/千分位)</summary>
    Number,

    /// <summary>整数</summary>
    Integer,

    /// <summary>日期 (yyyy-MM-dd / yyyy/MM/dd / yyyy年M月d日)</summary>
    Date,

    /// <summary>时间 (HH:mm / HH:mm:ss)</summary>
    Time,

    /// <summary>日期时间 (ISO 8601 / 常见组合)</summary>
    DateTime,

    /// <summary>单选 — 必须提供 Choices, 答案必须是其中之一</summary>
    Choice,

    /// <summary>多选 — 答案是 Choices 子集 (逗号/空格分隔)</summary>
    MultiChoice,

    /// <summary>布尔 (是/否/y/n/true/false)</summary>
    Boolean,

    /// <summary>文件/目录路径 (绝对或相对; 拒绝非法字符)</summary>
    Path,

    /// <summary>URL (http/https)</summary>
    Url,

    /// <summary>邮箱</summary>
    Email,

    /// <summary>代码表达式/片段 (非空即可, 长度上限放宽)</summary>
    CodeExpression,

    /// <summary>多行文本 (段落/描述)</summary>
    Multiline,

    /// <summary>IP 地址 (v4)</summary>
    IpAddress,

    /// <summary>端口号 (1-65535)</summary>
    Port,

    /// <summary>键值对 (key=value 或 key: value)</summary>
    KeyValue,
}

/// <summary>
/// 问询数据校验器 (v7.13): 纯规则、零分配热点路径。
/// 返回 (合法, 规范化值, 错误说明) — 规范化值用于偏好指纹 (b3) 与参数回填。
/// </summary>
public static class PromptDataValidator
{
    /// <summary>校验并规范化用户答案</summary>
    public static (bool Ok, string Normalized, string? Error) Validate(
        PromptDataType type, string input, IReadOnlyList<string>? choices = null)
    {
        var value = (input ?? string.Empty).Trim();
        if (value.Length == 0)
            return (false, string.Empty, "输入为空");

        switch (type)
        {
            case PromptDataType.String:
            case PromptDataType.Multiline:
                return (true, value, null);

            case PromptDataType.Integer:
                return long.TryParse(value.Replace(",", "").Replace("，", ""), out var iv) && iv >= int.MinValue && iv <= int.MaxValue
                    ? (true, iv.ToString(), null)
                    : (false, value, $"'{value}' 不是整数");

            case PromptDataType.Number:
                return double.TryParse(value.Replace(",", "").Replace("，", ""), out var nv)
                    ? (true, nv.ToString(System.Globalization.CultureInfo.InvariantCulture), null)
                    : (false, value, $"'{value}' 不是数字");

            case PromptDataType.Boolean:
                var b = value.ToLowerInvariant();
                return b is "y" or "yes" or "true" or "1" or "是" or "对" or "确认"
                    ? (true, "true", null)
                    : b is "n" or "no" or "false" or "0" or "否" or "错" or "取消"
                        ? (true, "false", null)
                        : (false, value, $"'{value}' 不是布尔值 (是/否/y/n/true/false)");

            case PromptDataType.Date:
                var d = NormalizeDate(value);
                return d != null ? (true, d, null) : (false, value, $"'{value}' 不是可识别日期 (yyyy-MM-dd / yyyy/M/d / yyyy年M月d日)");

            case PromptDataType.Time:
                return System.TimeSpan.TryParse(value, out var t)
                    ? (true, t.ToString(@"hh\:mm\:ss"), null)
                    : (false, value, $"'{value}' 不是可识别时间 (HH:mm)");

            case PromptDataType.DateTime:
                var dt = NormalizeDateTime(value);
                return dt != null ? (true, dt, null) : (false, value, $"'{value}' 不是可识别日期时间");

            case PromptDataType.Choice:
                if (choices == null || choices.Count == 0)
                    return (false, value, "Choice 类型必须提供选项列表");
                var hit = choices.FirstOrDefault(c =>
                    string.Equals(c, value, StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(c, value.TrimEnd('。', '，', ',', ' '), StringComparison.OrdinalIgnoreCase));
                return hit != null
                    ? (true, hit, null)
                    : (false, value, $"'{value}' 不在选项内: {string.Join(" / ", choices)}");

            case PromptDataType.MultiChoice:
                if (choices == null || choices.Count == 0)
                    return (false, value, "MultiChoice 类型必须提供选项列表");
                var parts = value.Split([',', '，', ' ', '、', ';', '；'], StringSplitOptions.RemoveEmptyEntries);
                var picked = new List<string>();
                foreach (var p in parts)
                {
                    var m = choices.FirstOrDefault(c => string.Equals(c, p.Trim(), StringComparison.OrdinalIgnoreCase));
                    if (m == null)
                        return (false, value, $"'{p.Trim()}' 不在选项内: {string.Join(" / ", choices)}");
                    if (!picked.Contains(m))
                        picked.Add(m);
                }
                return picked.Count > 0 ? (true, string.Join(",", picked), null) : (false, value, "未选择任何项");

            case PromptDataType.Path:
                if (value.IndexOfAny(['"', '|', '<', '>', '*', '?']) >= 0)
                    return (false, value, "路径含非法字符");
                return (true, value.Replace('\\', '/'), null);

            case PromptDataType.Url:
                return Uri.TryCreate(value, UriKind.Absolute, out var u) && u.Scheme is "http" or "https"
                    ? (true, u.ToString(), null)
                    : (false, value, $"'{value}' 不是 http(s) URL");

            case PromptDataType.Email:
                var at = value.IndexOf('@');
                return at > 0 && at < value.Length - 1 && !value.Contains(' ')
                    ? (true, value.ToLowerInvariant(), null)
                    : (false, value, $"'{value}' 不是邮箱");

            case PromptDataType.CodeExpression:
                return value.Length <= 8192
                    ? (true, value, null)
                    : (false, value, "代码片段过长 (>8192)");

            case PromptDataType.IpAddress:
                var segs = value.Split('.');
                return segs.Length == 4 && segs.All(s => byte.TryParse(s, out _))
                    ? (true, value, null)
                    : (false, value, $"'{value}' 不是 IPv4 地址");

            case PromptDataType.Port:
                return int.TryParse(value, out var port) && port is >= 1 and <= 65535
                    ? (true, port.ToString(), null)
                    : (false, value, "端口须为 1-65535");

            case PromptDataType.KeyValue:
                return value.Contains('=') || value.Contains(':') || value.Contains('：')
                    ? (true, value, null)
                    : (false, value, "须为 key=value / key: value 形式");

            default:
                return (true, value, null);
        }
    }

    private static string? NormalizeDate(string v)
    {
        // 中文日期: 2026年9月5日
        var m = System.Text.RegularExpressions.Regex.Match(v, @"^(\d{4})年(\d{1,2})月(\d{1,2})[日号]?$");
        if (m.Success)
            return $"{m.Groups[1].Value}-{int.Parse(m.Groups[2].Value):00}-{int.Parse(m.Groups[3].Value):00}";
        if (System.DateTime.TryParse(v, out var dt))
            return dt.ToString("yyyy-MM-dd");
        return null;
    }

    private static string? NormalizeDateTime(string v)
    {
        var m = System.Text.RegularExpressions.Regex.Match(v, @"^(\d{4})年(\d{1,2})月(\d{1,2})日?\s*(\d{1,2})[点时:：](\d{1,2})分?()");
        if (m.Success)
            return $"{m.Groups[1].Value}-{int.Parse(m.Groups[2].Value):00}-{int.Parse(m.Groups[3].Value):00}T{int.Parse(m.Groups[4].Value):00}:{int.Parse(m.Groups[5].Value):00}:00";
        if (System.DateTime.TryParse(v, out var dt))
            return dt.ToString("yyyy-MM-dd'T'HH:mm:ss");
        return null;
    }
}
