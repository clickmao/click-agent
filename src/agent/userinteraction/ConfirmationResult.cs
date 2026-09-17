namespace agent.userinteraction;


/// <summary>
/// 确认结果
/// </summary>
public class ConfirmationResult
{
    /// <summary>
    /// 请求ID
    /// </summary>
    public string RequestId { get; set; } = string.Empty;
    
    /// <summary>
    /// 是否批准
    /// </summary>
    public bool Approved { get; set; }
    
    /// <summary>
    /// 选择的选项ID
    /// </summary>
    public string? SelectedOptionId { get; set; }
    
    /// <summary>
    /// 用户输入（如果有）
    /// </summary>
    public string? UserInput { get; set; }
    
    /// <summary>
    /// 时间戳
    /// </summary>
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    
    /// <summary>
    /// 超时
    /// </summary>
    public bool TimedOut { get; set; }
}
