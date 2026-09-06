using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;

/// <summary>
/// 数据源类型枚举
/// </summary>
public enum DataSourceType
{
    /// <summary>持久化记忆 (RAG/Memory) </summary>
    Memory,
    
    /// <summary>当前会话历史</summary>
    Session,
    
    /// <summary>网络搜索结果</summary>
    WebSearch,
    
    /// <summary>用户倾向/偏好</summary>
    UserTendency,
    
    /// <summary>工作区文件</summary>
    WorkspaceFiles,
    
    /// <summary>外部工具输出</summary>
    ToolOutput,

    /// <summary>会话长期记忆 + 任务目标画像 (v7.14)</summary>
    SessionMemory,

    /// <summary>Agent 画像 + 能力清单 (v7.14)</summary>
    AgentContext
}

/// <summary>
/// 上下文片段（来自不同数据源）
/// </summary>
public class ContextSnippet
{
    /// <summary>唯一标识</summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>数据源类型</summary>
    public DataSourceType SourceType { get; set; }
    
    /// <summary>数据源名称</summary>
    public string SourceName { get; set; } = string.Empty;
    
    /// <summary>原始内容</summary>
    public string Content { get; set; } = string.Empty;
    
    /// <summary>压缩后的内容</summary>
    public string? CompressedContent { get; set; }
    
    /// <summary>相关性得分 (0-1)</summary>
    public double RelevanceScore { get; set; }
    
    /// <summary>创建时间</summary>
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    
    /// <summary>过期时间（可选）</summary>
    public DateTime? ExpiresAt { get; set; }
    
    /// <summary>是否已压缩</summary>
    public bool IsCompressed { get; set; }
    
    /// <summary>元数据</summary>
    public Dictionary<string, object> Metadata { get; set; } = new();
    
    /// <summary>Token数估算</summary>
    public int EstimatedTokens { get; set; }
    
    /// <summary>标签（用于分类/过滤）</summary>
    public List<string> Tags { get; set; } = new();
}

/// <summary>
/// 上下文组装请求
/// </summary>
public class ContextAssemblyRequest
{
    /// <summary>用户消息</summary>
    public string UserMessage { get; set; } = string.Empty;
    
    /// <summary>会话ID</summary>
    public string? SessionId { get; set; }
    
    /// <summary>用户ID</summary>
    public string? UserId { get; set; }
    
    /// <summary>要启用的数据源</summary>
    public HashSet<DataSourceType> EnabledSources { get; set; } = new()
    {
        DataSourceType.Memory,
        DataSourceType.Session,
        DataSourceType.UserTendency
    };
    
    /// <summary>v0.11.0 R11: 工作区根路径 (WorkspaceFiles 源召回用; null=不启用)</summary>
    public string? WorkspaceRoot { get; set; }

    /// <summary>最大Token预算</summary>
    public int MaxTokenBudget { get; set; } = 8000;
    
    /// <summary>每个数据源的Token配额</summary>
    public Dictionary<DataSourceType, int> SourceTokenQuota { get; set; } = new()
    {
        { DataSourceType.Memory, 2000 },
        { DataSourceType.Session, 3000 },
        { DataSourceType.WebSearch, 1500 },
        { DataSourceType.UserTendency, 500 },
        { DataSourceType.WorkspaceFiles, 1000 },
        { DataSourceType.ToolOutput, 500 },
        { DataSourceType.SessionMemory, 400 },
        { DataSourceType.AgentContext, 300 }
    };
    
    /// <summary>相关性阈值（低于此分数的片段将被过滤）</summary>
    public double MinRelevanceScore { get; set; } = 0.3;
    
    /// <summary>是否启用压缩</summary>
    public bool EnableCompression { get; set; } = true;
    
    /// <summary>压缩策略</summary>
    public tokencompression.CompressionStrategy CompressionStrategy { get; set; } = 
        tokencompression.CompressionStrategy.Selective;
    
    /// <summary>意图/任务类型（用于优化召回）</summary>
    public string? Intent { get; set; }
    
    /// <summary>是否包含高优先级上下文（如错误信息）</summary>
    public bool IncludeHighPriority { get; set; } = true;

    /// <summary>会话长期记忆+目标画像预渲染块 (v7.14; null = 不注入)</summary>
    public string? SessionMemoryBlock { get; set; }

    /// <summary>Agent 画像+能力清单预渲染块 (v7.14; null = 不注入)</summary>
    public string? AgentContextBlock { get; set; }
}

/// <summary>
/// 上下文组装结果
/// </summary>
public class ContextAssemblyResult
{
    /// <summary>组装后的Prompt头部</summary>
    public string PromptHeader { get; set; } = string.Empty;
    
    /// <summary>所有上下文片段</summary>
    public List<ContextSnippet> Snippets { get; set; } = new();
    
    /// <summary>各数据源的统计</summary>
    public Dictionary<DataSourceType, DataSourceStats> SourceStats { get; set; } = new();
    
    /// <summary>总Token数</summary>
    public int TotalTokens { get; set; }
    
    /// <summary>Token预算使用率</summary>
    public double TokenBudgetUsage { get; set; }
    
    /// <summary>上下文召回延迟（毫秒）</summary>
    public long AssemblyTimeMs { get; set; }
    
    /// <summary>警告信息</summary>
    public List<string> Warnings { get; set; } = new();
    
    /// <summary>是否成功</summary>
    public bool Success { get; set; }
    
    /// <summary>本次结果来自缓存 (重复请求直接复用)</summary>
    public bool FromCache { get; set; }  // 默认 false — 未命中缓存的结果不应标缓存 (打点统计真实性)
    
    /// <summary>错误信息</summary>
    public string? Error { get; set; }
}

/// <summary>
/// 数据源统计
/// </summary>
public class DataSourceStats
{
    public DataSourceType SourceType { get; set; }
    public int SnippetCount { get; set; }
    public int TotalTokens { get; set; }
    public double AvgRelevanceScore { get; set; }
    public long RecallTimeMs { get; set; }
}

/// <summary>
/// 上下文组装器接口
/// </summary>
public interface IContextAssembler
{
    /// <summary>
    /// 组装多数据源上下文
    /// </summary>
    /// <param name="request">组装请求</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>组装结果</returns>
    Task<ContextAssemblyResult> AssembleAsync(ContextAssemblyRequest request, CancellationToken ct = default);
    
    /// <summary>
    /// 异步组装（带进度报告）
    /// </summary>
    IAsyncEnumerable<ContextSnippet> AssembleWithProgressAsync(
        ContextAssemblyRequest request, 
        CancellationToken ct = default);
    
    /// <summary>
    /// 快速获取上下文摘要（用于预览）
    /// </summary>
    Task<ContextSummary> GetQuickSummaryAsync(
        string userMessage, 
        string sessionId, 
        int maxSnippets = 5);
    
    /// <summary>
    /// 失效特定上下文
    /// </summary>
    Task InvalidateAsync(string snippetId);
    
    /// <summary>
    /// 获取组装器统计信息
    /// </summary>
    ContextAssemblerStats GetStats();
}

/// <summary>
/// 上下文摘要（轻量级）
/// </summary>
public class ContextSummary
{
    public int TotalSnippets { get; set; }
    public Dictionary<DataSourceType, int> SnippetsBySource { get; set; } = new();
    public List<string> KeyTopics { get; set; } = new();
    public int EstimatedTokens { get; set; }
    public DateTime GeneratedAt { get; set; } = DateTime.UtcNow;
}

/// <summary>
/// 组装器统计
/// </summary>
public class ContextAssemblerStats
{
    public long TotalAssemblies { get; set; }
    public long TotalSnippets { get; set; }
    public long TotalTokensAssembled { get; set; }
    public double AvgAssemblyTimeMs { get; set; }
    public Dictionary<DataSourceType, long> RecallCountBySource { get; set; } = new();
    public long CacheHits { get; set; }
    public long CacheMisses { get; set; }
}
