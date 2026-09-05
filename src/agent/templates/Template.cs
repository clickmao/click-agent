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

/// <summary>
/// 正确示例
/// </summary>
public class CorrectExample
{
    /// <summary>
    /// 唯一标识符
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>
    /// 输入
    /// </summary>
    public string Input { get; set; } = string.Empty;
    
    /// <summary>
    /// 期望输出
    /// </summary>
    public string Output { get; set; } = string.Empty;
    
    /// <summary>
    /// 描述
    /// </summary>
    public string Description { get; set; } = string.Empty;
    
    /// <summary>
    /// 标签
    /// </summary>
    public List<string> Tags { get; set; } = new();
    
    /// <summary>
    /// 使用次数
    /// </summary>
    public int UsageCount { get; set; }
    
    /// <summary>
    /// 成功次数
    /// </summary>
    public int SuccessCount { get; set; }
    
    /// <summary>
    /// 计算成功率
    /// </summary>
    public double SuccessRate => UsageCount > 0 ? (double)SuccessCount / UsageCount : 0;
}

/// <summary>
/// 错误示例
/// </summary>
public class IncorrectExample
{
    /// <summary>
    /// 唯一标识符
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>
    /// 错误输入
    /// </summary>
    public string Input { get; set; } = string.Empty;
    
    /// <summary>
    /// 错误输出
    /// </summary>
    public string IncorrectOutput { get; set; } = string.Empty;
    
    /// <summary>
    /// 解释
    /// </summary>
    public string Explanation { get; set; } = string.Empty;
    
    /// <summary>
    /// 正确方法
    /// </summary>
    public string CorrectApproach { get; set; } = string.Empty;
    
    /// <summary>
    /// 标签
    /// </summary>
    public List<string> Tags { get; set; } = new();
}

/// <summary>
/// 模板查询
/// </summary>
public class TemplateQuery
{
    /// <summary>
    /// 名称（模糊匹配）
    /// </summary>
    public string? Name { get; set; }
    
    /// <summary>
    /// 分类
    /// </summary>
    public string? Category { get; set; }
    
    /// <summary>
    /// 模式（模糊匹配）
    /// </summary>
    public string? Pattern { get; set; }
    
    /// <summary>
    /// 标签
    /// </summary>
    public List<string>? Tags { get; set; }
    
    /// <summary>
    /// 是否启用
    /// </summary>
    public bool? IsEnabled { get; set; }
    
    /// <summary>
    /// 最小成功率
    /// </summary>
    public double? MinSuccessRate { get; set; }
    
    /// <summary>
    /// 跳过数量
    /// </summary>
    public int Skip { get; set; }
    
    /// <summary>
    /// 获取数量
    /// </summary>
    public int Take { get; set; } = 20;
    
    /// <summary>
    /// 排序字段
    /// </summary>
    public string SortBy { get; set; } = "UsageCount";
    
    /// <summary>
    /// 是否降序
    /// </summary>
    public bool Descending { get; set; } = true;
}

/// <summary>
/// 模板匹配结果
/// </summary>
public class TemplateMatchResult
{
    /// <summary>
    /// 匹配的模板
    /// </summary>
    public Template Template { get; set; } = null!;
    
    /// <summary>
    /// 匹配分数
    /// </summary>
    public double Score { get; set; }
    
    /// <summary>
    /// 匹配的标签
    /// </summary>
    public List<string> MatchedTags { get; set; } = new();
    
    /// <summary>
    /// 匹配原因
    /// </summary>
    public string Reason { get; set; } = string.Empty;
    
    /// <summary>
    /// 是否推荐
    /// </summary>
    public bool IsRecommended => Score >= 0.7;
}

/// <summary>
/// 应用上下文
/// </summary>
public class ApplyContext
{
    /// <summary>
    /// 输入数据
    /// </summary>
    public Dictionary<string, object> Inputs { get; set; } = new();
    
    /// <summary>
    /// 配置选项
    /// </summary>
    public Dictionary<string, object> Options { get; set; } = new();
    
    /// <summary>
    /// 用户ID
    /// </summary>
    public string? UserId { get; set; }
    
    /// <summary>
    /// 会话ID
    /// </summary>
    public string? SessionId { get; set; }
}
