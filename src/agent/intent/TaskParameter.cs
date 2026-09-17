namespace agent.intent;


/// <summary>子任务参数槽 — 问询协议的拆解侧载体 (复用 AnswerAuthority 语义)</summary>
public class TaskParameter
{
    public string Name { get; set; } = string.Empty;

    /// <summary>给用户看的参数名 (如 "目标分支")</summary>
    public string DisplayName { get; set; } = string.Empty;

    /// <summary>已填充值 (null = 待澄清)</summary>
    public string? Value { get; set; }

    public bool IsRequired { get; set; } = true;

    /// <summary>敏感参数 (如 API Key) — 只走真实用户, 永不代答</summary>
    public bool IsSensitive { get; set; }

    /// <summary>推荐值 (UI 可显示为快捷选项)</summary>
    public List<string> SuggestedValues { get; set; } = new();
}
