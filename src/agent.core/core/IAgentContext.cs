using Microsoft.Extensions.DependencyInjection;

namespace agent.core;

/// <summary>
/// Agent 上下文纯契约 —— 只含会话身份、Token 预算与 DI 服务解析。
/// 注意: 不含按类型的服务定位门面 (GetMemoryAsync 等), 具体服务一律由 DI 构造函数注入。
/// </summary>
public interface IAgentContext
{
    /// <summary>会话ID</summary>
    string SessionId { get; }

    /// <summary>用户ID</summary>
    string UserId { get; }

    /// <summary>父上下文（用于SubAgent）</summary>
    IAgentContext? Parent { get; }

    /// <summary>自定义属性</summary>
    IDictionary<string, object> Properties { get; }

    /// <summary>Token预算</summary>
    long TokenBudget { get; set; }

    /// <summary>已使用的Token数</summary>
    long TokensUsed { get; }

    /// <summary>添加Token使用量 (线程安全)</summary>
    void AddTokenUsage(long tokens);

    /// <summary>检查是否有足够的Token余量</summary>
    bool HasTokenBudget(long tokens);

    /// <summary>从 DI 容器解析服务 (强类型, 单一服务定位出口)</summary>
    T GetService<T>() where T : class;
}

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
