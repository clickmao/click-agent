using Microsoft.Extensions.Logging;
using System.Net.Http.Json;

namespace agent.maf;

/// <summary>
/// MAF配置
/// </summary>
public class MAFConfiguration
{
    public string Endpoint { get; set; } = "http://localhost:5000";
    public string? ApiKey { get; set; }
    public int MaxRetries { get; set; } = 3;
    public int RetryDelayMs { get; set; } = 1000;
    public int TimeoutMs { get; set; } = 30000;
    public bool Enabled { get; set; } = true;
}

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

/// <summary>
/// MAF Agent宿主实现
/// </summary>
public class MAFAgentHost : IMAFAgentHost
{
    private readonly MAFConfiguration _config;
    private readonly ILogger<MAFAgentHost> _logger;
    private readonly Dictionary<string, Func<core.Message, Task>> _subscribers = new();
    private bool _isRunning;
    
    public string HostId { get; } = Guid.NewGuid().ToString();
    public bool IsRunning => _isRunning;
    
    public MAFAgentHost(MAFConfiguration config, ILogger<MAFAgentHost> logger)
    {
        _config = config;
        _logger = logger;
    }
    
    public Task StartAsync(CancellationToken ct = default)
    {
        if (_config.Enabled)
        {
            _isRunning = true;
            _logger.LogInformation("MAF Agent Host {HostId} started at {Endpoint}", HostId, _config.Endpoint);
        }
        else
        {
            _logger.LogWarning("MAF is disabled in configuration");
        }
        
        return Task.CompletedTask;
    }
    
    public Task StopAsync(CancellationToken ct = default)
    {
        _isRunning = false;
        _subscribers.Clear();
        _logger.LogInformation("MAF Agent Host {HostId} stopped", HostId);
        return Task.CompletedTask;
    }
    
    public Task PublishMessageAsync(core.Message message)
    {
        if (!_isRunning)
        {
            _logger.LogWarning("Cannot publish message: host is not running");
            return Task.CompletedTask;
        }
        
        _logger.LogDebug("Publishing message {MessageId} to topic subscribers", message.Id);
        
        // 通知订阅者
        foreach (var subscriber in _subscribers.Values)
        {
            _ = Task.Run(() => subscriber(message));
        }
        
        return Task.CompletedTask;
    }
    
    public Task SubscribeAsync(string topic, Func<core.Message, Task> handler)
    {
        _subscribers[topic] = handler;
        _logger.LogDebug("Subscribed to topic: {Topic}", topic);
        return Task.CompletedTask;
    }
}

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
