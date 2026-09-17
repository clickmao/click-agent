using Microsoft.Extensions.Logging;
using System.Net.Http.Json;

namespace agent.maf;


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
