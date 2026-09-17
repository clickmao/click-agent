namespace agent.core;

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
