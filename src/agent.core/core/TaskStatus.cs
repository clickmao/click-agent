namespace agent.core;


/// <summary>
/// 任务状态
/// </summary>
public enum TaskStatus
{
    /// <summary>待处理</summary>
    Pending,
    
    /// <summary>运行中</summary>
    Running,
    
    /// <summary>等待依赖</summary>
    WaitingForDependencies,
    
    /// <summary>完成</summary>
    Completed,
    
    /// <summary>失败</summary>
    Failed,
    
    /// <summary>已取消</summary>
    Cancelled,
    
    /// <summary>超时</summary>
    Timeout
}
