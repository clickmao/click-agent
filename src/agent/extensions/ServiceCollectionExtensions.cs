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
/// AgentFramework服务扩展
/// </summary>
public static class ServiceCollectionExtensions
{
    /// <summary>
    /// 添加AgentFramework服务
    /// </summary>
    public static IServiceCollection AddAgentFramework(
        this IServiceCollection services,
        Action<AgentFrameworkOptions>? configure = null)
    {
        // 配置
        var options = new AgentFrameworkOptions();
        configure?.Invoke(options);
        services.AddSingleton(options);
        
        // HttpClient (OpenAILLMCaller/搜索插件共享)
        services.AddHttpClient();
        // v0.10.0 需求③: 官方/远端端点可配置代理 (models.yaml proxy 段)
        // 留空直连; 配置后 modelqueue 命名客户端全走代理 (主调用/余额/verify 共用)。
        // 正确形态: ConfigurePrimaryHttpMessageHandler 替换主处理器 (configure action 不能换 client 实例)。
        services.AddHttpClient("modelqueue")
            .ConfigurePrimaryHttpMessageHandler(sp =>
            {
                var cfg = sp.GetRequiredService<agent.config.ConfigSnapshot>();
                var url = cfg.Get("proxy", "url", "");
                var bypassLocal = cfg.Get("proxy", "bypass_local", true);
                if (string.IsNullOrWhiteSpace(url))
                    return new HttpClientHandler(); // 直连 (默认行为)
                return new HttpClientHandler
                {
                    Proxy = new System.Net.WebProxy(url) { BypassProxyOnLocal = bypassLocal },
                    UseProxy = true,
                };
            });

        // 核心服务
        services.AddSingleton<IMemoryStore, MemoryStore>();
        services.AddSingleton<ISummarizer, Summarizer>();
        services.AddSingleton<ITemplateStore, TemplateManager>();
        services.AddSingleton<ITemplateMatcher, TemplateMatcher>();
        // ✅ 插件化搜索体系: 多源插件 + 主备槽位故障转移 + 熔断提升 + 状态持久化
        // 免费源 (DDG/BingCN/百度) 优先, 付费源 (博查) 在用户提供 Key 后参与;
        // Key 缺失时由 ConsoleUserPromptService 向真实用户问询 (带作用说明+类型flag)
        services.AddSingleton<SearchProvidersOptions>(sp =>
        {
            var opts = sp.GetRequiredService<AgentFrameworkOptions>();
            return new SearchProvidersOptions
            {
                WebReaperCliPath = opts.WebReaperCliPath,
                SlotStatePath = "search_slots.json",
                ProviderTimeoutSeconds = 10,
                FailureThreshold = 3,
            };
        });
        services.AddSingleton<BochaSearchProvider>(sp =>
        {
            var opts = sp.GetRequiredService<AgentFrameworkOptions>();
            string? key = null;
            if (opts.SearchProviderConfig.TryGetValue("bocha", out var cfg))
                cfg.TryGetValue("apiKey", out key);
            return new BochaSearchProvider(
                SharedHttp.ForProviders(),
                sp.GetRequiredService<ILogger<BochaSearchProvider>>(),
                key);
        });
        services.AddSingleton<SearXngSearchProvider>(sp =>
        {
            var opts = sp.GetRequiredService<AgentFrameworkOptions>();
            string? endpoint = null;
            if (opts.SearchProviderConfig.TryGetValue("searxng", out var cfg))
                cfg.TryGetValue("endpoint", out endpoint);
            return new SearXngSearchProvider(
                SharedHttp.ForProviders(),
                sp.GetRequiredService<ILogger<SearXngSearchProvider>>(),
                endpoint);
        });
        services.AddSingleton<BingCnSearchProvider>(sp =>
            new BingCnSearchProvider(SharedHttp.ForProviders(),
                sp.GetRequiredService<ILogger<BingCnSearchProvider>>()));
        services.AddSingleton<BaiduSearchProvider>(sp =>
            new BaiduSearchProvider(SharedHttp.ForProviders(),
                sp.GetRequiredService<ILogger<BaiduSearchProvider>>()));
        services.AddSingleton<DuckDuckGoSearchProvider>(sp =>
            new DuckDuckGoSearchProvider(SharedHttp.ForProviders(),
                sp.GetRequiredService<ILogger<DuckDuckGoSearchProvider>>()));
        services.AddSingleton<ISearchService>(sp =>
        {
            var opts = sp.GetRequiredService<AgentFrameworkOptions>();
            return new SearchFailoverService(
                new ISearchProvider[]
                {
                    sp.GetRequiredService<DuckDuckGoSearchProvider>(),
                    sp.GetRequiredService<BochaSearchProvider>(),
                    sp.GetRequiredService<SearXngSearchProvider>(),
                    sp.GetRequiredService<BingCnSearchProvider>(),
                    sp.GetRequiredService<BaiduSearchProvider>(),
                },
                sp.GetRequiredService<SearchProvidersOptions>(),
                opts.DataStoragePath,
                sp.GetRequiredService<ILogger<SearchFailoverService>>(),
                sp.GetService<IUserPromptService>());
        });
        services.AddSingleton<ISubAgentPool, SubAgentPool>();

        // ✅ Agent 注册表 + 下轮预估 + 本地命令 + 问询打通 (v7.11)
        services.AddSingleton(sp =>
        {
            var opts = sp.GetRequiredService<AgentFrameworkOptions>();
            return new agent.registry.AgentRegistry(opts.DataStoragePath);
        });
        services.AddSingleton<agent.registry.ClarificationService>();

        // ✅ 返回内容区段路由 (v7.11): 插件化后处理, 宿主可追加自定义插件
        services.AddSingleton<agent.registry.IResponseSegmentPlugin, agent.registry.UiCapturePlugin>();
        services.AddSingleton<agent.registry.IResponseSegmentPlugin, agent.registry.CodeReviewPlugin>();
        services.AddSingleton(sp =>
        {
            var plugins = sp.GetServices<agent.registry.IResponseSegmentPlugin>();
            return new agent.registry.ResponseSegmentRouter(plugins);
        });
        services.AddSingleton<ISessionManager, SessionManager>();
        services.AddSingleton<IUserInteraction, ConsoleUserInteraction>();
        // ✅ 问询服务: 凭据/敏感操作的阻塞式交互 (等待真实用户或主agent代答)
        services.AddSingleton<IUserPromptService>(sp =>
        {
            var opts = sp.GetRequiredService<AgentFrameworkOptions>();
            var supervision = opts.SupervisionLevel?.ToLowerInvariant() switch
            {
                "full" => SupervisionLevel.Full,
                "strict" => SupervisionLevel.Strict,
                _ => SupervisionLevel.Standard,
            };
            return new ConsoleUserPromptService(
                sp.GetRequiredService<ILogger<ConsoleUserPromptService>>(),
                opts.DataStoragePath,
                supervision);
        });
        services.AddSingleton<ITokenCompressor, TokenCompressor>();
        services.AddSingleton<IDataStore, DataStore>();
        services.AddSingleton<IKeywordTagger, KeywordTagger>();
        services.AddSingleton<ITendencyAnalyzer, TendencyAnalyzer>();
        services.AddSingleton<ITaskDecomposer, TaskDecomposer>();
        
        // ✅ 代码生成和代码分析
        services.AddSingleton<ICodeGenerator, CodeGenerator>();
        
        // ✅ 工作区
        services.AddSingleton<IWorkspace, Workspace>();
        services.AddSingleton<IGitIntegration, GitIntegration>();
        
        // ✅ 向量存储
        services.AddSingleton<IVectorStore, VectorStore>();
        
        // ✅ 恢复系统
        services.AddSingleton<IRecoverySystem, RecoverySystem>();
        
        // ✅ 任务规划
        services.AddSingleton<ITaskPipeline, TaskPipeline>();
        
        // ✅ 交互管理
        
        // ✅ 记忆系统
        services.AddSingleton<IVectorMemoryRecall, VectorMemoryRecall>();
        services.AddSingleton<IAgentMemoryStore, AgentMemoryStore>();
        
        // ✅ Prompt构建
        services.AddSingleton<IPromptBuilder, PromptBuilder>();
        
        // ContextAssembler - 多数据源上下文组装
        services.AddSingleton<IRAGRecall, RAGRecall>();
        // v7.15 P3: bge 嵌入器 (压缩语义漂移校验) — 模型路径走配置, 缺失 → NullTextEmbedder (锚词模式, 行为兼容)
        services.AddSingleton<agent.contextgradient.ITextEmbedder>(sp =>
        {
            var cfg = sp.GetRequiredService<agent.config.ConfigSnapshot>();
            var modelPath = cfg.Get("embedding", "model_path", "");
            return File.Exists(modelPath)
                ? new agent.llamalocal.BgeEmbedder(modelPath)
                : new agent.contextgradient.NullTextEmbedder();
        });
        services.AddSingleton<IContextAssembler>(sp =>
        {
            var embedder = sp.GetRequiredService<agent.contextgradient.ITextEmbedder>();
            return new ContextAssembler(
                sp.GetRequiredService<ILogger<ContextAssembler>>(),
                sp.GetRequiredService<IRAGRecall>(),
                sp.GetRequiredService<ISessionManager>(),
                sp.GetRequiredService<ITendencyAnalyzer>(),
                sp.GetRequiredService<ISearchService>(),
                sp.GetRequiredService<ITokenCompressor>(),
                embedder.IsAvailable ? embedder : null);
        });
        services.AddSingleton<IFeedbackPersistence, FeedbackPersistence>();
        
        // 主Agent: IndustrialAgentV2 是完整管线（意图识别→多源上下文组装→PromptBuilder→LLM→记忆/会话存储）
        // LLM 调用器: v7.15 模型队列接管 (目录 config/base/models.yaml — 主备切换/意图选模/手动覆盖)
        services.AddSingleton(sp =>
            agent.modelqueue.ModelCatalog.Load(sp.GetRequiredService<agent.config.ConfigSnapshot>()));
        // v0.10.0 需求①: 本地推理通道 — LocalLlamaCaller 按 models.yaml local 段构造
        // (gguf 文件缺失 → LocalInferenceAdapter.IsAvailable=false, 本地通道诚实降级, 不伪造)
        services.AddSingleton(sp =>
        {
            var localCfg = sp.GetRequiredService<agent.modelqueue.ModelCatalog>().LocalChannel;
            return new agent.llamalocal.LocalLlamaCaller(
                Microsoft.Extensions.Logging.LoggerFactory.Create(b => { }).CreateLogger<agent.llamalocal.LocalLlamaCaller>(),
                localCfg.ModelPath,
                (uint)Math.Max(512, localCfg.ContextSize),
                gpuLayers: (uint)Math.Max(0, localCfg.GpuLayers));
        });
        services.AddSingleton(sp => new agent.modelqueue.TokenUsageService(
            sp.GetRequiredService<agent.modelqueue.BalanceQueryService>(),
            sp.GetRequiredService<agent.modelqueue.ModelCatalog>()));
        services.AddSingleton(sp => new agent.modelqueue.ModelQueueRouter(
            sp.GetRequiredService<agent.modelqueue.ModelCatalog>(),
            sp.GetRequiredService<IHttpClientFactory>(),
            sp.GetRequiredService<Microsoft.Extensions.Logging.ILogger<IndustrialAgentV2>>(),
            localInference: new agent.modelqueue.LocalInferenceAdapter(
                sp.GetRequiredService<agent.llamalocal.LocalLlamaCaller>()),
            tokenUsage: sp.GetRequiredService<agent.modelqueue.TokenUsageService>()));
        services.AddSingleton<ModelQueueAdapter>();
        services.AddSingleton<ILLMCaller>(sp => sp.GetRequiredService<ModelQueueAdapter>());
        services.AddSingleton<agent.subagent.ILLMCallerForIsolated>(sp => sp.GetRequiredService<ModelQueueAdapter>());
        services.AddSingleton(sp => new agent.modelqueue.BalanceQueryService(
            sp.GetRequiredService<agent.modelqueue.ModelCatalog>(),
            sp.GetRequiredService<IHttpClientFactory>()));
        services.AddSingleton(sp => new agent.modelqueue.ModelVerifyService(
            sp.GetRequiredService<agent.modelqueue.ModelCatalog>(),
            sp.GetRequiredService<IHttpClientFactory>()));

        // v7.15 P2: ConfigSnapshot 统一注册 (宿主未注册时兜底 — Skill/ModelCatalog DI 依赖)
        services.TryAddSingleton(sp => new agent.config.ConfigSnapshot());

        // v7.15 Skill 调度 (P1): skills/ 目录静态加载 + 触发匹配 + 口径承载
        services.AddSingleton(sp => agent.skills.SkillRegistry.LoadFromDirectory("skills"));
        services.AddSingleton(sp => new agent.skills.SkillDispatcher(
            sp.GetRequiredService<agent.skills.SkillRegistry>(),
            new agent.skills.TriggerMatcher(
                sp.GetRequiredService<agent.contextgradient.ITextEmbedder>()),
            getConfig: (module, key, fallback) => sp.GetRequiredService<agent.config.ConfigSnapshot>()
                .Get(module, key, fallback)));

        // v7.15 日志四通道: LogRouter (flags 默认全开 — config/base/logging.yaml 分层可覆盖)
        services.AddSingleton(sp => new agent.logging.MemoryLogBuffer(2000));
        // v7.15 L.6 定案: chatbox 推送通道出口 — CLI=控制台单行 JSON 协议行 (@chatbox: 前缀);
        // websocket/面板宿主注入各自 IChatboxSink 实现, agent 层零改动
        services.AddSingleton<agent.logging.IChatboxSink, agent.logging.ConsoleChatboxSink>();
        services.AddSingleton(sp => new agent.logging.LogRouter(
            agent.logging.LogFlags.All, sp.GetRequiredService<agent.logging.MemoryLogBuffer>())
        {
            ChatboxSink = sp.GetRequiredService<agent.logging.IChatboxSink>(),
        });

        // 优先注册 V2；MainAgent 保留为简单回显的 fallback
        services.AddSingleton<IndustrialAgentV2>();
        services.AddSingleton<IAgent>(sp =>
        {
            // NullLLMCaller 恒注册 → V2 管线总是可用；仅在 ILLMCaller 被外部移除时退回 MainAgent
            var llmCaller = sp.GetService<ILLMCaller>();
            if (llmCaller != null)
            {
                return sp.GetRequiredService<IndustrialAgentV2>();
            }
            return sp.GetRequiredService<MainAgent>();
        });
        // 同时保留 IAgent 的默认解析（无 LLM 配置时也可手动获取 V2）
        
        return services;
    }
    
    /// <summary>
    /// 添加带MAF的AgentFramework服务
    /// </summary>
    public static IServiceCollection AddAgentFrameworkWithMAF(
        this IServiceCollection services,
        Action<AgentFrameworkOptions>? configure = null)
    {
        services.AddAgentFramework(configure);
        
        // 添加MAF服务
        services.AddSingleton<agent.maf.MAFService>();
        services.AddSingleton<agent.maf.IMAFAgentHost, agent.maf.MAFAgentHost>();
        
        return services;
    }
}

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

/// <summary>
/// 主Agent实现
/// </summary>
public class MainAgent : AgentBase
{
    public MainAgent(
        ILogger<MainAgent> logger,
        IEnumerable<IMessageHandler> handlers) : base(logger, handlers)
    {
        Name = "MainAgent";
    }
    
    protected override Task<AgentResponse> OnProcessAsync(Message message, CancellationToken ct)
    {
        // 主Agent处理逻辑
        var response = new AgentResponse
        {
            Content = $"Processed: {message.Content}",
            Success = true,
            Type = MessageType.Text
        };
        
        return Task.FromResult(response);
    }
}
