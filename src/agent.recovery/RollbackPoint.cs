using Microsoft.Extensions.Logging;

namespace agent.recovery;


/// <summary>
/// 回滚点
/// </summary>
public class RollbackPoint
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Operation { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public string State { get; set; } = string.Empty;
    public Dictionary<string, object> Metadata { get; set; } = new();
    public Func<Task<bool>> RollbackAction { get; set; } = () => Task.FromResult(true);
}
