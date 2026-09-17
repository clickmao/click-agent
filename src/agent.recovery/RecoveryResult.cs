using Microsoft.Extensions.Logging;

namespace agent.recovery;


/// <summary>
/// 恢复结果
/// </summary>
public class RecoveryResult
{
    public bool Success { get; set; }
    public string? Error { get; set; }
    public int Attempts { get; set; }
    public TimeSpan Duration { get; set; }
    public string? ActionTaken { get; set; }
}
