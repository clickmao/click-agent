namespace agent.templates;

/// <summary>
/// 模板模型
/// </summary>
public class Template
{
    /// <summary>
    /// 唯一标识符
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>
    /// 模板名称
    /// </summary>
    public string Name { get; set; } = string.Empty;
    
    /// <summary>
    /// 分类
    /// </summary>
    public string Category { get; set; } = string.Empty;
    
    /// <summary>
    /// 版本
    /// </summary>
    public string Version { get; set; } = "1.0";
    
    /// <summary>
    /// 描述
    /// </summary>
    public string Description { get; set; } = string.Empty;
    
    /// <summary>
    /// 模式（正则表达式或模式描述）
    /// </summary>
    public string Pattern { get; set; } = string.Empty;
    
    /// <summary>
    /// 模式类型
    /// </summary>
    public PatternType PatternType { get; set; } = PatternType.Regex;
    
    /// <summary>
    /// 数据Schema（JSON Schema）
    /// </summary>
    public string? Schema { get; set; }
    
    /// <summary>
    /// 正确示例列表
    /// </summary>
    public List<CorrectExample> CorrectExamples { get; set; } = new();
    
    /// <summary>
    /// 错误示例列表
    /// </summary>
    public List<IncorrectExample> IncorrectExamples { get; set; } = new();
    
    /// <summary>
    /// 元数据
    /// </summary>
    public Dictionary<string, object> Metadata { get; set; } = new();
    
    /// <summary>
    /// 创建时间
    /// </summary>
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    
    /// <summary>
    /// 更新时间
    /// </summary>
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
    
    /// <summary>
    /// 使用次数
    /// </summary>
    public int UsageCount { get; set; }
    
    /// <summary>
    /// 成功率
    /// </summary>
    public double SuccessRate { get; set; } = 1.0;
    
    /// <summary>
    /// 标签
    /// </summary>
    public List<string> Tags { get; set; } = new();
    
    /// <summary>
    /// 作者
    /// </summary>
    public string? Author { get; set; }
    
    /// <summary>
    /// 是否启用
    /// </summary>
    public bool IsEnabled { get; set; } = true;
}
