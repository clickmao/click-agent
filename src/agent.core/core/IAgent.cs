namespace agent.core;

/// <summary>
/// Agent核心接口
/// </summary>
public interface IAgent
{
    /// <summary>
    /// Agent唯一标识符
    /// </summary>
    string Id { get; }
    
    /// <summary>
    /// Agent名称
    /// </summary>
    string Name { get; }
    
    /// <summary>
    /// 当前状态
    /// </summary>
    AgentState State { get; }
    
    /// <summary>
    /// 初始化Agent
    /// </summary>
    Task InitializeAsync(IAgentContext context, CancellationToken ct = default);
    
    /// <summary>
    /// 处理消息
    /// </summary>
    Task<AgentResponse> ProcessAsync(Message message, CancellationToken ct = default);
    
    /// <summary>
    /// 执行子任务
    /// </summary>
    Task<AgentResponse> ExecuteTaskAsync(subagent.SubAgentTask task, CancellationToken ct = default);
    
    /// <summary>
    /// 路由消息到合适的处理器
    /// </summary>
    Task<AgentResponse> RouteAsync(Message message, CancellationToken ct = default);
    
    /// <summary>
    /// 关闭Agent
    /// </summary>
    Task ShutdownAsync(CancellationToken ct = default);
    
    /// <summary>
    /// 状态变更事件
    /// </summary>
    event EventHandler<AgentStateChangedEventArgs>? StateChanged;
    
    /// <summary>
    /// 消息接收事件
    /// </summary>
    event EventHandler<Message>? MessageReceived;
}

/// <summary>
/// Agent状态变更事件参数
/// </summary>
public class AgentStateChangedEventArgs : EventArgs
{
    /// <summary>
    /// Agent ID
    /// </summary>
    public string AgentId { get; set; } = string.Empty;
    
    /// <summary>
    /// 旧状态
    /// </summary>
    public AgentState OldState { get; set; }
    
    /// <summary>
    /// 新状态
    /// </summary>
    public AgentState NewState { get; set; }
    
    /// <summary>
    /// 变更原因
    /// </summary>
    public string? Reason { get; set; }
}
