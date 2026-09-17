using Microsoft.Extensions.Logging;
using System.Net.Http.Json;

namespace agent.maf;


/// <summary>
/// MAF服务实现
/// </summary>
public class MAFService : IMAFService
{
    private readonly MAFConfiguration _config;
    private readonly ILogger<MAFService> _logger;
    private readonly HttpClient _httpClient;
    private readonly Queue<core.Message> _messageQueue = new();
    private readonly object _lock = new();
    private bool _lastCommunicationSucceeded;

    /// <summary>真实连接状态: 配置启用 且 最近一次实际通信成功 (而非仅看配置位)</summary>
    public bool IsConnected => _config.Enabled && _lastCommunicationSucceeded;
    
    public MAFService(MAFConfiguration config, ILogger<MAFService> logger, HttpClient httpClient)
    {
        _config = config;
        _logger = logger;
        _httpClient = httpClient;
        _httpClient.BaseAddress = new Uri(config.Endpoint);
    }
    
    public async Task<bool> SendMessageAsync(string agentId, core.Message message)
    {
        if (!_config.Enabled)
        {
            _logger.LogDebug("MAF disabled, queuing message locally");
            lock (_lock) { _messageQueue.Enqueue(message); }
            return true;
        }
        
        try
        {
            var response = await _httpClient.PostAsJsonAsync($"/api/agents/{agentId}/messages", message);
            _lastCommunicationSucceeded = response.IsSuccessStatusCode;
            return response.IsSuccessStatusCode;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to send message via MAF");
            lock (_lock) { _messageQueue.Enqueue(message); }
            return false;
        }
    }
    
    public Task<core.Message?> ReceiveMessageAsync(CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (_messageQueue.TryDequeue(out var message))
            {
                return Task.FromResult<core.Message?>(message);
            }
        }
        
        return Task.FromResult<core.Message?>(null);
    }
    
    public async Task<bool> RegisterAgentAsync(string agentId, string name)
    {
        if (!_config.Enabled)
        {
            _logger.LogDebug("MAF disabled, agent registration skipped");
            return true;
        }
        
        _logger.LogInformation("Registering agent {AgentId} ({Name}) with MAF", agentId, name);
        try
        {
            var response = await _httpClient.PostAsJsonAsync("/api/agents/register",
                new { agentId, name });
            _lastCommunicationSucceeded = response.IsSuccessStatusCode;
            return response.IsSuccessStatusCode;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to register agent {AgentId} with MAF", agentId);
            _lastCommunicationSucceeded = false;
            return false;
        }
    }
    
    public Task DeregisterAgentAsync(string agentId)
    {
        _logger.LogInformation("Deregistering agent {AgentId} from MAF", agentId);
        return Task.CompletedTask;
    }
}
