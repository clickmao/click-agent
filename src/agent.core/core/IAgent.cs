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
    Task<AgentResponse> ExecuteTaskAsync(SubAgentTask task, CancellationToken ct = default);
    
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
