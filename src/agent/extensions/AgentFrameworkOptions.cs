using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Configuration;
using agent.core;
using agent.memory;
using agent.templates;
using agent.search;
using agent.subagent;
using agent.session;
using agent.userinteraction;
using agent.pipeline;
using agent.tokencompression;
using agent.context;
using agent.rag;
using agent.datastore;
using agent.codegen;
using agent.workspace;
using agent.vectormemory;
using agent.recovery;
using agent.keywordannotation;
using agent.tendency;

namespace agent;


/// <summary>
/// AgentFramework选项
/// </summary>
public class AgentFrameworkOptions
{
    /// <summary>
    /// Agent名称
    /// </summary>
    public string AgentName { get; set; } = "MainAgent";
    
    /// <summary>
    /// 最大Token预算
    /// </summary>
    public long MaxTokenBudget { get; set; } = 100000;
    
    /// <summary>
    /// 默认超时
    /// </summary>
    public TimeSpan DefaultTimeout { get; set; } = TimeSpan.FromMinutes(5);
    
    /// <summary>
    /// 最大SubAgent数
    /// </summary>
    public int MaxSubAgents { get; set; } = 4;
    
    /// <summary>
    /// 启用MAF
    /// </summary>
    public bool EnableMAF { get; set; } = true;
    
    /// <summary>
    /// 启用搜索缓存
    /// </summary>
    public bool EnableSearchCache { get; set; } = true;
    
    /// <summary>
    /// webreaper CLI 可执行文件路径 (可选; 缺省走 PATH 探测)
    /// </summary>
    public string? WebReaperCliPath { get; set; }
    
    /// <summary>
    /// 托管级别 (full/standard/strict): 决定敏感操作是否需要问询真实用户
    /// </summary>
    public string? SupervisionLevel { get; set; } = "standard";
    
    /// <summary>
    /// 搜索插件配置 (博查Key/SearXNG端点等; 缺失时运行时向用户问询)
    /// </summary>
    public Dictionary<string, Dictionary<string, string>> SearchProviderConfig { get; set; } = new();
    
    /// <summary>
    /// MAF端点
    /// </summary>
    public string MAFEndpoint { get; set; } = "http://localhost:5000";
    
    /// <summary>
    /// 摘要触发轮次
    /// </summary>
    public int SummarizeAfterTurns { get; set; } = 10;
    
    /// <summary>
    /// 短期记忆最大条目数
    /// </summary>
    public int ShortTermMemoryMaxEntries { get; set; } = 1000;
    
    /// <summary>
    /// 数据存储路径
    /// </summary>
    public string DataStoragePath { get; set; } = "./data";
    
    /// <summary>
    /// 模板存储路径
    /// </summary>
    public string TemplateStoragePath { get; set; } = "./data/templates";
}
