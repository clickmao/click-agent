namespace agent.templates;


/// <summary>
/// 模式类型
/// </summary>
public enum PatternType
{
    /// <summary>正则表达式</summary>
    Regex,
    
    /// <summary>DSL语法</summary>
    DSL,
    
    /// <summary>JSON模式</summary>
    Json,
    
    /// <summary>自定义</summary>
    Custom
}
