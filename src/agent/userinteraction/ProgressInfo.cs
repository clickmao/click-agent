namespace agent.userinteraction;


/// <summary>
/// 进度信息
/// </summary>
public class ProgressInfo
{
    /// <summary>
    /// 进度百分比
    /// </summary>
    public double Progress { get; set; }
    
    /// <summary>
    /// 状态消息
    /// </summary>
    public string? Status { get; set; }
    
    /// <summary>
    /// 当前步骤
    /// </summary>
    public string? CurrentStep { get; set; }
    
    /// <summary>
    /// 总步骤数
    /// </summary>
    public int TotalSteps { get; set; }
    
    /// <summary>
    /// 预估剩余时间
    /// </summary>
    public TimeSpan? EstimatedRemaining { get; set; }
}
