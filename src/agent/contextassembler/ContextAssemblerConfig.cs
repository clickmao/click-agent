using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;

/// <summary>
/// 上下文组装器配置
/// </summary>
public class ContextAssemblerConfig
{
    /// <summary>
    /// 默认最大Token预算
    /// </summary>
    public int DefaultMaxTokenBudget { get; set; } = 8000;
    
    /// <summary>
    /// 每个数据源的默认Token配额
    /// </summary>
    public Dictionary<DataSourceType, int> DefaultSourceQuota { get; set; } = new()
    {
        { DataSourceType.Memory, 2000 },
        { DataSourceType.Session, 3000 },
        { DataSourceType.WebSearch, 1500 },
        { DataSourceType.UserTendency, 500 },
        { DataSourceType.WorkspaceFiles, 1000 },
        { DataSourceType.ToolOutput, 500 }
    };
    
    /// <summary>
    /// 默认相关性阈值
    /// </summary>
    public double DefaultMinRelevanceScore { get; set; } = 0.3;
    
    /// <summary>
    /// 默认启用压缩
    /// </summary>
    public bool DefaultEnableCompression { get; set; } = true;
    
    /// <summary>
    /// 缓存过期时间（秒）
    /// </summary>
    public int CacheExpirationSeconds { get; set; } = 300;
    
    /// <summary>
    /// 最大缓存条目数
    /// </summary>
    public int MaxCacheEntries { get; set; } = 1000;
    
    /// <summary>
    /// 并行召回超时（毫秒）
    /// </summary>
    public int RecallTimeoutMs { get; set; } = 5000;
    
    /// <summary>
    /// 启用并行召回
    /// </summary>
    public bool EnableParallelRecall { get; set; } = true;
    
    /// <summary>
    /// 启用缓存
    /// </summary>
    public bool EnableCache { get; set; } = true;
    
    /// <summary>
    /// 启用网络搜索
    /// </summary>
    public bool EnableWebSearch { get; set; } = true;
    
    /// <summary>
    /// 启用用户倾向
    /// </summary>
    public bool EnableUserTendency { get; set; } = true;
}
