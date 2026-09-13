namespace agent.registry;

/// <summary>
/// v0.23.0-exp12 · R391(C7/C8): **clickproof 围栏提取器** —— 形式化断言在模型回答里的承载形态。
///
/// 单一事实源: C8 静态前缀注入的契约要求模型用 ```clickproof 围栏承载断言;
/// 消费侧有两处 (段插件 / 计划节点执行器), 二者必须用**同一套提取语义**, 否则"注入了却读不到"= 断链。
///
/// 提取语义 (逐条可证伪):
///   1) 只认**行首**围栏 (避免行内反引号误匹配), 语言标识大小写不敏感且必须整词等于 clickproof。
///   2) 返回围栏内正文 (不含围栏行本身), 统一 CRLF→LF。
///   3) 围栏未闭合 (截断) ⇒ 返回**剩余正文**而不是 null —— 截断不可被当作"没声明"而静默放行;
///      残缺内容会落进契约解析器, 由它按"残缺不放行"处置。
///   4) 无围栏 ⇒ null (调用方自行决定回退路径)。
/// 零正则 / 零 shell / 零反射 / 零 token。
/// </summary>
public static class ClickProofFence
{
    /// <summary>围栏语言标识 (与 <c>FormalPromptContract.FenceLanguage</c> 同值, 由机检保证一致)。</summary>
    public const string Language = "clickproof";

    /// <summary>提取首个 clickproof 围栏正文; 无围栏 ⇒ null。</summary>
    public static string? Extract(string? text)
    {
        if (string.IsNullOrWhiteSpace(text)) return null;

        var lines = text.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n');
        var start = -1;

        for (var i = 0; i < lines.Length; i++)
        {
            var t = lines[i].Trim();
            if (start < 0)
            {
                if (IsOpenFence(t)) start = i + 1;
                continue;
            }

            if (t.StartsWith("```", StringComparison.Ordinal))
                return string.Join("\n", lines[start..i]);
        }

        // 未闭合: 返回剩余正文 (截断 ⇒ 交契约解析器判残缺, 不静默吞)。
        return start >= 0 ? string.Join("\n", lines[start..]) : null;
    }

    /// <summary>提取并规整: 去首尾空行; 结果为空 ⇒ null。</summary>
    public static string? ExtractTrimmed(string? text)
    {
        var body = Extract(text);
        if (body is null) return null;
        body = body.Trim('\n', ' ', '\t');
        return body.Length == 0 ? null : body;
    }

    /// <summary>是否形如 ```` ```clickproof ```` 的开围栏 (语言标识整词匹配)。</summary>
    public static bool IsOpenFence(string trimmedLine)
    {
        if (trimmedLine.Length <= 3 || !trimmedLine.StartsWith("```", StringComparison.Ordinal)) return false;
        var lang = trimmedLine[3..].Trim();
        return lang.Equals(Language, StringComparison.OrdinalIgnoreCase);
    }
}
