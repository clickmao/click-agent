using Microsoft.Extensions.Logging;
using System.Text.Json.Serialization;

namespace agent.session;


/// <summary>
/// 会话管理器接口
/// </summary>
public interface ISessionManager
{
    /// <summary>
    /// 创建会话
    /// </summary>
    Task<Session> CreateSessionAsync(string userId, SessionConfig? config = null);
    
    /// <summary>
    /// 获取会话
    /// </summary>
    Task<Session?> GetSessionAsync(string sessionId);
    
    /// <summary>
    /// 获取或创建会话 (幂等: 指定 Id 不存在时以该 Id 创建, 保证多轮对话历史不因会话缺失而静默丢失)
    /// </summary>
    Task<Session> GetOrCreateSessionAsync(string sessionId, string userId);
    
    /// <summary>
    /// 更新会话
    /// </summary>
    Task UpdateSessionAsync(Session session);
    
    /// <summary>
    /// 结束会话
    /// </summary>
    Task EndSessionAsync(string sessionId);
    
    /// <summary>
    /// 获取会话循环
    /// </summary>
    Task<SessionLoop> GetSessionLoopAsync(string sessionId);
    
    /// <summary>
    /// 获取用户的所有会话
    /// </summary>
    Task<IEnumerable<Session>> GetUserSessionsAsync(string userId);

    /// <summary>
    /// 获取全部会话 (v7.14 面板: /session 需要跨用户枚举)
    /// </summary>
    Task<IEnumerable<Session>> GetAllSessionsAsync();
}
