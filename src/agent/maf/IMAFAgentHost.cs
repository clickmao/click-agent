using Microsoft.Extensions.Logging;
using System.Net.Http.Json;

namespace agent.maf;


/// <summary>
/// MAF Agent宿主接口
/// </summary>
public interface IMAFAgentHost
{
    string HostId { get; }
    bool IsRunning { get; }
    Task StartAsync(CancellationToken ct = default);
    Task StopAsync(CancellationToken ct = default);
    Task PublishMessageAsync(core.Message message);
    Task SubscribeAsync(string topic, Func<core.Message, Task> handler);
}
