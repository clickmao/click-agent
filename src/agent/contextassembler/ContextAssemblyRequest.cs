using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;


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

    /// <summary>v0.14.0 T2d: 修法记忆块 (宿主从 FixMemory recall 预渲染; null=不启用该源)</summary>
    public string? FixMemoryBlock { get; set; }

    /// <summary>v0.15.2: 警告/铁律块 (宿主从 GuardrailMemory recall 预渲染; null=不启用该源)</summary>
    public string? GuardrailBlock { get; set; }

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
