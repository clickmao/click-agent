using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;


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
