using Microsoft.Extensions.Logging;

namespace agent.recovery;


/// <summary>
/// 恢复操作
/// </summary>
public class RecoveryAction
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Name { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public RecoveryStrategy Strategy { get; set; }
    public int Priority { get; set; }
    public bool IsAutomatic { get; set; }
    public Func<Task<RecoveryResult>> ExecuteAsync { get; set; } = () => Task.FromResult(new RecoveryResult());
}
