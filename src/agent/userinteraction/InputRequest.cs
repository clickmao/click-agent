namespace agent.userinteraction;


/// <summary>
/// 输入请求
/// </summary>
public class InputRequest
{
    /// <summary>
    /// 提示
    /// </summary>
    public string Prompt { get; set; } = string.Empty;
    
    /// <summary>
    /// 默认值
    /// </summary>
    public string? DefaultValue { get; set; }
    
    /// <summary>
    /// 是否多行
    /// </summary>
    public bool MultiLine { get; set; }
    
    /// <summary>
    /// 占位符
    /// </summary>
    public string? Placeholder { get; set; }
    
    /// <summary>
    /// 验证器
    /// </summary>
    public Func<string, (bool IsValid, string? ErrorMessage)>? Validator { get; set; }
}
