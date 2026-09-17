using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.rag;


/// <summary>
/// 用户反馈持久化服务
/// </summary>
public interface IFeedbackPersistence
{
    /// <summary>
    /// 保存用户反馈
    /// </summary>
    Task SaveAsync(UserFeedback feedback);
    
    /// <summary>
    /// 查询相似反馈（用于RAG召回）
    /// </summary>
    Task<List<RecallResult>> QuerySimilarAsync(string query, int topK = 5);
    
    /// <summary>
    /// 获取任务的所有反馈
    /// </summary>
    Task<List<UserFeedback>> GetByTaskAsync(string taskId);
    
    /// <summary>
    /// 获取会话的所有反馈
    /// </summary>
    Task<List<UserFeedback>> GetBySessionAsync(string sessionId);
    
    /// <summary>
    /// 标记反馈结果
    /// </summary>
    Task UpdateOutcomeAsync(string feedbackId, string outcome, double? satisfaction = null);
}
