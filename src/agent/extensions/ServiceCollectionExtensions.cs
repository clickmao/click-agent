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
        services.AddHttpClient("modelqueue", (sp, c) =>
            {
                // v0.11.0 R24: reasoning 模型长输出 (C03 报告类 60-100s) 需要超时余量;
                // 默认 100s 偶发掐断 3 子任务报告生成 (超时是重试/failover 的最大来源)。
                var llmTimeoutSec = sp.GetRequiredService<agent.config.ConfigSnapshot>()
                    .Get("llm", "timeout_seconds", 180);
                c.Timeout = TimeSpan.FromSeconds(llmTimeoutSec);
            })
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
        // ✅ R391(C8): 本地形式化验证段插件 — **在场** ⇒ 静态前缀注入 clickproof 输出契约 (不在场 ⇒ 前缀与 R380 逐字一致)。
        //    非 clickproof 段恒等透传 (零改动模型正文); clickproof 段 → 本地内核确定性裁决 + 遥测 (零 token)。
        //    环境开关 AGENTFRAMEWORK_FORMAL_SEGMENT=0 可整段关闭 (缺省开)。
        if (agent.registry.ClickRoverSegmentPlugin.Enabled)
            services.AddSingleton<agent.registry.IResponseSegmentPlugin, agent.registry.ClickRoverSegmentPlugin>();
        // ✅ R368: python 段 → 落盘 + py_compile 机器校验 (用户钦定 "内置个PY和PY执行插件")
        services.AddSingleton<agent.registry.PythonArtifactLedger>();
        services.AddSingleton<agent.registry.IResponseSegmentPlugin>(sp =>
        {
            var opts = sp.GetRequiredService<AgentFrameworkOptions>();
            return new agent.registry.PythonArtifactPlugin(
                sp.GetRequiredService<agent.registry.PythonArtifactLedger>(),
                System.IO.Path.Combine(opts.DataStoragePath, "artifacts"));
        });
        // v0.22.0 exp9 D3: 计划真执行体 — 本地节点零 token 真跑 (需 python 产物台账定位产物路径)
        services.AddSingleton(sp => new agent.intent.PlanRunner(
            executors: null,
            ledger: sp.GetRequiredService<agent.registry.PythonArtifactLedger>(),
            events: sp.GetService<agent.intent.IPlanEventSink>()));
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
        // v0.11.0 R103: RAG 注入 EmbeddingRouter (bge 首选/词袋兜底, 用户钦定优先级;
        // 模式决策: LLM 已加载→CPU 档, 未加载+真 GPU→vulkan)。工厂走 DI 让 bge 感知共享服务状态。
        services.AddSingleton<RAGConfig>(sp =>
        {
            var cfg = new RAGConfig();
            // v0.13.0 (用户钦定): RAG 数据文件可由用户指定 — CLI -rag <path> 或任务内 /rag <path>
            // 都落到此 env 钩子 (启动期设置, 进程内生效); 未设 → 既有解析序 (覆写/CWD/AppContext)。
            var ragOverride = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_RAG_PATH");
            if (!string.IsNullOrEmpty(ragOverride)) cfg.PersistPathOverride = ragOverride;
            // R352: EmbeddingRouter = RemoteEmbedder (语义) + hash 兜底 (本地 bge 已移除)
            cfg.EmbeddingFunction = text => new agent.llamalocal.EmbeddingRouter(
                sp.GetRequiredService<agent.contextgradient.ITextEmbedder>()).Embed(text);
            // R404 (用户钦定): 检索融合 = 词法路 + dense 路 + RRF(k0=10, w=1:1)。
            // 产品口径 (dense 路喂的是链上真身 bge-q8.gguf = 25.2MB bge-small-zh-v1.5 q8):
            // 冻结集 (1299 语料/120 查询) 实测 r@10 0.6333 → 0.7833 (+18 条查询, 配对 McNemar p=4e-05);
            // 旧注释的 0.8500 是 dense-base(110MB) 评测对照口径 —— 跨基座混算之误, 已订正。
            // Fusion=null 时完全退回旧 hybrid 加权路 (行为兼容)。
            cfg.Fusion = new agent.rag.FusionOptions { Enabled = true, K0 = 10, DenseWeight = 1.0, LexicalWeight = 1.0 };
            return cfg;
        });
        services.AddSingleton<IRAGRecall, RAGRecall>();
        // R353 (用户钦定): bge 本地 CPU 最小推理 (纯托管 BERT forward, 零 LLamaSharp/ONNX) —
        // EmbedAsync 异步, 与召回/压缩主链并行 (R352-b)。模型缺失 → NullTextEmbedder (锚词模式, 行为兼容)。
        services.AddSingleton<agent.contextgradient.ITextEmbedder>(sp =>
        {
            // R408 (用户钦定: 本地 GGUF 引擎整线退役 → llama.cpp 进程化接入):
            // 嵌入 = **懒启动**的专用 llama-server 进程 (`--embeddings`; 该开关与生成互斥 ⇒ 与生成各起一个进程)。
            // 边界只有「进程 + loopback HTTP」⇒ 零 P/Invoke、跨平台、AOT 可用
            // (对照 R90: LLamaSharp 进程内 interop 在 NativeAOT 下 SIGSEGV)。
            // IsAvailable = 纯配置判定 (模型文件 ∧ 二进制可解析, 零 I/O 零进程) ⇒ 不满足即锚词回退 (行为兼容)。
            // 失败不静默兜底: EmbedAsync 抛 LlamaCppException(带 code) 由调用方决定。
            var embedder = new agent.llamacpp.LlamaCppTextEmbedder(agent.llamacpp.LlamaCppEmbedderOptions.FromEnvironment());
            if (embedder.IsAvailable) return embedder;
            // R465: 三态 —— 「env 声明了 bge 权重但文件缺失」**必须留痕**, 不再与「未声明」不可区分
            //   (与 R464 生成通道同一纪律: 声明即意图; 错配不静默替换, 但通道仍 fail-open 回锚词)。
            var embEnvPath = Environment.GetEnvironmentVariable(agent.llamacpp.LocalChannelWiring.EmbedderEnvVar);
            var embWiring = agent.llamacpp.LocalChannelWiring.ResolveEmbedder(
                !string.IsNullOrWhiteSpace(embEnvPath), embEnvPath, agent.llamacpp.LlamaCppEmbedderOptions.DefaultModelPath);
            if (embWiring.Warning is not null)
            {
                sp.GetService<Microsoft.Extensions.Logging.ILoggerFactory>()
                  ?.CreateLogger("agent.llamacpp.EmbedderWiring")
                  .LogWarning("{EmbedderWiringWarning}", embWiring.Warning);
                Console.Error.WriteLine("[warn] " + embWiring.Warning);
            }
            return new agent.contextgradient.NullTextEmbedder();
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
        // LLM 调用器: 模型队列接管 (目录 config/base/models.yaml — 主备切换/意图选模/手动覆盖)
        services.AddSingleton(sp =>
            agent.modelqueue.ModelCatalog.Load(sp.GetRequiredService<agent.config.ConfigSnapshot>()));
        services.AddSingleton(sp => new agent.modelqueue.TokenUsageService(
            sp.GetRequiredService<agent.modelqueue.BalanceQueryService>(),
            sp.GetRequiredService<agent.modelqueue.ModelCatalog>()));
        services.AddSingleton(sp =>
        {
            var tokenUsageLocal = sp.GetRequiredService<agent.modelqueue.TokenUsageService>();
            var routerLocal = new agent.modelqueue.ModelQueueRouter(
                sp.GetRequiredService<agent.modelqueue.ModelCatalog>(),
                sp.GetRequiredService<IHttpClientFactory>(),
                sp.GetRequiredService<Microsoft.Extensions.Logging.ILogger<IndustrialAgentV2>>(),
                tokenUsage: tokenUsageLocal,
                localPort: sp.GetService<agent.modelqueue.ILocalGenerationPort>());
            // auto 选模主路径余额感知 — EstimateBalance (含 CNY→USD 换算) 注入排序强降权
            routerLocal.Scheduler.BalanceProbe = tokenUsageLocal.EstimateBalance;
            return routerLocal;
        });
        // R413: 本地生成执行面端口 (llama.cpp 长驻 llama-server; 进程 + HTTP, 零 P/Invoke)。
        // 通道开关在 config 的 local 段 (catalog.LocalChannel.IsReady) — 未配置 ⇒ 判据必拒 = 零回归;
        // 端口 IsAvailable 为**真实探测** (gguf 存在 ∧ 二进制可解析), 探测不确定不得当可用。
        // R464: 路径解析走**三态** (未声明 / 配置可用 / 配置错配)。原接线 `lc.IsReady ? lc.ModelPath : baseOpts.ModelPath`
        //   把「配置错配」当「未配置」⇒ **静默改用默认权重**, 既不告警也不留痕 ⇒ 以权重档位为单变量的测量
        //   在该配置下读数是错的且看不出来 (R463 负控 BP 因此 VOID)。现在: 声明即意图, 错配 ⇒ 通道不可用 +
        //   必落告警 (ILogger + stderr), **绝不替换**。
        services.AddSingleton<agent.modelqueue.ILocalGenerationPort>(sp =>
        {
            var baseOpts = agent.llamacpp.LlamaCppGeneratorOptions.FromEnvironment();
            var lc = sp.GetRequiredService<agent.modelqueue.ModelCatalog>().LocalChannel;
            var wiring = agent.llamacpp.LocalChannelWiring.ResolveForHost(lc.Declared, lc.ModelPath, baseOpts.ModelPath);
            if (wiring.Warning is not null)
            {
                // 仪器异常必留痕 (双通道: DI logger + stderr —— headless 宿主也必须可见; 标记 ASCII 便于机检)
                sp.GetService<Microsoft.Extensions.Logging.ILoggerFactory>()
                  ?.CreateLogger("agent.llamacpp.LocalChannelWiring")
                  .LogWarning("{LocalChannelWiringWarning}", wiring.Warning);
                Console.Error.WriteLine("[warn] " + wiring.Warning);
            }
            var opts = new agent.llamacpp.LlamaCppGeneratorOptions
            {
                ModelPath = wiring.ModelPath,
                BinaryPath = baseOpts.BinaryPath,
                BinaryEnvVar = baseOpts.BinaryEnvVar,
                ContextSize = wiring.UseConfiguredWidths && lc.ContextSize > 0 ? lc.ContextSize : baseOpts.ContextSize,
                Threads = baseOpts.Threads,
                Parallel = wiring.UseConfiguredWidths && lc.Parallel > 0 ? lc.Parallel : baseOpts.Parallel,
                StartTimeoutMs = baseOpts.StartTimeoutMs,
                AllowRestart = baseOpts.AllowRestart,
                MaxTokens = lc.MaxTokens > 0 ? lc.MaxTokens : baseOpts.MaxTokens,
            };
            return new agent.llamacpp.LlamaCppLocalGenerationPort(opts);
        });
        // R456 动作环: 执行面端口 (可替换)。默认实现 = 工作区受限文件/命令端口;
        //   AGENTFRAMEWORK_WORKSPACE 指定工作区根 (缺省 = 进程 cwd)。
        //   AGENTFRAMEWORK_ACTION_LOOP=off 可整体关闭 (关闭时请求体与旧版逐字节相同)。
        services.AddSingleton<agent.modelqueue.IActionPort>(_ =>
            agent.action.WorkspaceActionPort.FromEnvironment(Environment.CurrentDirectory));
        services.AddSingleton<ModelQueueAdapter>();
        services.AddSingleton<ILLMCaller>(sp => sp.GetRequiredService<ModelQueueAdapter>());
        services.AddSingleton<agent.subagent.ILLMCallerForIsolated>(sp => sp.GetRequiredService<ModelQueueAdapter>());
        // v0.11.0 (打点驱动修复): IsolatedTaskRunner DI 缺注册 — 隔离子代理链路整体休眠 (1.4 判定恒跳过)
        services.AddSingleton(sp => new agent.subagent.IsolatedTaskRunner(
            sp.GetRequiredService<ISessionManager>(),
            sp.GetRequiredService<agent.subagent.ILLMCallerForIsolated>(),
            sp.GetRequiredService<Microsoft.Extensions.Logging.ILogger<IndustrialAgentV2>>()));
        services.AddSingleton(sp => new agent.modelqueue.BalanceQueryService(
            sp.GetRequiredService<agent.modelqueue.ModelCatalog>(),
            sp.GetRequiredService<IHttpClientFactory>()));
        services.AddSingleton(sp => new agent.modelqueue.ModelVerifyService(
            sp.GetRequiredService<agent.modelqueue.ModelCatalog>(),
            sp.GetRequiredService<IHttpClientFactory>()));

        // v7.15 P2: ConfigSnapshot 统一注册 (宿主未注册时兜底 — Skill/ModelCatalog DI 依赖)
        services.TryAddSingleton(sp => new agent.config.ConfigSnapshot());

        // v7.15 Skill 调度 (P1): skills/ 目录静态加载 + 触发匹配 + 口径承载
        // v0.16.0-a (用户钦定): 外挂 skills 目录/单文件合并注册 + blacklist 过滤
        //   env AGENTFRAMEWORK_SKILLS_EXTRA_DIRS / _FILES / _BLACKLIST (CLI --skills-* 写入, 分号分隔)。
        //   外挂与内置不冲突: 同 SkillId 时外挂覆盖内置 (后注册者胜 — Register 语义确认)。
        services.AddSingleton(sp =>
        {
            var registry = agent.skills.SkillRegistry.LoadFromDirectory("skills");
            var extraDirs = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_SKILLS_EXTRA_DIRS");
            if (!string.IsNullOrEmpty(extraDirs))
            {
                foreach (var dir in extraDirs.Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
                {
                    if (!Directory.Exists(dir))
                        continue;
                    foreach (var pkg in agent.skills.SkillPackageLoader.LoadPackages(dir))
                        registry.Register(pkg); // 同 Id 覆盖内置 (外挂优先)
                }
            }
            var extraFiles = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_SKILLS_EXTRA_FILES");
            if (!string.IsNullOrEmpty(extraFiles))
            {
                foreach (var file in extraFiles.Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
                {
                    if (!File.Exists(file))
                        continue;
                    var pkg = agent.skills.SkillPackageLoader.LoadPackage(
                        Path.GetDirectoryName(Path.GetFullPath(file))!);
                    if (pkg is not null)
                        registry.Register(pkg); // 单 SKILL.md 文件 (取其所在目录解析)
                }
            }
            var blacklist = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_SKILLS_BLACKLIST");
            if (!string.IsNullOrEmpty(blacklist))
            {
                foreach (var bl in blacklist.Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
                    registry.RemoveById(bl); // 精确 Id 或目录名前缀匹配 (RemoveById 实现)
            }
            return registry;
        });
        // v0.11.0 (打点驱动补全): executive skill 包内脚本执行链路 — DI 缺 scriptRunner 注入,
        // 实测 wordcount 正则命中后静默降级 LLM (脚本从未运行)
        services.AddSingleton(sp => new agent.skills.SkillScriptRunner(
            getConfig: (module, key, fallback) => sp.GetRequiredService<agent.config.ConfigSnapshot>()
                .Get(module, key, fallback)));
        services.AddSingleton(sp => new agent.skills.SkillDispatcher(
            sp.GetRequiredService<agent.skills.SkillRegistry>(),
            new agent.skills.TriggerMatcher(
                sp.GetRequiredService<agent.contextgradient.ITextEmbedder>()),
            getConfig: (module, key, fallback) => sp.GetRequiredService<agent.config.ConfigSnapshot>()
                .Get(module, key, fallback),
            scriptRunner: sp.GetRequiredService<agent.skills.SkillScriptRunner>()));

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
