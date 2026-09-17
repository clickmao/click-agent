using Microsoft.Extensions.DependencyInjection;

namespace agent.core;


/// <summary>
/// Agent 上下文默认实现 —— 仅依赖 IServiceProvider, 无任何具体服务类型依赖 (契约层纯净)。
/// </summary>
public class AgentContext : IAgentContext
{
    private readonly IServiceProvider _serviceProvider;
    private long _tokensUsed;

    public string SessionId { get; set; } = string.Empty;
    public string UserId { get; set; } = string.Empty;
    public IAgentContext? Parent { get; set; }
    public IDictionary<string, object> Properties { get; set; } = new Dictionary<string, object>();
    public long TokenBudget { get; set; } = 100000;
    public long TokensUsed => Interlocked.Read(ref _tokensUsed);

    public AgentContext(IServiceProvider serviceProvider)
    {
        _serviceProvider = serviceProvider;
    }

    public void AddTokenUsage(long tokens) => Interlocked.Add(ref _tokensUsed, tokens);

    public bool HasTokenBudget(long tokens) => (TokensUsed + tokens) <= TokenBudget;

    public T GetService<T>() where T : class
    {
        return _serviceProvider.GetRequiredService<T>();
    }
}
