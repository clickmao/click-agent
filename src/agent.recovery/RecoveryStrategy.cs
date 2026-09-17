using Microsoft.Extensions.Logging;

namespace agent.recovery;


/// <summary>
/// 恢复策略
/// </summary>
public enum RecoveryStrategy
{
    Retry,
    RetryWithBackoff,
    Skip,
    Fallback,
    Rollback,
    UserConfirmation,
    Cancel
}
