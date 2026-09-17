using Microsoft.Extensions.Logging;

namespace agent.core;


/// <summary>
/// 消息处理器接口
/// </summary>
public interface IMessageHandler
{
    /// <summary>
    /// 是否能处理该消息
    /// </summary>
    Task<bool> CanHandleAsync(Message message, CancellationToken ct = default);
    
    /// <summary>
    /// 处理消息
    /// </summary>
    Task<AgentResponse> HandleAsync(Message message, CancellationToken ct = default);
    
    /// <summary>
    /// 优先级（数字越小优先级越高）
    /// </summary>
    int Priority { get; }
}
