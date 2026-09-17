namespace agent.templates;


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
