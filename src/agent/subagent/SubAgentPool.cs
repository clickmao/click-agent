using Microsoft.Extensions.Logging;
using agent.core;

namespace agent.subagent;


/// <summary>
/// SubAgent池实现
/// </summary>
public class SubAgentPool : ISubAgentPool
{
    private readonly ILogger<SubAgentPool> _logger;
    private readonly List<SubAgent> _agents = new();
    private readonly Queue<SubAgent> _availableAgents = new();
    private readonly object _lock = new();
    
    public int MaxAgents { get; set; } = 4;
    public int ActiveAgentCount
    {
        get
        {
            lock (_lock)
            {
                return _agents.Count(a => a.IsBusy);
            }
        }
    }
    
    public event EventHandler<SubAgent>? AgentAcquired;
    public event EventHandler<SubAgent>? AgentReleased;
    
    public SubAgentPool(ILogger<SubAgentPool> logger, int maxAgents = 4)
    {
        _logger = logger;
        MaxAgents = maxAgents;
    }
    
    public async Task<ISubAgent> AcquireAsync(CancellationToken ct = default)
    {
        SubAgent agent;
        
        lock (_lock)
        {
            // 尝试获取空闲的Agent
            while (_availableAgents.Count > 0)
            {
                var candidate = _availableAgents.Dequeue();
                if (!candidate.IsBusy)
                {
                    agent = candidate;
                    _logger.LogDebug("Reusing existing SubAgent {AgentId}", agent.Id);
                    AgentAcquired?.Invoke(this, agent);
                    return agent;
                }
            }
            
            // 创建新的Agent（如果未达到上限）
            if (_agents.Count < MaxAgents)
            {
                agent = new SubAgent(
                    _logger as ILogger<SubAgent> ?? 
                    LoggerFactory.Create(b => b.AddConsole()).CreateLogger<SubAgent>()
                );
                _agents.Add(agent);
                _logger.LogDebug("Created new SubAgent {AgentId} (total: {Count}/{Max})", 
                    agent.Id, _agents.Count, MaxAgents);
                AgentAcquired?.Invoke(this, agent);
                return agent;
            }
        }
        
        // 等待可用Agent
        _logger.LogWarning("All SubAgents busy, waiting for available agent...");
        
        while (true)
        {
            ct.ThrowIfCancellationRequested();
            
            lock (_lock)
            {
                if (_availableAgents.Count > 0)
                {
                    agent = _availableAgents.Dequeue();
                    if (!agent.IsBusy)
                    {
                        AgentAcquired?.Invoke(this, agent);
                        return agent;
                    }
                }
            }
            
            await Task.Delay(100, ct);
        }
    }
    
    public Task ReleaseAsync(ISubAgent agent)
    {
        if (agent is SubAgent subAgent)
        {
            lock (_lock)
            {
                if (!_availableAgents.Contains(subAgent))
                {
                    _availableAgents.Enqueue(subAgent);
                }
            }
            
            _logger.LogDebug("SubAgent {AgentId} released and available", agent.Id);
            AgentReleased?.Invoke(this, subAgent);
        }
        
        return Task.CompletedTask;
    }
    
    public Task<bool> TryRouteAsync(Message message, out ISubAgent agent)
    {
        lock (_lock)
        {
            // 优先选择空闲的Agent
            foreach (var subAgent in _agents)
            {
                if (!subAgent.IsBusy)
                {
                    agent = subAgent;
                    return Task.FromResult(true);
                }
            }
        }
        
        agent = null!;
        return Task.FromResult(false);
    }
    
    public IEnumerable<ISubAgent> GetAllAgents()
    {
        lock (_lock)
        {
            return _agents.ToList();
        }
    }
    
    public IEnumerable<ISubAgent> GetIdleAgents()
    {
        lock (_lock)
        {
            return _agents.Where(a => !a.IsBusy).ToList();
        }
    }
}
