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

/// <summary>
/// 上下文质量评估器
/// </summary>
public interface IContextQualityEvaluator
{
    /// <summary>
    /// 评估上下文片段质量
    /// </summary>
    Task<ContextQualityScore> EvaluateAsync(ContextSnippet snippet, CancellationToken ct = default);
    
    /// <summary>
    /// 评估组装结果质量
    /// </summary>
    Task<AssemblyQualityReport> EvaluateAssemblyAsync(ContextAssemblyResult result, CancellationToken ct = default);
}

/// <summary>
/// 上下文质量评分
/// </summary>
public class ContextQualityScore
{
    /// <summary>
    /// 总体质量分数 (0-1)
    /// </summary>
    public double OverallScore { get; set; }
    
    /// <summary>
    /// 相关性分数
    /// </summary>
    public double RelevanceScore { get; set; }
    
    /// <summary>
    /// 新鲜度分数
    /// </summary>
    public double FreshnessScore { get; set; }
    
    /// <summary>
    /// 完整性分数
    /// </summary>
    public double CompletenessScore { get; set; }
    
    /// <summary>
    /// 一致性分数
    /// </summary>
    public double ConsistencyScore { get; set; }
    
    /// <summary>
    /// 问题列表
    /// </summary>
    public List<string> Issues { get; set; } = new();
    
    /// <summary>
    /// 建议列表
    /// </summary>
    public List<string> Suggestions { get; set; } = new();
}

/// <summary>
/// 组装质量报告
/// </summary>
public class AssemblyQualityReport
{
    /// <summary>
    /// 总体质量
    /// </summary>
    public double OverallQuality { get; set; }
    
    /// <summary>
    /// 覆盖率
    /// </summary>
    public double Coverage { get; set; }
    
    /// <summary>
    /// 效率（Token使用率）
    /// </summary>
    public double Efficiency { get; set; }
    
    /// <summary>
    /// 多样性
    /// </summary>
    public double Diversity { get; set; }
    
    /// <summary>
    /// 各数据源质量
    /// </summary>
    public Dictionary<DataSourceType, double> QualityBySource { get; set; } = new();
    
    /// <summary>
    /// 问题
    /// </summary>
    public List<string> Issues { get; set; } = new();
    
    /// <summary>
    /// 优化建议
    /// </summary>
    public List<string> OptimizationSuggestions { get; set; } = new();
}

/// <summary>
/// 上下文优先级
/// </summary>
public enum ContextPriority
{
    /// <summary>低优先级</summary>
    Low = 0,
    
    /// <summary>普通优先级</summary>
    Normal = 1,
    
    /// <summary>高优先级</summary>
    High = 2,
    
    /// <summary>关键优先级（不可压缩）</summary>
    Critical = 3
}

/// <summary>
/// 上下文过期策略
/// </summary>
public class ContextExpirationPolicy
{
    /// <summary>
    /// 基于时间的过期
    /// </summary>
    public TimeSpan TimeToLive { get; set; } = TimeSpan.FromMinutes(30);
    
    /// <summary>
    /// 基于访问次数的过期
    /// </summary>
    public int MaxAccessCount { get; set; } = 100;
    
    /// <summary>
    /// 基于Token使用的过期
    /// </summary>
    public int MaxTokenUsage { get; set; } = 10000;
    
    /// <summary>
    /// 是否启用惰性删除
    /// </summary>
    public bool LazyDeletion { get; set; } = true;
}

/// <summary>
/// 上下文验证器
/// </summary>
public interface IContextValidator
{
    /// <summary>
    /// 验证片段
    /// </summary>
    ValidationResult ValidateSnippet(ContextSnippet snippet);
    
    /// <summary>
    /// 验证组装请求
    /// </summary>
    ValidationResult ValidateRequest(ContextAssemblyRequest request);
    
    /// <summary>
    /// 验证组装结果
    /// </summary>
    ValidationResult ValidateResult(ContextAssemblyResult result);
}

/// <summary>
/// 验证结果
/// </summary>
public class ValidationResult
{
    public bool IsValid { get; set; }
    public List<string> Errors { get; set; } = new();
    public List<string> Warnings { get; set; } = new();
    public List<string> Infos { get; set; } = new();
    
    public static ValidationResult Success() => new() { IsValid = true };
    
    public static ValidationResult Failure(params string[] errors) => new()
    {
        IsValid = false,
        Errors = errors.ToList()
    };
}
