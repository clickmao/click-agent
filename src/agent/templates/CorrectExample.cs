namespace agent.templates;


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
