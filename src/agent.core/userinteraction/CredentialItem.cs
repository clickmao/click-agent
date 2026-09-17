namespace agent.userinteraction;


/// <summary>凭据问询中的单个条目</summary>
public class CredentialItem
{
    /// <summary>条目键 (如 "apiKey" / "endpoint"), 与配置键对应</summary>
    public string Key { get; set; } = string.Empty;

    /// <summary>给用户看的条目名 (如 "API Key")</summary>
    public string DisplayName { get; set; } = string.Empty;

    /// <summary>是否必须 (false = 可留空跳过)</summary>
    public bool Required { get; set; } = true;

    /// <summary>是否敏感值 (输入时打码, 存储时仅入本地凭据文件)</summary>
    public bool Sensitive { get; set; }

    /// <summary>R375 (exp2 P0-3): 答案数据类型 ("text"/"choice"/"multi_choice"/"number"/"boolean"/...); 前端据此渲染控件</summary>
    public string? DataType { get; set; }

    /// <summary>R375 (exp2 P0-3): 完整选项列表 (choice/multi_choice 必须给全) —— 不得只把菜单拼进 DisplayName 文本</summary>
    public List<CredentialChoice> Choices { get; set; } = new();

    /// <summary>R375: 多选标志 (DataType=multi_choice)</summary>
    public bool MultiSelect { get; set; }

    /// <summary>R375: 默认值/推荐值 (前端可预选; 用户可直接采用)</summary>
    public string? DefaultValue { get; set; }
}
