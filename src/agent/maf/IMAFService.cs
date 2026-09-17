using Microsoft.Extensions.Logging;
using System.Net.Http.Json;

namespace agent.maf;


/// <summary>
/// MAF服务接口
/// </summary>
public interface IMAFService
{
    Task<bool> SendMessageAsync(string agentId, core.Message message);
    Task<core.Message?> ReceiveMessageAsync(CancellationToken ct = default);
    Task<bool> RegisterAgentAsync(string agentId, string name);
    Task DeregisterAgentAsync(string agentId);
    bool IsConnected { get; }
}
