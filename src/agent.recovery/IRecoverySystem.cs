using Microsoft.Extensions.Logging;

namespace agent.recovery;


/// <summary>
/// 错误恢复系统接口
/// </summary>
public interface IRecoverySystem
{
    /// <summary>
    /// 记录错误
    /// </summary>
    Task<ErrorInfo> RecordErrorAsync(Exception exception, Dictionary<string, object>? context = null);
    
    /// <summary>
    /// 获取恢复建议
    /// </summary>
    Task<List<RecoveryAction>> GetRecoveryActionsAsync(string errorId);
    
    /// <summary>
    /// 执行恢复
    /// </summary>
    Task<RecoveryResult> ExecuteRecoveryAsync(string errorId, RecoveryAction action);
    
    /// <summary>
    /// 创建回滚点
    /// </summary>
    Task<string> CreateRollbackPointAsync(string operation, string state, Dictionary<string, object>? metadata = null);
    
    /// <summary>
    /// 回滚到指定点
    /// </summary>
    Task<bool> RollbackToAsync(string rollbackPointId);
    
    /// <summary>
    /// 获取错误历史
    /// </summary>
    Task<List<ErrorInfo>> GetErrorHistoryAsync(int count = 50);
}
