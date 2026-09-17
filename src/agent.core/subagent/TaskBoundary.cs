using agent.core;
using TaskStatus = agent.core.TaskStatus;

namespace agent.subagent;


/// <summary>
/// 任务边界定义
/// </summary>
public class TaskBoundary
{
    /// <summary>
    /// 任务ID
    /// </summary>
    public string TaskId { get; set; } = string.Empty;
    
    /// <summary>
    /// 输入需求
    /// </summary>
    public List<string> InputRequirements { get; set; } = new();
    
    /// <summary>
    /// 依赖
    /// </summary>
    public List<string> Dependencies { get; set; } = new();
    
    /// <summary>
    /// 输出文件
    /// </summary>
    public List<string> OutputFiles { get; set; } = new();
    
    /// <summary>
    /// 输出模式
    /// </summary>
    public List<string> OutputPatterns { get; set; } = new();
    
    /// <summary>
    /// 最大Token数
    /// </summary>
    public long MaxTokens { get; set; } = 8000;
    
    /// <summary>
    /// 超时时间（毫秒）
    /// </summary>
    public long TimeoutMs { get; set; } = 300000;
    
    /// <summary>
    /// 约束条件
    /// </summary>
    public Dictionary<string, object> Constraints { get; set; } = new();
    
    /// <summary>
    /// 上下文提示
    /// </summary>
    public Dictionary<string, object> ContextHints { get; set; } = new();
}
