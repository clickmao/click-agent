using Microsoft.Extensions.Logging;
using agent.core;
using agent.workspace;
using agent.codegen;
using agent.recovery;
using agent.vectormemory;
using agent.memory;
using agent.templates;
using agent.search;
using agent.subagent;
using agent.session;
using agent.userinteraction;
using agent.context;
using agent.rag;
using agent.tendency;
using agent.tokencompression;
using agent.registry;

using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text;

using agent.intent;

namespace agent;

/// <summary>
/// 改进版工业Agent - 真正将上下文注入到 LLM Prompt
/// 
/// 核心改进：
/// 1. 使用 PromptBuilder 构建真正发给 LLM 的 Prompt
/// 2. 上下文被整合到 System Prompt 中，而非只是展示
/// 3. 支持带历史的对话 Prompt
/// </summary>
/// <summary>
/// R379: 缓存前缀治理 — 会话 → (冻结的系统提示, 冻结时意图)。
/// messages[0] 必须会话内恒定字节, 否则 provider 的缓存前缀自字节 0 失配。
/// </summary>
public sealed class FrozenSystemPromptTable
{
    private readonly System.Collections.Concurrent.ConcurrentDictionary<string, (string Prompt, string Intent)> _map =
        new(StringComparer.Ordinal);

    public int Count => _map.Count;
    public void Clear() => _map.Clear();

    public (string Prompt, string Intent) GetOrAdd(string sessionId, (string Prompt, string Intent) seed)
        => _map.GetOrAdd(sessionId, seed);

    public bool TryGet(string sessionId, out (string Prompt, string Intent) value)
        => _map.TryGetValue(sessionId, out value);

    public void Set(string sessionId, (string Prompt, string Intent) value) => _map[sessionId] = value;
}

public class IndustrialAgentV2 : AgentBase
{
    /// <summary>R379: 会话冻结系统提示表 (缓存前缀铁律: messages[0] 会话内恒定字节)</summary>
    private readonly FrozenSystemPromptTable _frozenSystemPrompt = new();

    /// <summary>
    /// R379: 会话 → 已注入过的上下文行哈希 (动态块跨轮行级去重)。
    /// 已在前几轮追加区出现过的行不再重复注入 —— 历史里已有、信息不丢, 但每轮增量 token 大幅下降
    /// (实测每轮增量 ~850 token 而会话前缀仅 ~970 token → 不去重则命中率天花板仅 ~53%)。
    /// </summary>
    private readonly System.Collections.Concurrent.ConcurrentDictionary<string, SessionInjectionPlanner.InjectionLedger> _sessionSentLines = new(StringComparer.Ordinal);

    private readonly IWorkspace _workspace;
    private readonly ICodeGenerator _codeGenerator;
    private readonly agent.registry.AgentRegistry _agentRegistry;
    private readonly agent.registry.ResponseSegmentRouter _segmentRouter;
    private readonly agent.registry.ClarificationService _clarificationService;
    private readonly agent.userinteraction.IUserPromptService? _promptService; // v7.14: EvidenceGate→批量问询驱动 (null=静默跳过)
    private readonly string _dataStoragePath;
    private readonly IRecoverySystem _recoverySystem;
    private readonly IVectorStore _vectorStore;
    private readonly IRAGRecall? _ragRecall;
    private readonly agent.contextgradient.ITextEmbedder? _textEmbedder;
    private readonly string _instanceId = Guid.NewGuid().ToString("N")[..8];
    private agent.exploration.ThinkMemory? _thinkMemory;
    /// <summary>v0.13.3 R275: 联想库为**进程级**单例 (V2 实例可能每轮重建 — host 生命周期语义), 跨轮保留。
    private static readonly agent.exploration.ThinkMemory _thinkMemoryGlobal = LoadThinkMemory();

    /// <summary>R413: 门配置遥测只发一次 (进程级) — 让「臂B 有没有真的开门」可观测。</summary>
    private static int _gateConfigEmitted;
    private static readonly string _thinkMemoryPath = Path.Combine("./data", "think-memory.json");

    /// <summary>v0.13.3 R283: 联想库持久化 — 进程启动加载 (文件缺失/损坏 → 空库, 行为兼容)。</summary>
    private static agent.exploration.ThinkMemory LoadThinkMemory()
    {
        try
        {
            return agent.exploration.ThinkMemory.Load(Path.Combine("./data", "think-memory.json"));
        }
        catch
        {
            return new agent.exploration.ThinkMemory(new agent.exploration.ThinkMemoryConfig());
        }
    }
    /// <summary>v0.13.3 R282: 探索链接登记表 (进程级) — 上下文 URL 三信号预判+激活打点。</summary>
    private static readonly agent.exploration.LinkRegistry _linkRegistry = new();
    /// <summary>R307 (L1): 连续偏题轮计数 (≥2 触发轻牵引提示; 回归主题轮清零)。</summary>
    private static int _consecutiveDrift;
        // R315 (拉回率度量): clarify 问句发出后置位; 用户回锚轮 (≤2 轮内 isDrift=false) 时 Emit pulled_back。
        private static bool _clarifyArmed;
        // R326 (R-1 收敛): pivot/转向词表单一来源 (原 3 份拷贝已发散 — "不管之前" 仅 1.4 有)。
        private static readonly string[] PivotMarkers =
        {
            "不要之前", "不用之前", "放弃", "重新开始", "取消之前", "先不做", "不管之前",
            "算了", "改成", "改为", "换成", "不要了", "还是做", "换一个",
        };
        // v0.14.0 T2d: 修法记忆 (进程级单例, data/fix-memory.json 持久化)
        private static agent.critique.FixMemory? _fixMemory;
        // v0.15.2: 警告/铁律记忆 (guardrails.json 持久化) + 同会话去重集 (habituation 防护)
        private static agent.critique.GuardrailMemory? _guardrailMemory;
        // R326-f: KnowledgeHint skill 知识注入 (本轮待注入, prompt 装配时消费)
        private static string _pendingSkillKnowledge = string.Empty;
        private static int _skillKnowledgeInjected;
        private static readonly HashSet<string> _injectedGuardrails = new();
        private static int _clarifyTurnsLeft;  // v0.11.0 R6: 存储召回同源修复
    private readonly agent.exploration.ContextBudgetGate _contextGate = new();  // v0.13.3 M2: 上下文预算门
    private readonly IVectorMemoryRecall _memoryRecall;
    private readonly ITemplateStore _templateStore;
    private readonly ISearchService _searchService;
    private readonly ISubAgentPool _subAgentPool;
    private readonly ISessionManager _sessionManager;
    private readonly IUserInteraction _userInteraction;
    private readonly IContextAssembler _contextAssembler;
    private readonly agent.session.JsonSessionMemoryStore _sessionMemoryStore; // v7.14 会话长期记忆落盘
    private readonly agent.registry.AgentProfileStore _agentProfileStore;      // v7.14 agent 画像
    private readonly agent.registry.CapabilityScanner _capabilityScanner;      // v7.14 能力清单 (扫描一次)
    private readonly ITendencyAnalyzer _tendencyAnalyzer;
    
    // ✅ 新增：Prompt 构建器
    private readonly IPromptBuilder _promptBuilder;
    
    // ✅ 新增：LLM 调用器（示例接口）
    private readonly ILLMCaller _llmCaller;

    // R374 (D3): 运行结果回流闭环 (懒构造: 复用本实例的段落路由器 + LLM 端口, 零构造签名变更)。
    private ArtifactRepairLoop? _artifactRepair;
    private readonly agent.subagent.IsolatedTaskRunner? _isolatedTaskRunner;
    private readonly System.Collections.Concurrent.ConcurrentDictionary<string, string> _lastReplyBySession = new();
    private readonly agent.roles.FailureClusters _failureClusters = new();

    /// <summary>R365: 纠正检测微 prompt 通道 (走模型队列; ~140 tok/次)。</summary>
    private async Task<(string Content, int TokensUsed)> DetectViaLlm(string prompt, int maxTokens)
    {
        var resp = await _modelRouter!.CallAsync(new agent.modelqueue.QueuePrompt
        {
            SystemPrompt = "只输出一个字母。",
            UserMessage = prompt,
            EstimatedTokens = prompt.Length / 2,
        }, agent.modelqueue.TaskKindHint.ContextCompression, "general", CancellationToken.None);
        return (resp.Success ? resp.Content : "", prompt.Length / 2 + resp.Content.Length / 2);
    }

    private readonly agent.modelqueue.ModelQueueRouter? _modelRouter;
    /// <summary>R363: 当前激活 Role 文档 (可空 — .rbin 未挂时 null, 行为与无 Role 完全一致)。</summary>
    public agent.roles.RoleBinaryFile.RoleDocument? ActiveRole { get; }

    /// <summary>R363: Role 成长账本 (仅挂载 .rbin 时非空 — 赏罚计数/置信度/倾向)。</summary>
    public agent.roles.RoleGrowthLedger? GrowthLedger { get; }
    private readonly string? _roleFilePath;

    /// <summary>R356-c: 前端 state.snapshot 真实状态快照 (零反射手写序列化由消费方做)。</summary>
    public sealed record AgentSnapshot(
        string SessionId,
        string? ModelId,
        string? ModelProvider,
        string SelectionBasis,
        string SelectionMode,
        int ModelSwitches,
        long UptimeMs);

    private readonly long _startTicks = Environment.TickCount64;
    private readonly agent.modelqueue.BalanceQueryService? _balanceService;
    private readonly agent.modelqueue.TokenUsageService? _tokenUsageService;
    private readonly agent.modelqueue.ModelVerifyService? _verifyService;
    private readonly agent.logging.LogRouter? _logRouter;

    /// <summary>
    /// R21: 简单意图启发式 — 问候/闲聊/单句解释/事实问答走轻思考 (省 reasoning token 与延迟)。
    /// 复杂信号 (多步/代码/分析/对比/计划/长输入) 一律保留默认深推理, 宁可多花不可降智。
    /// </summary>
        /// <summary>
    /// v0.13.3 R286: 思考链宿主循环 (任务1 收口)。播种 = 消息+上下文中的 URL/目录线索;
    /// 循环 = TryDequeueNext → HostExploreExecutor 执行 → Record (发现入队, per-source 预算内);
    /// 收敛 = 预算/无新发现/步数; 产出 = 各步 digest 拼接 (回注预算内截断)。
    /// 打点: think_chain (steps, ok, ms, digest_len)。
    /// </summary>
    private static async Task<string> RunThinkChainAsync(string messageContent, string contextPrompt, CancellationToken ct)
    {
        // R287: A/B 开关 (AGENTFRAMEWORK_EXPLORE=0 → 探索链全关, explore_eval 对照组语义)
        if (Environment.GetEnvironmentVariable("AGENTFRAMEWORK_EXPLORE") == "0")
            return string.Empty;
        try
        {
            var planner = new agent.exploration.ExplorationPlanner(new agent.exploration.ExplorationConfig());
            var seeded = 0;
            foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(
                         messageContent + " " + contextPrompt, @"https?://[^\s,，。;；)" + "\"" + "'" + "]+"))
            {
                var u = m.Value.TrimEnd('.', ',', ')', '}', ']', '"', '\'');
                if (u.Length > 8 && u.Contains("example.com") == false) // example.com 演示域不探索
                {
                    planner.Seed(agent.exploration.ExploreSourceKind.Url, u, fromContext: true, discoveredFrom: null);
                    seeded++;
                }
            }
            if (seeded == 0) return string.Empty;

            var executor = new agent.exploration.HostExploreExecutor("./");
            var session = new agent.exploration.ThinkChainSession(planner, memory: null, deadlineMs: 4000);
            var sw = System.Diagnostics.Stopwatch.StartNew();
            var sb = new System.Text.StringBuilder();
            var steps = 0;
            while (!planner.BudgetExhausted && steps < 4 && sw.ElapsedMilliseconds < 4000)
            {
                var node = planner.TryDequeueNext();
                if (node == null) break;
                var result = await session.ExecuteStepAsync(node, executor, ct);
                if (result == null) break;
                steps++;
                if (result.Ok && !string.IsNullOrEmpty(result.Digest))
                {
                    sb.AppendLine($"[{node.Kind}:{Truncate(node.Ref, 60)}] {Truncate(result.Digest, 400)}");
                }
                if (!result.Ok) break; // 首败即停 (探索是增强, 不拖主链)
            }
            agent.config.AgentTelemetry.Emit("think_chain", "IndustrialAgentV2",
                ("seeded", seeded), ("steps", steps), ("ms", (int)sw.ElapsedMilliseconds),
                ("digest_len", sb.Length));
            return sb.ToString();
        }
        catch (OperationCanceledException) { throw; }
        catch (Exception ex)
        {
            agent.config.AgentTelemetry.Emit("think_chain", "IndustrialAgentV2",
                ("error", ex.Message[..Math.Min(60, ex.Message.Length)]));
            return string.Empty;
        }
    }

    private static string Truncate(string s, int n) => s.Length <= n ? s : s[..n] + "…";

    /// <summary>
    /// v0.13.3 B2 (R274): 微步骤隔离执行宿主链。子任务 → MicroQuestion (回注上下文=空, 主上下文不复制)
    /// → 独立微 prompt 逐条问询 (与主链同一 LLM 通道, 但 prompt 只有微问题本身 — 隔离语义) →
    /// MicroStepSession.Record (失败计数/升级联动) → 回注摘要 (≤200 tok/条)。
    /// 打点: micro_step (per-micro: ok/tokens/ms) + micro_session (汇总)。
    /// </summary>
    private async Task<string> RunMicroStepsAsync(IReadOnlyList<IntentDecomposer.SubTask> subTasks, string intent, CancellationToken ct)
    {
        var session = new agent.exploration.MicroStepSession();
        var sb = new System.Text.StringBuilder();
        foreach (var st in subTasks)
        {
            var mq = new agent.exploration.MicroQuestion
            {
                Question = st.Text,
                ForwardRefs = new List<string>(),
                InjectedContext = string.Empty,
            };
            var sw = System.Diagnostics.Stopwatch.StartNew();
            string answer;
            try
            {
                var microPrompt = new Prompt
                {
                    UserMessage = $"[微步骤隔离问询] {mq.Question}\n(只回答本微问题, 不引申)",
                    SystemPrompt = "你是隔离执行的微步骤助手: 只回答给出的微问题本身, 不引用任何外部会话历史。",
                    EstimatedTokens = 100,
                };
                var resp = await _llmCaller.CallAsync(microPrompt, ct);
                answer = resp.Content ?? string.Empty;
            }
            catch (OperationCanceledException) { throw; }
            catch (Exception ex)
            {
                answer = string.Empty;
                agent.config.AgentTelemetry.Emit("micro_step", "IndustrialAgentV2",
                    ("id", mq.Id), ("ok", false), ("error", ex.Message[..Math.Min(80, ex.Message.Length)]));
            }
            sw.Stop();
            var result = new agent.exploration.MicroStepResult
            {
                MicroId = mq.Id,
                Ok = answer.Length > 0,
                Answer = answer,
                Ms = (int)sw.ElapsedMilliseconds,
            };
            session.Record(result);
            agent.config.AgentTelemetry.Emit("micro_step", "IndustrialAgentV2",
                ("id", mq.Id), ("ok", result.Ok), ("tokens", result.TokensUsed), ("ms", result.Ms));
            var summary = session.BuildRestoreSummary(result);
            if (summary.Length > 0) sb.AppendLine(summary);
        }
        agent.config.AgentTelemetry.Emit("micro_session", "IndustrialAgentV2",
            ("count", subTasks.Count), ("failures", session.ConsecutiveFailures));
        return sb.ToString();
    }

private static bool IsSimpleIntentForReasoning(string intent, string userMessage)
    {
        // 复杂信号优先: 命中即深推理
        if (userMessage.Contains("分析") || userMessage.Contains("对比") || userMessage.Contains("设计") ||
            userMessage.Contains("实现") || userMessage.Contains("写一个") || userMessage.Contains("调研") ||
            userMessage.Contains("计划") || userMessage.Contains("为什么") || userMessage.Contains("原因") ||
            userMessage.Contains("优化") || userMessage.Contains("报告") || userMessage.Contains("步骤") ||
            userMessage.Length > 120)
            return false;
        // 简单意图: general/小任务 (解释/转换/查询类短句)
        return intent is "general" or "smalltalk" or "search" && userMessage.Length <= 120;
    }
    private readonly agent.skills.SkillDispatcher? _skillDispatcher;

    private agent.staging.ApprovalController? _staging;
    private agent.staging.ApprovalController Staging()
        => _staging ??= new agent.staging.ApprovalController(new agent.staging.StagedFileStore());

    private agent.activity.ActivityService? _activity;
    private agent.activity.ActivityService Activity()
        => _activity ??= new agent.activity.ActivityService();

    private static string RenderGit(agent.gitops.GitOperations.GitResult r)
        => r.Ok ? (string.IsNullOrWhiteSpace(r.StdOut) ? "(ok, 无输出)" : r.StdOut.Trim())
                : $"✗ git 失败 (exit {r.ExitCode}): {r.ErrorSummary}";

    // v0.17.2-b/c (R337): 脚本插件服务 + 条件定时调度器 (惰性; 教训 sink → 真实 ExecutorLessonMemory 落盘)
    private agent.skills.ScriptPluginRunner? _scriptPlugin;
    private agent.skills.ConditionalScriptScheduler? _scriptScheduler;
    private agent.skills.ScriptPluginRunner ScriptPlugin()
        => _scriptPlugin ??= new agent.skills.ScriptPluginRunner(lessonSink: RecordScriptLesson);
    private agent.skills.ConditionalScriptScheduler ScriptScheduler()
        => _scriptScheduler ??= new agent.skills.ConditionalScriptScheduler(
            ScriptPlugin(), () => { try { return Activity().IsOtherAgentBusy(); } catch { return false; } });
    private static void RecordScriptLesson(string pattern, string summary, string? solution, string? context)
    {
        try { agent.execution.ExecutorLessonMemory.Default.Record(pattern, summary, solution, context); }
        catch { /* 教训持久化失败不阻塞主链 */ }
    }

    /// <summary>v0.17.2-a (R336): 进程优雅退出时清自身活动心跳文件 (host finally 调用; kill -9 由 TTL 兜底)。</summary>
    public void ClearActivity()
    {
        try { _activity?.Clear(); } catch { /* 静默 — 退出清理不可阻塞 */ }
    }
    
    private readonly List<string> _capabilities = new();
    
    private readonly int _maxTokenBudget = 8000;
    
    public IndustrialAgentV2(
        ILogger<IndustrialAgentV2> logger,
        IEnumerable<IMessageHandler> handlers,
        IWorkspace workspace,
        ICodeGenerator codeGenerator,
        IRecoverySystem recoverySystem,
        IVectorStore vectorStore,
        IVectorMemoryRecall memoryRecall,
        ITemplateStore templateStore,
        ISearchService searchService,
        ISubAgentPool subAgentPool,
        ISessionManager sessionManager,
        IUserInteraction userInteraction,
        IContextAssembler contextAssembler,
        ITendencyAnalyzer tendencyAnalyzer,
        IPromptBuilder promptBuilder,
        ILLMCaller llmCaller,
        agent.registry.AgentRegistry agentRegistry,
        agent.registry.ResponseSegmentRouter segmentRouter,
        agent.registry.ClarificationService clarificationService,
        string dataStoragePath = "./data",
        agent.userinteraction.IUserPromptService? promptService = null,
        agent.subagent.IsolatedTaskRunner? isolatedTaskRunner = null,
        agent.modelqueue.ModelQueueRouter? modelRouter = null,
        agent.modelqueue.BalanceQueryService? balanceService = null,
        agent.modelqueue.TokenUsageService? tokenUsageService = null,
        agent.modelqueue.ModelVerifyService? verifyService = null,
        agent.logging.LogRouter? logRouter = null,
        agent.skills.SkillDispatcher? skillDispatcher = null,
        IRAGRecall? ragRecall = null,
        agent.contextgradient.ITextEmbedder? textEmbedder = null,
        string? roleFilePath = null,
        byte[]? roleMasterKey = null,
        agent.intent.PlanRunner? planRunner = null) : base(logger, handlers)
    {
        _isolatedTaskRunner = isolatedTaskRunner;
        // R363: roleFilePath 未传时回退 env (DI 无参构造场景 — Program --role 解析后写入)。
        // 密钥: data/master.key 持久主密钥 (与 credentials.json 同层级 — 跨会话可解, 换机不可解)。
        roleFilePath ??= Environment.GetEnvironmentVariable("AGENTFRAMEWORK_ROLE_FILE");
        _roleFilePath = roleFilePath;
        if (roleFilePath is not null && File.Exists(roleFilePath))
        {
            var key = roleMasterKey ?? agent.userinteraction.CredentialEncryption.LoadOrCreateMasterKey("data");
            ActiveRole = agent.roles.RoleBinaryFile.Read(roleFilePath, key);
            GrowthLedger = new agent.roles.RoleGrowthLedger(ActiveRole.Id, Path.Combine("data", "roles"));
            GrowthLedger.SeedFrom(ActiveRole.Growth); // 文档内计数播种 (文件无增量时生效)
        }
        _modelRouter = modelRouter;
        _balanceService = balanceService;
        _tokenUsageService = tokenUsageService;
        _verifyService = verifyService;
        _logRouter = logRouter;
        _skillDispatcher = skillDispatcher;
        _promptService = promptService;
        _workspace = workspace;
        _codeGenerator = codeGenerator;
        _recoverySystem = recoverySystem;
        _vectorStore = vectorStore;
        _memoryRecall = memoryRecall;
        _ragRecall = ragRecall;
        _textEmbedder = textEmbedder;
        _thinkMemory = _thinkMemoryGlobal;
        agent.config.AgentTelemetry.Emit("think_memory_boot", "IndustrialAgentV2",
            ("embedder_injected", textEmbedder is not null),
            ("available", textEmbedder is { IsAvailable: true }),
            ("instance", Guid.NewGuid().ToString("N")[..8]));
        _templateStore = templateStore;
        _searchService = searchService;
        _subAgentPool = subAgentPool;
        _sessionManager = sessionManager;
        _userInteraction = userInteraction;
        _contextAssembler = contextAssembler;
        _tendencyAnalyzer = tendencyAnalyzer;
        _promptBuilder = promptBuilder;
        _llmCaller = llmCaller;
        _agentRegistry = agentRegistry;
        _segmentRouter = segmentRouter;
        _planRunner = planRunner;
        _clarificationService = clarificationService;
        _dataStoragePath = dataStoragePath;
        _sessionMemoryStore = new agent.session.JsonSessionMemoryStore(_dataStoragePath);
        _agentProfileStore = new agent.registry.AgentProfileStore(_dataStoragePath);
        _capabilityScanner = new agent.registry.CapabilityScanner();
        _capabilityScanner.Scan(); // 启动时探嗅一次 (⑤)
        
        Name = "IndustrialAgentV2";
        InitializeCapabilities();
    }
    
    private void InitializeCapabilities()
    {
        _capabilities.AddRange(new[]
        {
            "多数据源上下文注入", "意图识别", "代码生成/修改/审查",
            "任务规划", "记忆召回", "网络搜索", "错误恢复"
        });
    }
    
    /// <summary>
    /// v0.11.0 R14: goal 锚定收窄 — 偏好陈述/寒暄 ("我喜欢简洁") 不该锚成项目目标,
    /// 否则后续正常问题全部"实体零重叠"被误隔离。仅任务性消息锚定。
    /// </summary>
    private static bool IsGoalWorthy(string content)
    {
        if (string.IsNullOrWhiteSpace(content) || content.Length < 8)
            return false;
        // v0.11.0 R26 (真 bug 22): 记忆性/偏好性陈述不是任务目标 — "记住我的项目名是X"
        // 曾因裸词"项目"命中被锚成 goal, 导致后续 8 轮全部"实体零重叠"误隔离 (长会话实测)。
        // R306 (L1 GoalText 锚定修复): 复合句 "做一个X项目, 记住这个背景" — 任务标记在场时
        // 任务优先 (记忆注记只是附带), 不被 memoryMarkers 误杀 (牵引实验轮1 实证 GoalText 空)。
        string[] taskMarkersPre =
        {
            "帮我", "请帮我", "需要你", "做一个", "开发一个", "实现一个", "项目目标", "项目需求",
            "这个项目", "目标是", "计划", "写一个", "修复", "重构", "部署", "上线", "排查", "设计一个",
        };
        if (taskMarkersPre.Any(m => content.Contains(m, StringComparison.Ordinal)))
            return true;
        string[] memoryMarkers = { "记住", "记一下", "记着", "我喜欢", "我的名字", "我叫" };
        if (memoryMarkers.Any(m => content.Contains(m, StringComparison.Ordinal)))
            return false;
        string[] taskMarkers =
        {
            "帮我", "请帮我", "需要你", "做一个", "开发一个", "实现一个", "项目目标", "项目需求",
            "这个项目", "目标是", "计划", "任务", "写一个", "修复", "重构", "部署", "上线", "排查", "设计一个",
        };
        return taskMarkers.Any(m => content.Contains(m, StringComparison.Ordinal));
    }

    protected override async Task<AgentResponse> OnProcessAsync(Message message, CancellationToken ct)
    {
        var startTime = DateTime.UtcNow;
        // v0.17.2-a (R336): 活动心跳 — 每轮注册本进程活动 (任务摘要), 退出由 10s TTL 过期自清
        try { Activity().Heartbeat(message.Content); } catch { /* 活动感知不阻塞主链 */ }
        var response = new AgentResponse();
        
        try
        {
            // 0.-1 /plan 计划查询 (v7.15 T.4-4; v0.22.0 exp9: 加"已路由计划 + 真执行结论"两段)
            if (message.Content.Trim().Equals("/plan", StringComparison.OrdinalIgnoreCase))
            {
                response.Success = true;
                if (_lastPlan is null && _lastPlanRun is null)
                {
                    response.Content = "{\"plan\": null, \"hint\": \"尚无计划记录 — 发送一条多子任务消息后再查\"}";
                }
                else
                {
                    // 每节点: 位置 (local/remote/hybrid) + 执行器 + 状态/耗时/tokens — 前端直接可画
                    var planJson = _lastPlan is null ? "null" : TaskPlanJsonContext.ToJson(_lastPlan);
                    var runJson = _lastPlanRun is null ? "null" : TaskPlanJsonContext.ToJson(_lastPlanRun);
                    var local = _lastPlan?.Nodes.Count(n => n.RunsLocally) ?? 0;
                    var remote = _lastPlan?.Nodes.Count(n => n.Location == NodeExecutionLocation.Remote) ?? 0;
                    var localTokens = _lastPlanRun?.Outcomes.Where(o => o.Location is "local" or "hybrid").Sum(o => o.Tokens) ?? 0;
                    // D6: 计划级 KPI 一并回给前端 (本地先行节点数/真重叠 ms/远程等待 ms/本地 token) —
                    //     "本地先行到底省了什么"必须由数字回答, 不能只给一句话。
                    var kpiJson = _lastPlanRun?.Kpi is { } kpi ? TaskPlanJsonContext.ToJson(kpi) : "null";
                    response.Content =
                        "{\"plan\":" + planJson + ",\"run\":" + runJson + ",\"kpi\":" + kpiJson +
                        ",\"routing\":{\"local\":" + local + ",\"remote\":" + remote +
                        ",\"local_tokens\":" + localTokens + "}}";
                }
                response.Data = new Dictionary<string, object> { { "localCommand", "plan" } };
                response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                return response;
            }

            // 0.-1c /rag (v0.13.0 用户钦定): RAG 数据文件查询/切换
            //   /rag          → 当前 RAG 数据文件路径 (JSON)
            //   /rag <path>   → 切换 RAG 数据文件 (设置 env 钩子 + DI 单例 override; 新文档落盘到新路径;
            //                    历史索引重载需重启进程 — 诚实提示)
            var trimmedRag = message.Content.Trim();
            if (trimmedRag.Equals("/rag", StringComparison.OrdinalIgnoreCase) ||
                trimmedRag.StartsWith("/rag ", StringComparison.OrdinalIgnoreCase))
            {
                var ragRecall = _ragRecall;
                var arg = trimmedRag.Length > 5 ? trimmedRag[5..].Trim() : "";
                if (arg.Length == 0)
                {
                    response.Success = true;
                    var currentPath = ragRecall?.CurrentPersistPath() ?? "";
                    response.Content = System.Text.Json.JsonSerializer.Serialize(
                        new RagInfoPayload { CurrentPath = currentPath, Override = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_RAG_PATH") ?? currentPath },
                        ModelCommandJsonContext.Default.RagInfoPayload);
                    response.Data = new Dictionary<string, object> { { "localCommand", "rag" } };
                    response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                    return response;
                }
                var fullRag = System.IO.Path.GetFullPath(arg);
                var ragDir = System.IO.Path.GetDirectoryName(fullRag);
                if (ragDir is not null && !System.IO.Directory.Exists(ragDir))
                    System.IO.Directory.CreateDirectory(ragDir);
                Environment.SetEnvironmentVariable("AGENTFRAMEWORK_RAG_PATH", fullRag);
                if (ragRecall is not null) ragRecall.SetPersistOverride(fullRag);
                response.Success = true;
                response.Content = System.Text.Json.JsonSerializer.Serialize(
                    new RagSwitchPayload { Path = fullRag, Reloaded = false, Hint = "RAG 数据文件已切换; 历史索引重载需重启进程 (诚实语义)" },
                    ModelCommandJsonContext.Default.RagSwitchPayload);
                response.Data = new Dictionary<string, object> { { "localCommand", "rag" } };
                response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                return response;
            }

            // 0.-1b /forecast 下轮预估查询 (v0.10.0 新需求4): 读回上轮落盘的下轮预估
            // (NextTurnForecast v7.11 内部机制 — 用户钦定补前端指令; 无记录 → 诚实 null 提示)
            if (message.Content.Trim().Equals("/forecast", StringComparison.OrdinalIgnoreCase))
            {
                var forecastIdentity = _agentRegistry.Get(message.SenderId is { Length: > 0 } ? message.SenderId : "main")
                                ?? _agentRegistry.Main;
                var fc = agent.registry.NextTurnForecast.Load(_dataStoragePath, forecastIdentity.Uid);
                response.Success = true;
                response.Content = fc is null
                    ? "{\"forecast\": null, \"hint\": \"\u5c1a\u65e0\u4e0b\u8f6e\u9884\u4f30 \u2014 \u5b8c\u6210\u4e00\u8f6e\u4efb\u52a1\u540e\u81ea\u52a8\u751f\u6210\"}"
                    : System.Text.Json.JsonSerializer.Serialize(
                        new ForecastPayload
                        {
                            AgentUid = fc.AgentUid,
                            TaskSummary = fc.TaskSummary,
                            LastIntent = fc.LastIntent,
                            Tendency = fc.Tendency,
                            ContinuationHint = fc.ContinuationHint,
                            LikelyContinues = fc.LikelyContinues,
                            TurnCount = fc.TurnCount,
                            UpdatedAt = fc.UpdatedAt,
                        }, ModelCommandJsonContext.Default.ForecastPayload);
                response.Data = new Dictionary<string, object> { { "localCommand", "forecast" } };
                response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                return response;
            }

            // 0.-2 /model 与 /balance (v7.15 模型队列): 切换/恢复自动 + 余额查询 + 目录校验 (全 JSON 输出)
            var trimmedCmd = message.Content.Trim();
            if (trimmedCmd.Equals("/log", StringComparison.OrdinalIgnoreCase) ||
                trimmedCmd.StartsWith("/log ", StringComparison.OrdinalIgnoreCase))
            {
                var logResp = HandleLogCommand(trimmedCmd, message.SessionId,
                    (long)(DateTime.UtcNow - startTime).TotalMilliseconds);
                if (logResp != null)
                {
                    return logResp;
                }
            }

            if (trimmedCmd.StartsWith("/model", StringComparison.OrdinalIgnoreCase) ||
                trimmedCmd.StartsWith("/token", StringComparison.OrdinalIgnoreCase) ||
                trimmedCmd.Equals("/balance", StringComparison.OrdinalIgnoreCase) || 
                trimmedCmd.StartsWith("/balance ", StringComparison.OrdinalIgnoreCase))
            {
                var cmdResp = HandleModelCommand(trimmedCmd, (long)(DateTime.UtcNow - startTime).TotalMilliseconds);
                if (cmdResp != null)
                {
                    return cmdResp;
                }
            }

            // 0.-3 Skill 调度 (v7.15 S.3 阶段一): 推理前激活判定 — 命中即走 Skill 流程 (force_use 承载口径)
            if (_skillDispatcher != null &&
                !trimmedCmd.StartsWith('/'))  // 本地指令不走 Skill
            {
                var skillResult = await _skillDispatcher.DispatchAsync(message.Content, ct);
                // v0.11.0 (打点驱动修复): executive 脚本成功输出同样直接承载 —
                // 原 ForceUse-only 导致脚本输出被丢弃、静默降级 LLM (实测 wordcount 链路)
                // v0.11.0 R83 (真缺陷 34): 失败 skill 的错误 JSON (Content 非空但 Success=false) 原样直出
                // 给用户 ({"error":"no_pattern_match"}) — 失败必须静默降级 LLM, 成功才承载。
                if (skillResult is { Success: true } && (skillResult.ForceUse || skillResult.Content.Length > 0))
                {
                    // R326-f (KnowledgeHint): 知识提示型命中 → SKILL.md body 作系统侧知识注入, 回复仍走主链 LLM
                    if (skillResult.IsKnowledgeHint)
                    {
                        _skillKnowledgeInjected += skillResult.Content.Length;
                        _logger.LogInformation("Skill {SkillId} knowledge-hint injected ({Chars}ch)",
                            skillResult.SkillId, skillResult.Content.Length);
                        agent.config.AgentTelemetry.Emit("skill_knowledge", "IndustrialAgentV2",
                            ("skill", skillResult.SkillId), ("chars", skillResult.Content.Length));
                        // 注入到 prompt 知识区: 记入待注入变量, 主链装配时加 (见 prompt 构建处)
                        _pendingSkillKnowledge = skillResult.Content;
                    }
                    else if (skillResult.Success && (skillResult.ForceUse || !string.IsNullOrEmpty(skillResult.Content)))
                    {
                    _logger.LogInformation("Skill {SkillId} activated ({Mode}, {Ms}ms)",
                        skillResult.SkillId, skillResult.ForceUse ? "force_use" : "executive", skillResult.ElapsedMs);
                    response.Success = true;
                    response.Content = skillResult.Content;
                    response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                    // v0.11.0 R62: executive 直达同样进 loop_turn 打点 (原提前 return 造成度量盲区)
                    agent.config.AgentTelemetry.Emit("loop_turn", "IndustrialAgentV2",
                        ("total_ms", response.ExecutionTimeMs), ("success", true),
                        ("reply_chars", response.Content.Length), ("asked", false),
                        ("executive", true), ("skill", skillResult.SkillId));
                    // R309 (缺陷 72 修复): executive 直达补 intent 打点 — 原 return 在 intent 打点 (L507) 前,
                    // C04/C06 类用例 summarize intent=None (批244 起的结构性观测盲区)。
                    var _execSubTasks = IntentDecomposer.Decompose(message.Content);
                    agent.config.AgentTelemetry.Emit("intent", "IndustrialAgentV2",
                        ("primary", IntentDecomposer.PrimaryIntent(_execSubTasks)),
                        ("subtask_count", _execSubTasks.Count),
                        ("input_chars", message.Content.Length), ("executive", true));
                    return response;
                    }
                }
                // 未命中/失败/禁语拦截 → 静默降级普通推理 (S.5: 用户无感)
            }

            // 0. 非 LLM 本地强制指令拦截 (v7.11): /stop /continue 等, 不进意图识别/LLM
            var localCommand = agent.registry.LocalCommandRouter.TryRoute(message.Content);
            // v0.18.0 T2 (R339, 用户钦定防幻觉假执行): fail-closed 硬闸 — Known 指令若 TryRoute 未路由
            // (拦截链断裂: Known 加了忘 switch 臂/豁免) → 返回内部错误,**绝不送 LLM** (模型会假装执行
            // 并编造假输出 — /skills 首版 + /git AOT 首测两度实证)。记录教训供下次注入。
            if (!localCommand.Handled)
            {
                var breakInput = message.Content.Trim();
                var firstWord = breakInput.Split(' ', 2, StringSplitOptions.RemoveEmptyEntries).FirstOrDefault() ?? "";
                if (firstWord.StartsWith('/') && agent.registry.LocalCommandRouter.KnownCommands.Contains(firstWord))
                {
                    agent.config.AgentTelemetry.Emit("route_break", "IndustrialAgentV2",
                        ("cmd", firstWord), ("input_len", breakInput.Length));
                    agent.execution.ExecutorLessonMemory.Default.Record($"route-break:{firstWord}",
                        $"本地指令 {firstWord} 路由断裂 (Known 含但 TryRoute NotCommand) — 已硬闸阻止送 LLM",
                        "检查 Known/switch 臂/PreRoutedCommands 三表一致性 (v0.18.0 T1 审计测试)",
                        "曾发生: /skills 与 /git 断裂 → LLM 幻觉假执行输出");
                    response.Content = $"⚠ 本地指令 {firstWord} 路由异常 (内部错误) — 已阻止送 LLM 防假执行。三表一致性见 v0.18.0 审计。";
                    response.Success = true;
                    response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                    return response;
                }
            }
            if (localCommand.Handled)
            {
                // v0.16.0-c (用户钦定): /skills 查询当前激活 (可匹配) 的全部 skills;
                // /skills-only <id,...> 动态 whitelist; /skills-exclude <id,...> 动态 blacklist (v0.16.0-b)。
                if (localCommand.Command is "skills" or "skills-only" or "skills-exclude")
                {
                    response.Success = true;
                    var registry = _skillDispatcher?.Registry;
                    if (registry is null)
                    {
                        response.Content = "skills 引擎未启用。";
                    }
                    else if (localCommand.Command == "skills")
                    {
                        var all = registry.All;
                        var sb2 = new System.Text.StringBuilder($"📚 当前激活 skills ({all.Count}):\n");
                        foreach (var sk in all)
                            sb2.Append($"- {sk.SkillId} (v{sk.Version}, {sk.Type}, 触发词: {string.Join("/", sk.Keywords.Take(3))})\n");
                        response.Content = sb2.ToString();
                    }
                    else
                    {
                        var ids = (localCommand.Argument ?? "").Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
                        if (localCommand.Command == "skills-only") registry.SetActiveWhitelist(ids.Length > 0 ? ids : null);
                        else registry.SetActiveBlacklist(ids.Length > 0 ? ids : null);
                        var joined = ids.Length > 0 ? string.Join(",", ids) : "清除";
                        response.Content = $"✓ 动态过滤已更新 ({localCommand.Command}: {joined})。当前可匹配 {registry.All.Count} 个。";
                    }
                    response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                    return response;
                }
                // v0.17.1 (R335): 离线变更审批 /staged /approve /reject /cleanup
                if (localCommand.Command is "staged" or "approve" or "reject" or "cleanup")
                {
                    response.Success = true;
                    try
                    {
                        var staging = Staging();
                        if (localCommand.Command == "staged")
                        {
                            var arg2 = (localCommand.Argument ?? "").Trim();
                            if (arg2.StartsWith("diff ", StringComparison.Ordinal))
                                response.Content = staging.Diff(arg2["diff ".Length..].Trim());
                            else
                                response.Content = staging.ListPending(arg2.Length > 0 ? arg2 : null);
                        }
                        else if (localCommand.Command == "approve")
                        {
                            var id = (localCommand.Argument ?? "").Trim();
                            if (string.Equals(id, "all", StringComparison.OrdinalIgnoreCase))
                            {
                                var store = new agent.staging.StagedFileStore();
                                var pending = store.All().Where(b => b.IsPending).ToList();
                                if (pending.Count == 0) { response.Content = "无待审批批次。"; }
                                else
                                {
                                    var parts2 = new System.Text.StringBuilder();
                                    foreach (var b in pending)
                                        parts2.AppendLine(staging.Apply(b.Id).Render());
                                    response.Content = parts2.ToString().TrimEnd();
                                }
                            }
                            else
                            {
                                response.Content = string.IsNullOrEmpty(id)
                                    ? "用法: /approve <批次id|all> (/staged 查看)"
                                    : staging.Apply(id).Render();
                            }
                        }
                        else if (localCommand.Command == "reject")
                        {
                            var id = (localCommand.Argument ?? "").Trim();
                            if (string.IsNullOrEmpty(id)) { response.Content = "用法: /reject <批次id>"; }
                            else if (new agent.staging.StagedFileStore().Find(id) is null) { response.Content = $"批次 {id} 不存在。"; }
                            else { staging.Reject(id); response.Content = $"✗ 批次 {id} 已标记 rejected (staging 内容保留, /cleanup 物理删除)。"; }
                        }
                        else // cleanup
                        {
                            var n = new agent.staging.StagedFileStore().Cleanup(includeExpired: false);
                            response.Content = n > 0 ? $"🗑 已清理 {n} 个 reclaimable 批次。" : "无 reclaimable 批次可清理。";
                        }
                    }
                    catch (Exception ex)
                    {
                        response.Content = $"staging 操作失败: {ex.Message}";
                    }
                    response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                    return response;
                }
                // v0.18.0 G1 (R338): /git status|diff|commit <msg>|push <一次性url>
                if (localCommand.Command == "git")
                {
                    response.Success = true;
                    try
                    {
                        var git = new agent.gitops.GitOperations(Environment.CurrentDirectory);
                        var arg2 = (localCommand.Argument ?? "").Trim();
                        if (arg2 == "status") response.Content = RenderGit(git.Status());
                        else if (arg2 == "diff") response.Content = RenderGit(git.DiffStat()) + "\n" + RenderGit(git.Diff());
                        else if (arg2.StartsWith("commit ", StringComparison.Ordinal))
                            response.Content = RenderGit(git.StageAndCommit(arg2["commit ".Length..].Trim()));
                        else if (arg2.StartsWith("push ", StringComparison.Ordinal))
                        {
                            var url = arg2["push ".Length..].Trim();
                            var p = git.PushOnce(url);
                            var verify = git.VerifyPush(url);
                            response.Content = RenderGit(p) + "\n复核: " + verify + "\n(一次性 URL 已用; 凭据卫生: 未写入 git config)";
                        }
                        else response.Content = "用法: /git status|diff|commit <msg>|push <一次性url>";
                    }
                    catch (Exception ex) { response.Content = $"git 操作失败: {ex.Message}"; }
                    response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                    return response;
                }
                // v0.17.2-a (R336): /activity 查询全部激活 agent/窗口/任务 (含其他 CLI, job_id/pid)
                if (localCommand.Command == "activity")
                {
                    response.Success = true;
                    response.Content = Activity().Render();
                    response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                    return response;
                }
                // v0.20.2 (R345): /llm-service — llm-manager/worker 状态观测 (独立进程; manager 不在 → 提示启动)
                if (localCommand.Command == "llm-service")
                {
                    var sock = agent.llamalocal.RemoteEmbedder.GetSockFromEnv();
                    var st = agent.llmservice.LlmServiceStatus.Query(sock);
                    response.Success = true;
                    response.Content = st.Render(sock);
                    response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                    return response;
                }
                // v0.17.2-b/c (R337): /schedule-run 条件定时执行 py 插件脚本 —
                // 用法: /schedule-run <延时秒> <py脚本路径> [目标描述]; 到期且无其他 agent 忙则执行
                // (v0.17.2-b 事件流协议; 坏 py 拒绝 + 教训落盘)。v1 延时上限 60s (长延时/跨重启调度交互语义待用户裁定)。
                if (localCommand.Command == "schedule-run")
                {
                    response.Success = true;
                    var arg = (localCommand.Argument ?? string.Empty).Trim();
                    var parts = arg.Split(' ', 3, StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
                    if (parts.Length < 2 || !int.TryParse(parts[0], System.Globalization.NumberStyles.None,
                        System.Globalization.CultureInfo.InvariantCulture, out var dueSecs) || dueSecs < 0)
                    {
                        response.Content = "用法: /schedule-run <延时秒> <py脚本路径> [目标描述]\n到期且无其他 agent 忙则执行 (脚本须符合 v0.17.2-b JSON Lines 事件流协议; py_compile 验证拒绝则记教训不执行)。";
                    }
                    else if (dueSecs > 60)
                    {
                        response.Content = "v1 延时上限 60s (更长延时/跨重启调度 = 下轮候选, 交互语义待用户裁定)。";
                    }
                    else
                    {
                        try
                        {
                            var scriptPath = parts[1];
                            var goal = parts.Length > 2 ? parts[2] : scriptPath;
                            var payload = new agent.skills.ScriptTaskPayload
                            {
                                Id = Guid.NewGuid().ToString("N"),
                                Goal = goal.Length > 200 ? goal[..200] : goal,
                                OutputDir = Path.Combine(Environment.CurrentDirectory, "data", "script-plugin", "outputs"),
                            };
                            var verdict = await ScriptScheduler().RunWhenIdleAfterAsync(
                                scriptPath, payload, TimeSpan.FromSeconds(dueSecs), ct).ConfigureAwait(false);
                            response.Content = verdict.Render();
                        }
                        catch (Exception ex)
                        {
                            response.Content = $"schedule-run 失败: {ex.Message}";
                        }
                    }
                    response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                    return response;
                }
                response.Content = localCommand.Reply;
                response.Success = true;
                response.Data = new Dictionary<string, object>
                {
                    { "localCommand", localCommand.Command },
                    { "argument", localCommand.Argument ?? string.Empty },
                };
                response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                return response;
            }

            // 1.0 跨轮续跑 (v0.22.0 exp9 D7b): 上一轮计划卡在"等用户回答"时, 这一轮消息的语义 = **答复它**,
            //     不是新任务 —— 必须在意图拆解**之前**拦下, 否则答复会被重拆成新任务, 用户永远等不到续跑。
            if (await TryResumePausedPlanAsync(message, response, ct))
            {
                response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                return response;
            }

            // 1. 意图识别 + 子任务拆解 (v7.9): 复合句拆为有序子任务, 主意图驱动模板选择
            // v0.11.0 R129 (PGO v2 D3): 意图阶段热路径计时
            var intentSw = System.Diagnostics.Stopwatch.StartNew();
            var subTasks = IntentDecomposer.Decompose(message.Content);
            var intent = IntentDecomposer.PrimaryIntent(subTasks);
            intentSw.Stop();
            agent.config.AgentTelemetry.Emit("intent", "IndustrialAgentV2",
                ("primary", intent), ("subtask_count", subTasks.Count),
                ("input_chars", message.Content.Length),
                ("sensitive", agent.intent.InjectedInstructionClassifier.IsSensitiveIntent(intent)),
                ("ms", intentSw.ElapsedMilliseconds));
            if (subTasks.Count > 1)
            {
                _logger.LogInformation(
                    "Intent decomposed into {Count} sub-tasks, primary={Intent}, intents=[{Intents}]",
                    subTasks.Count, intent, string.Join(",", subTasks.Select(t => t.Intent)));
            }
            
            // 1.38 v0.15.2-b (警告语义写入链): 用户主动警告 ("不要/禁止/别再/记住/警告你" + 指向性)
            // → 提取逻辑三元组入 GuardrailMemory (source=human_warning, 最高秩)。
            // 规则先行 (词表), LLM 辅助解析待标定 (plan 待确认项)。域锚 = GoalText (既有锚定)。
            try
            {
                var warningMarkers = new[] { "不要", "禁止", "别再", "不要再", "警告你", "记住了", "以后别", "禁止再" };
                var hitMarker = warningMarkers.FirstOrDefault(w => message.Content.Contains(w, StringComparison.Ordinal));
                if (hitMarker != null && message.Content.Length >= 8)
                {
                    _guardrailMemory ??= agent.critique.GuardrailMemory.Load(
                        Path.Combine(_dataStoragePath, "guardrails.json"));
                    var goal = _sessionMemoryStore.Load(message.SessionId)?.Goal;
                    var domain = goal?.GoalText ?? "general";
                    // 规则解析 (最小可行): 禁令 = 警告词后片段 (≤40ch); pattern = 内容名词化 (意图关键词);
                    var afterIdx = message.Content.IndexOf(hitMarker, StringComparison.Ordinal) + hitMarker.Length;
                    var prohibition = message.Content[afterIdx..].TrimStart(' ', ',', '，')[..Math.Min(40, message.Content[afterIdx..].TrimStart(' ', ',', '，').Length)];
                    var patternWords = agent.intent.TaskRelevanceChecker.ExtractEntities(message.Content);
                    var pattern = string.Join(" ", patternWords.Take(3));
                    if (prohibition.Length >= 2 && pattern.Length >= 2)
                    {
                        var entry = _guardrailMemory.Write(domain, pattern, "", prohibition, "", message.Content[..Math.Min(60, message.Content.Length)], "human_warning");
                        agent.config.AgentTelemetry.Emit("guardrail_write", "IndustrialAgentV2",
                            ("id", (object)entry.Id), ("marker", (object)hitMarker));
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "警告语义写入失败 (不影响本轮)");
            }

            // 1.39 v0.15.1-a (任务进行中新输入路由): TaskCharter 活跃时按章程锚三态路由 —
            // 相关补充 → pending_inputs (下轮循环注入依据); 无关任务 → 隔离子 (既有链);
            // 换任务语义 → pivot (既有重锚)。判定器全复用 TopicRelevanceEvaluator (R308)。
            // 无活动章程 → 既有行为 (本块零干预)。
            try
            {
                var charter = agent.tasks.TaskCharter.LoadActive(_dataStoragePath);
                if (charter is { IsRunning: true })
                {
                    // pivot 语义判定 (与 1.4 块同词表 — 用户转向/放弃类输入优先路由 Pivot)
                    var pivotInput = PivotMarkers.Any(m => message.Content.Contains(m, StringComparison.Ordinal));
                    var routeVerdict = agent.intent.TopicRelevanceEvaluator.Evaluate(
                        message.Content,
                        charter.KeyEntities.AsReadOnly(),
                        charter.GoalText,
                        intent,
                        coreTopic: "");  // v0.15.1-a: 章程锚已含主题语义, 词面偏离不参与路由 (Isolate/Supplement 二态即可)
                    var route = routeVerdict.Action switch
                    {
                        _ when pivotInput => agent.tasks.TaskCharter.InputRoute.Pivot,
                        agent.intent.TopicRelevanceEvaluator.Recommendation.Isolate => agent.tasks.TaskCharter.InputRoute.Isolate,
                        _ => agent.tasks.TaskCharter.InputRoute.Supplement,
                    };
                    agent.config.AgentTelemetry.Emit("task_input", "IndustrialAgentV2",
                        ("route", route.ToString()), ("charter", charter.Id),
                        ("score", routeVerdict.Score));
                    switch (route)
                    {
                        case agent.tasks.TaskCharter.InputRoute.Supplement:
                            // 主题补充: 暂存下轮注入 (持久化 — 跨进程/跨轮)
                            charter.PendingInputs.Add(message.Content);
                            charter.Save(_dataStoragePath);
                            break;
                        case agent.tasks.TaskCharter.InputRoute.Pivot:
                            // 换任务: 章程归档 failed (用户转向) — pivot 既有机制接管重锚
                            charter.Archive(_dataStoragePath, "failed");
                            break;
                        case agent.tasks.TaskCharter.InputRoute.Isolate:
                            // 无关任务: 走既有隔离子 (下方 1.4 隔离判定承接, 此处仅打点路由去向)
                            break;
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "任务路由判定失败 (降级: 既有行为)");
            }

            // 1.4 隔离任务判定 (v7.15 I.2): 单任务 + 判定与主目标无关 → 隔离子执行, 不进主链
            // (首轮无 GoalProfile 锚 → 不隔离; 多子任务=当前目标链的一部分 → 不隔离)
            // R308b (合并判定收口): TopicRelevanceEvaluator 一次计算 — 隔离/牵引/打点三路消费同一 verdict。
            string coreTopic = "";
            agent.intent.TopicRelevanceEvaluator.TopicRelevanceVerdict? topicVerdict = null;
            try
            {
                // v0.15.3 T-A3 (P2): GetAwaiter().GetResult() → await (每消息热路径阻塞消除; T-A1 后内层已无阻塞)
                var biasScores = (await _tendencyAnalyzer.GetContextBiasAsync(
                    message.SenderId ?? "cli-user", message.Content)).BiasScores;
                coreTopic = biasScores.OrderByDescending(kv => kv.Value).FirstOrDefault().Key ?? "";
            }
            catch (Exception ex)
            {
                agent.config.AgentTelemetry.Emit("topic_relevance", "IndustrialAgentV2",
                    ("error", ex.Message[..Math.Min(50, ex.Message.Length)]));
            }
            if (_isolatedTaskRunner != null && subTasks.Count == 1)
            {
                var goalMemory = _sessionMemoryStore.Load(message.SessionId);
                var goal = goalMemory?.Goal;
                var goalEntities = goal?.KeyEntities ?? new List<string>();
                // v0.11.0 R72 (真缺陷 31): 显式放弃旧目标 ("不要之前…/算了改…/放弃…") 的轮次
                // 必须跳过隔离 — 否则零重叠判定先行拦截, 455 行的 pivot 重锚永远执行不到 (死区)。
                var pivotRequested = PivotMarkers.Any(m => message.Content.Contains(m, StringComparison.Ordinal));
                agent.config.AgentTelemetry.Emit("topic_relevance", "IndustrialAgentV2",
                    ("stage", "isolation-point"), ("core", coreTopic),
                    ("goal_entities", goalEntities.Count), ("subtasks", subTasks.Count));
                // 首轮 (无目标锚) 不隔离 — 无"当前任务"可言
                if (!pivotRequested && goal != null && goalEntities.Count > 0)
                {
                    // R308b (合并判定收口): 隔离消费走统一 evaluator (与牵引/打点同源)。
                    topicVerdict = agent.intent.TopicRelevanceEvaluator.Evaluate(
                        message.Content, goalEntities, goal.GoalIntent, subTasks[0].Intent, coreTopic);
                    // R313 (重构事故修复): R312 插入 else 分支时把有锚隔离执行链误删 —
                    // C14 类用例 verdict=Isolate 但 subagent 打点/ExecuteAsync 全灭 (批477 首败实锤)。
                    // 恢复: 有锚 isIsolated → subagent 打点 + 隔离执行 (与 R307 前行为一致)。
                    if (topicVerdict.IsIsolated)
                    {
                        var (scoreI, reasonI) = (topicVerdict.Score,
                            string.Join(";", topicVerdict.Signals));
                        agent.config.AgentTelemetry.Emit("subagent", "IsolatedTaskRunner",
                            ("isolated", true), ("relevance_score", scoreI), ("reason", reasonI));
                        _logger.LogInformation(
                            "IsolatedTask triggered: score={Score} reason={Reason} task={Task}",
                            scoreI, reasonI, message.Content);
                        var isolated = await _isolatedTaskRunner.ExecuteAsync(message.Content, $"{scoreI}:{reasonI}", ct);
                        response.Success = isolated.Success;
                        response.Content = $"[隔离任务] {isolated.Answer ?? isolated.Error ?? "(无返回)"}";
                        response.Data = new Dictionary<string, object>
                        {
                            { "isolatedTask", true },
                            { "isolatedSessionId", isolated.IsolatedSessionId },
                            { "relevanceScore", scoreI },
                        };
                        response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                        return response;
                    }
                }
                else if (goal == null && !pivotRequested && !string.IsNullOrEmpty(coreTopic))
                {
                    // R312: 无 goal 锚轮 — 纯词面 verdict (goalEntities 空 → 隔离恒 false,
                    // 词面偏离 → IsDrift)。恢复 R307 L1 行为, 保持单源 evaluator。
                    topicVerdict = agent.intent.TopicRelevanceEvaluator.Evaluate(
                        message.Content,
                        (IReadOnlyList<string>)Array.Empty<string>(), "", subTasks.Count > 0 ? subTasks[0].Intent : "general", coreTopic);
                    var (isIsolated, score, reason) = (topicVerdict.IsIsolated,
                        topicVerdict.Score, string.Join(";", topicVerdict.Signals));
                    if (isIsolated)
                    {
                        agent.config.AgentTelemetry.Emit("subagent", "IsolatedTaskRunner",
                            ("isolated", true), ("relevance_score", score), ("reason", reason));
                        _logger.LogInformation(
                            "IsolatedTask triggered: score={Score} reason={Reason} task={Task}",
                            score, reason, message.Content);
                        var isolated = await _isolatedTaskRunner.ExecuteAsync(message.Content, $"{score}:{reason}", ct);
                        response.Success = isolated.Success;
                        response.Content = $"[隔离任务] {isolated.Answer ?? isolated.Error ?? "(无返回)"}";
                        response.Data = new Dictionary<string, object>
                        {
                            { "isolatedTask", true },
                            { "isolatedSessionId", isolated.IsolatedSessionId },
                            { "relevanceScore", score },
                        };
                        response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                        return response;
                    }
                }
            }

            // 1.5 EvidenceGate 裁定 → ClarificationBatch 真实批量问询 (v7.14 ①):
            // 低置信子任务生成疑问 → REPL 弹批量问题 → 答案并入本轮任务描述 (不带疑问硬执行)
            var clarifiedAddendum = await RunEvidenceGateAsync(message, subTasks, ct);
            if (!string.IsNullOrEmpty(clarifiedAddendum))
            {
                message.Content = $"{message.Content}\n[用户补充说明]\n{clarifiedAddendum}";
                _logger.LogInformation("EvidenceGate 补充了 {Count} 字用户说明", clarifiedAddendum.Length);
            }

            // 1.6 计划构建 + 确定性路由 (v0.22.0 exp9 D1+D2): 子任务 → 节点位置 (本地/远程) → 追加本地验证节点。
            //     D5: 意图进入即把"子任务细分+每步位置"公告前端 (不等模型生成完);
            //     D4: 无依赖本地节点 (输入=用户原文, 已在手) 此刻就**并行先跑**, 不等远程产物。
            _lastPlan = BuildRoutedPlan(message.Content, subTasks);
            _planRunner ??= new agent.intent.PlanRunner();
            await _planRunner.AnnounceAsync(_lastPlan, ct);
            _planCtx = agent.intent.PlanRunner.NewContext(
                sessionId: message.SessionId, sourceText: message.Content);
            _planRemoteStartUs = agent.intent.Monotonic.NowUs();
            _localFirst = _planRunner.StartLocalFirst(_lastPlan, _planCtx, ct);

            // 1.7 出站文本扣减 (v0.22.0 exp9 D4b): 已判"框架自己做"的子请求**不许再发给模型**。
            //     路由是"谁来做", 不是"记账": 不扣减 ⇒ 模型把同一步再算一遍 (真机 R382: 模型算 118 / 框架确定性算 117),
            //     零 token 收益被吃掉, 而且用户看到的是模型那个错的数。
            //     保守方向: 定位不到/多处出现/比例过大一律**不扣** (RequestAblation 内部硬约束), 绝不改坏用户原话;
            //     全部节点都是本地 ⇒ 那是"本地独占回合"(§10 边界, 本轮不实现), 也不扣, 交原链路。
            _planAblation = agent.intent.RequestAblation.SubtractForPlan(message.Content, _lastPlan.Nodes);
            agent.config.AgentTelemetry.Emit("plan_ablate", "IndustrialAgentV2",
                ("applied", _planAblation.Applied),
                ("removed_chars", _planAblation.RemovedChars),
                ("clauses", string.Join(" | ", _planAblation.RemovedClauses)),
                ("reason", _planAblation.AbortReason),
                ("src_chars", message.Content.Length),
                ("out_chars", _planAblation.Text.Length));
            if (_planAblation.Applied)
                _logger.LogInformation("出站扣减 (D4b): {Count} 段本地子请求 / {Chars} 字符不再发给模型",
                    _planAblation.RemovedClauses.Count, _planAblation.RemovedChars);

            // 2. 多数据源上下文组装（失败时降级为空上下文，不阻断对话）
            var contextResult = await AssembleContextAsync(message, intent, subTasks, ct);
            // v0.11.0: source 级召回统计 (对比数据 — 召回率/压缩率/延迟)
            var sourceStats = string.Join(",", contextResult.SourceStats.Select(kv =>
                kv.Key + ":" + kv.Value.SnippetCount + "snip/" + kv.Value.TotalTokens + "tok/r" + Math.Round(kv.Value.AvgRelevanceScore, 2) + "rel"));
            agent.config.AgentTelemetry.Emit("assembly", "ContextAssembler",
                ("success", contextResult.Success), ("error", contextResult.Error),
                ("sources", sourceStats), ("snippets", contextResult.Snippets.Count),
                ("total_tokens", contextResult.TotalTokens),
                ("budget_usage", Math.Round(contextResult.TokenBudgetUsage, 3)),
                ("assembly_ms", contextResult.AssemblyTimeMs), ("from_cache", contextResult.FromCache));
            if (!contextResult.Success)
            {
                _logger.LogWarning(
                    "Context assembly failed, continuing without context: {Error}",
                    contextResult.Error);
            }
            
            // 3. 获取对话历史 (R379: 全量正序回放 — 追加式前缀; 旧实现倒序 Take(10) 头部滚动丢弃)
            var history = await GetConversationHistoryAsync(message.SessionId, ct);
            
            // 4. ✅ 关键：构建真正发给 LLM 的 Prompt
            var systemPrompt = IntentPromptTemplates.GetSystemPrompt(intent);

            // ── R379 Fix B (真机实证) ──
            // systemPrompt 由 intent 逐轮选择 → 会话内意图漂移 (实况: 轮1 search → 轮2 general)
            // 会让 messages[0] 从字节 4 起变化 → DS 缓存前缀 (64 token 单元, 自 token 0 完整匹配) 整段失配,
            // 实测轮2 命中率 0%。铁律: messages[0] 必须"会话内恒定字节"。
            // 意图漂移不再改写 system, 而是以 [本轮意图适配] 尾部块注入 user (纯追加区, 不破坏已有前缀)。
            // R379 增量最小化 (实测: 每轮增量 ~850 token, 会话前缀仅 ~970 token → 命中率天花板 ~53%):
            //   ① 会话静态块 (画像/偏好/工作区) 只在**会话首轮**焊进前缀, 之后不再重复注入;
            //   ② 动态块跨轮行级去重 (已发过的行不再重复发 —— 历史里已有);
            //   ③ 意图漂移只追加一行短提示 (整段专用指引白烧 ~500 字符/轮)。
            var headerBlocks = SessionInjectionPlanner.Split(contextResult.PromptHeader);
            var staticBlocks = new List<SessionInjectionPlanner.Block>();
            var dynamicBlocks = new List<SessionInjectionPlanner.Block>();
            foreach (var b in headerBlocks)
            {
                if (SessionInjectionPlanner.IsSessionStatic(b.Title)) staticBlocks.Add(b);
                else dynamicBlocks.Add(b);
            }
            var staticText = SessionInjectionPlanner.Join(staticBlocks);

            string intentAdaptHint = string.Empty;
            var systemPromptFrozen = false;
            var staticHoistedChars = 0;
            var baselineChars = 0;
            var sysKey = string.IsNullOrEmpty(message.SessionId) ? null : message.SessionId;
            if (sysKey != null)
            {
                if (_frozenSystemPrompt.Count > 512) _frozenSystemPrompt.Clear(); // 有界: 防长驻进程无界增长
                if (!_frozenSystemPrompt.TryGet(sysKey, out var frozen))
                {
                    // 会话首轮: (会话基线 + 静态块) 焊进前缀 —— 此后每轮都命中这段缓存, 且不再重复注入。
                    // R380/R393 (用户 OOB 红线 95%→97%, 越线必查+修复): 命中上限 ≈ (n−1)/n (n = 前缀 64-token 单元数)
                    //  ⇒ 前缀必须够厚, 否则结构修到极限也越线 (真机实测 981 token 前缀的上限恰为 896 = 91.3%)。
                    var baseline = SessionBaseline.Build(
                        _workspace is { RootPath: { Length: > 0 } wr } ? wr : Environment.CurrentDirectory,
                        // R391(C8): 本地形式化验证段插件**在场** ⇒ 注入 clickproof 输出契约 (不在场 ⇒ 前缀逐字不变)
                        System.Linq.Enumerable.Contains(_segmentRouter.PluginNames, agent.registry.ClickRoverSegmentPlugin.PluginId));
                    var initial = systemPrompt + "\n\n" + baseline
                                  + (staticText.Length > 0 ? "\n[会话静态上下文]\n" + staticText : string.Empty);
                    staticHoistedChars = initial.Length - systemPrompt.Length;
                    baselineChars = baseline.Length;
                    frozen = (initial, intent);
                    _frozenSystemPrompt.Set(sysKey, frozen);
                }
                else if (!string.Equals(frozen.Intent, intent, StringComparison.Ordinal))
                {
                    // 意图漂移: 只追加一行短提示 (专用指引已在冻结人格里) → 不再动 messages[0] 的字节
                    intentAdaptHint = $"[本轮意图] {intent} (会话人格保持不变)";
                    systemPromptFrozen = true;
                    // KPI 归因: 该轮拦截了一次意图漂移 (否则该轮缓存命中率归零)
                    agent.config.AgentTelemetry.Emit("cache_prefix_guard", "IndustrialAgentV2",
                        ("frozen", true), ("intent", intent), ("session", message.SessionId));
                }
                systemPrompt = frozen.Prompt;
            }
            else if (staticText.Length > 0)
            {
                // 无会话 (一次性请求): 无处冻结 → 静态块随本轮尾部下发
                dynamicBlocks.Insert(0, new SessionInjectionPlanner.Block("[会话静态上下文]", staticText));
            }

            // 下轮预估读回 (v7.11): 上轮循环落盘的预估 → 指示 LLM 用户本轮输入倾向
            var identity = _agentRegistry.Get(message.SenderId is { Length: > 0 } ? message.SenderId : "main")
                            ?? _agentRegistry.Main;
            var forecast = agent.registry.NextTurnForecast.Load(_dataStoragePath, identity.Uid);
            var forecastHeader = agent.registry.NextTurnForecast.ToPromptHeader(forecast);
            // ── R379 缓存前缀稳定化 (用户钦定 KPI 红线: 多轮会话第 2 轮起命中率 ≥90%, 目标 98~99%) ──
            // systemPrompt 是 messages[0] → 只要它每轮变一个字节, provider 的缓存前缀就从字节 0 失配。
            // 因此 systemPrompt 保持"会话内恒定", 一切每轮变化的块 (下轮预估 / 技能知识 / 上下文召回)
            // 一律内联进"本轮 user 内容", 并落进 SentContent 作为回放字节 (追加区语义)。
            var inlineBlocks = new List<string>();
            if (intentAdaptHint.Length > 0)
                inlineBlocks.Add(intentAdaptHint);
            if (forecastHeader.Length > 0)
                inlineBlocks.Add(forecastHeader);
            // R326-f: KnowledgeHint skill 知识注入 (命中后尾挂知识参考; 本轮一次)
            if (_pendingSkillKnowledge.Length > 0)
            {
                inlineBlocks.Add("[技能知识参考]\n" + _pendingSkillKnowledge);
                _pendingSkillKnowledge = string.Empty;
            }
            // 动态块: 跨轮行级去重后下发 (去重集合按会话持有; 一次性请求用临时集合)
            var dynKept = 0;
            var dynDropped = 0;
            var dynText = string.Empty;
            if (dynamicBlocks.Count > 0)
            {
                if (sysKey != null)
                {
                    var seen = _sessionSentLines.GetOrAdd(sysKey, _ => new SessionInjectionPlanner.InjectionLedger());
                    lock (seen) { (dynText, dynKept, dynDropped) = SessionInjectionPlanner.Dedupe(dynamicBlocks, seen); }
                }
                else
                {
                    (dynText, dynKept, dynDropped) = SessionInjectionPlanner.Dedupe(dynamicBlocks, new SessionInjectionPlanner.InjectionLedger());
                }
            }
            if (dynText.Length > 0)
                inlineBlocks.Add(dynText);

            // D4b: 出站正文 = 原文扣掉"框架自己做"的子请求 (未扣减时逐字等于原文 ⇒ 零改动)
            var outboundText = _planAblation is { Applied: true } ? _planAblation.Text : message.Content;
            var sentUserContent = outboundText;
            if (inlineBlocks.Count > 0)
                sentUserContent = outboundText + "\n\n[本轮参考上下文]\n" + string.Join("\n\n", inlineBlocks);
            message.SentContent = sentUserContent;

            var prompt = _promptBuilder.BuildWithHistory(
                message,
                contextResult,
                systemPrompt,
                history);
            // 上下文/预估/技能知识已内联在 user 消息里 → 不再作为独立 system 消息发出 (否则切断前缀)
            prompt.UserMessage = sentUserContent;
            prompt.ContextPrompt = string.Empty;
            // R379 KPI 归属 (红线判据: 多轮会话第 2 轮起命中率 ≥90%) — 无会话/轮次则 KPI 无法追到"第几轮"
            prompt.SessionId = message.SessionId;
            prompt.TurnIndex = history.Count / 2 + 1;
            prompt.EstimatedTokens += EstimateTokens(forecastHeader) + EstimateTokens(sentUserContent)
                                      - EstimateTokens(message.Content) - EstimateTokens(contextResult.PromptHeader);
            
            _logger.LogInformation(
                "Built prompt: {Tokens} tokens (Context: {ContextTokens})",
                prompt.EstimatedTokens,
                EstimateTokens(prompt.ContextPrompt));

            // v0.11.0: prompt 构成打点 (历史/上下文/系统占比 — token 治理对比数据)
            agent.config.AgentTelemetry.Emit("prompt_build", "IndustrialAgentV2",
                ("total_tokens", prompt.EstimatedTokens),
                ("history_msgs", prompt.History.Count),
                ("history_tokens", prompt.History.Sum(h => EstimateTokens(h.Content))),
                ("history_trimmed", prompt.HistoryTrimmedMessages),
                ("inline_context_tokens", EstimateTokens(contextResult.PromptHeader)),
                ("sent_user_tokens", EstimateTokens(prompt.UserMessage)),
                ("inline_dedupe_kept", dynKept),
                ("inline_dedupe_dropped", dynDropped),
                ("static_hoisted_chars", staticHoistedChars),
                ("baseline_chars", baselineChars),
                ("prefix_frozen", sysKey != null),
                ("intent_drift_guarded", systemPromptFrozen));
            
            // v0.13.3 M2 (用户钦定 Baseline 换血): 上下文预算门 — est 与 WARN/HARD 比较,
            // normal/isolated_micro/hard_drop 三态打点 (微隔离触发的前置观测点; 判定器在 agent.exploration)。
            var gateVerdict = _contextGate.Evaluate(prompt.EstimatedTokens);
            agent.config.AgentTelemetry.Emit("context_gate", "IndustrialAgentV2",
                ("est_tokens", gateVerdict.EstimatedTokens),
                ("warn", gateVerdict.WarnThreshold),
                ("hard", gateVerdict.HardThreshold),
                ("mode", gateVerdict.Mode.ToString()));

            // 4.5 思考流 (v7.15 L.2.2): 推理前发 page_switch + 构建摘要分片; LLM 返回后发 thinking_end
            if (_logRouter != null)
            {
                _logRouter.Write("IndustrialAgentV2", "info", agent.logging.LogChannel.Thinking,
                    $"prompt 构建完成: ~{prompt.EstimatedTokens} tokens, 意图={intent}",
                    contentFingerprint: FnvHash(prompt.UserMessage), contentLength: prompt.UserMessage.Length);
            }

            // v0.13.3 B2 (R274): 微步骤隔离执行 — gate 判 IsolatedMicro 时, 子任务转微问题经独立
            // 微 prompt 逐条问询 (不带主上下文), 结果按回注预算拼进主 prompt (A5 语义: 主记忆零污染)。
            var microRestore = string.Empty;
            agent.config.AgentTelemetry.Emit("micro_decision", "IndustrialAgentV2",
                ("mode", gateVerdict.Mode.ToString()), ("subtasks", subTasks.Count));

            // R308b (合并判定): topic_relevance 单点 — 隔离/牵引/打点三路消费同一 verdict
            // (TopicRelevanceEvaluator, 见 L520 隔离判定处的一次计算)。
            // R308b: 复用隔离点已算的 topicVerdict (一次计算 — 无重复评估); 无锚轮 (verdict null)
            // 退化为纯画像词面 drift (原 L2 行为)。
            var isDrift = topicVerdict is { IsDrift: true } &&
                          topicVerdict.Action == agent.intent.TopicRelevanceEvaluator.Recommendation.SteerHint;
            if (topicVerdict is not null)
            {
                agent.config.AgentTelemetry.Emit("topic_relevance", "IndustrialAgentV2",
                    ("score", topicVerdict.Score), ("verdict", topicVerdict.Action.ToString()),
                    ("core", coreTopic),
                    ("signals", string.Join(";", topicVerdict.Signals)[..Math.Min(120, string.Join(";", topicVerdict.Signals).Length)]));
            }
            else
            {
                // R308b: 无 goal 锚轮 (verdict null — 非隔离路径) 也打点, 消除观测盲区。
                agent.config.AgentTelemetry.Emit("topic_relevance", "IndustrialAgentV2",
                    ("stage", "no-anchor"), ("core", coreTopic), ("drift", isDrift));
            }

            // v0.13.3 R286 (思考链任务1 宿主收口): 上下文含 URL/目录线索且非 HardDrop 时, 思考链探索
            // (预算: deadline 4s + 步数≤4 — user 钦定 per-source 最大渐进探索步骤 config 语义)。
            // 探索 digest 进 exploreDigest, 与 microRestore 同通道回注。
            var exploreDigest = await RunThinkChainAsync(message.Content, prompt.ContextPrompt, ct);
            if (gateVerdict.Mode == agent.exploration.ContextGateMode.IsolatedMicro && subTasks.Count > 0)
            {
                microRestore = await RunMicroStepsAsync(subTasks, intent, ct);
            }

            // v0.13.3 R275: think-memory 联想检索真机链 — bge 向量 (ITextEmbedder DI) → Recall 历史相似问题
            // (MinSimilarity 0.75, 负样本降权) → 命中摘要回注 (复用 microRestore 通道, A5 语义);
            // 本轮问题向量 Write 入记忆 (联想库, 进程内 — 持久化排后续轮)。
            agent.config.AgentTelemetry.Emit("think_memory_recall_gate", "IndustrialAgentV2",
                ("count", _thinkMemory?.Count ?? -1), ("embedder", _textEmbedder is { IsAvailable: true }), ("instance", _instanceId));
            if (_textEmbedder is { IsAvailable: true } && _thinkMemory is { Count: > 0 })
            {
                try
                {
                    var qVec = await _textEmbedder.EmbedAsync(message.Content, ct);
                    var hits = _thinkMemory.Recall(qVec, 2);
                    if (hits.Count > 0)
                    {
                        var sbHit = new System.Text.StringBuilder();
                        foreach (var h in hits)
                        {
                            sbHit.AppendLine($"[联想 {h.Similarity:F2}] {h.Record.QuestionHead}");
                        }
                        microRestore = string.IsNullOrEmpty(microRestore)
                            ? sbHit.ToString()
                            : microRestore + "\n" + sbHit;
                        agent.config.AgentTelemetry.Emit("think_memory", "IndustrialAgentV2",
                            ("hits", hits.Count), ("top_sim", hits[0].Similarity));
                    }
                }
                catch (OperationCanceledException) { throw; }
                catch (Exception ex)
                {
                    agent.config.AgentTelemetry.Emit("think_memory", "IndustrialAgentV2",
                        ("error", ex.Message[..Math.Min(60, ex.Message.Length)]));
                }
            }
            // v0.13.3 R282: LinkRegistry 宿主挂载 — 上下文中的 URL 登记 + 三信号预判 + 激活打点
            // (设计稿 §7.2: 递进未进入时不靠召回笼统索引, 凭锚定/结构/递进判定关键文档)。
            try
            {
                var urlMatches = System.Text.RegularExpressions.Regex.Matches(
                    message.Content + " " + prompt.ContextPrompt, @"https?://[^\s,，。;；)" + "\"" + "'" + "]+");
                var urls = urlMatches.Select(m2 => m2.Value.TrimEnd('.', ',', ')', '}', ']'))
                    .Where(u => u.Length > 8).Distinct().Take(20).ToList();
                if (urls.Count > 0)
                {
                    string? parent = null;
                    var activatedAny = new List<string>();
                    foreach (var u in urls)
                    {
                        var entry = _linkRegistry.Register(u, parent);
                        var score = _linkRegistry.PreJudge(u, message.Content, urls, inThinkMemory: false);
                        var guarded = _linkRegistry.ActivateIfWorthy(entry, score, message.Content, urls, inThinkMemory: false);
                        if (guarded.Count > 0) activatedAny.AddRange(guarded);
                        parent = u; // 链式: 文档内先后 URL 视为父子候选
                    }
                    agent.config.AgentTelemetry.Emit("link_activation", "IndustrialAgentV2",
                        ("urls", urls.Count),
                        ("activated", activatedAny.Distinct().Count()),
                        ("registry", _linkRegistry.Count));
                }
            }
            catch (Exception ex)
            {
                agent.config.AgentTelemetry.Emit("link_activation", "IndustrialAgentV2",
                    ("error", ex.Message[..Math.Min(60, ex.Message.Length)]));
            }

            if (_textEmbedder is { IsAvailable: true } && _thinkMemory is not null)
            {
                try
                {
                    var wVec = await _textEmbedder.EmbedAsync(message.Content, ct);
                    _thinkMemory.Write(new agent.exploration.ThinkRecord
                    {
                        QuestionEmbedding = wVec,
                        QuestionHead = message.Content.Length > 60 ? message.Content[..60] : message.Content,
                        AvgConfidence = subTasks.Count > 0 ? subTasks.Average(t => t.Confidence) : 1.0,
                    });
                    agent.config.AgentTelemetry.Emit("think_memory", "IndustrialAgentV2",
                        ("written", true), ("count", _thinkMemory.Count), ("instance", _instanceId));
                    _thinkMemory.Save(_thinkMemoryPath);
                }
                catch (OperationCanceledException) { throw; }
                catch { /* 联想写入失败不影响主链 (防御性 — 打点在 Recall 侧已覆盖) */ }
            }

            // 5. ✅ 调用 LLM（传入完整 Prompt）
            // v0.11.0 R21: 推理档位路由 — 简单任务轻思考省 token/延迟, 复杂任务保留默认深推理。
            // 实测 (glm-5.3-flash): 简单题 reasoning 0 vs 8910ch; 复杂题 low 档 wall -55%。
            prompt.ReasoningEffort = IsSimpleIntentForReasoning(intent, prompt.UserMessage) ? "low" : null;
            prompt.Intent = intent;   // R373: 意图透传到模型队列 (首轮预算策略的确定性输入, 不靠文本猜测)
            var restoreBlock = string.Join("\n\n", new[] { microRestore, exploreDigest }.Where(s => !string.IsNullOrEmpty(s)));
            if (restoreBlock.Length > 0)
            {
                // 回注摘要拼在用户消息尾 (微步骤 ≤200 tok/条 + 探索 digest 截断 — 预算封顶)
                prompt.UserMessage = prompt.UserMessage + "\n\n[探索与微步骤结论回注]\n" + restoreBlock;
                // ── R379 Fix A (真机实证) ──
                // 该追加发生在 SentContent 快照之后 → 存进会话的是"旧字节", 回放时少这一个块 (实测 turn2 的
                // user 消息被回放成 1150 字符, 而当时实发 1222 字符 → 前缀在历史中部断裂)。
                // 铁律: SentContent = 最终发送字节。任何对 prompt.UserMessage 的事后追加都必须回写。
                message.SentContent = prompt.UserMessage;
            }
            // ── R413 前置门 (默认关; role 缺失自动失效 ⇒ 零回归) ──
            // 语义: 本轮消息无新增诉求 (纯认可/确认/寒暄/重复) ⇒ 本地消化, 不发远端主调用
            // ⇒ 省掉整轮 prompt (实测基线 2.4k–3.0k tok/轮)。判别失败/无法解析 ⇒ 一律降级远端。
            LLMResponse llmResponse;
            var gateOutcome = agent.modelqueue.TurnGateOutcome.Undecided("gate_disabled");
            if (System.Threading.Interlocked.Exchange(ref _gateConfigEmitted, 1) == 0)
            {
                agent.config.AgentTelemetry.Emit("local_turn_gate_config", "IndustrialAgentV2",
                    ("router_present", (_modelRouter is not null).ToString()),
                    ("turn_gate_enabled", (_modelRouter?.TurnGateEnabled ?? false).ToString()),
                    ("local_channel_ready", (_modelRouter?.LocalChannelReady ?? false).ToString()),
                    ("role", ActiveRole?.Id ?? "(null)"));
            }
            if (_modelRouter is { TurnGateEnabled: true } && ActiveRole is not null)
            {
                // R413 实测铁律: 判别提示必须**规格化** — role 全文/成长全文灌进去会挤爆生成预算,
                // 真机表现为输出截断在思考链中途 (无闭合标记) ⇒ 判别恒降级、增益归零。
                // 只挂「角色标识 + 种子的有界片段」(可对账、可负控), 不灌全文。
                // ★ 必须判「用户本轮原文」而不是 prompt.UserMessage —— 后者已被 role 块/计划续跑/微提示
                // 追加过 (R379 Fix A), 里面必然含数字与长文本 ⇒ 机械门恒 Pass、增益归零 (真机诊断实证)。
                if (agent.modelqueue.TurnGateJudge.MechanicalPass(message.Content))
                {
                    // R413 机械前置门 (零 token): 命中「疑问/新诉求/纠正/结构化实体/长文本」⇒ 直接 Pass,
                    // 根本不问 r1 —— 假阴性 (新诉求被误跳) 是结构性风险, 不能靠小模型判对来兜。
                    _modelRouter.TurnGate.RecordMechanicalPass();
                    gateOutcome = agent.modelqueue.TurnGateOutcome.Decide(
                        agent.modelqueue.TurnGateVerdict.Pass, "mechanical:pass");
                }
                else gateOutcome = await _modelRouter.JudgeTurnAsync(
                    message.Content,
                    ActiveRole.Id + "|" + agent.modelqueue.TurnGateJudge.Clip(ActiveRole.ProfileSeed, 80),
                    null,
                    ct).ConfigureAwait(false);
                agent.config.AgentTelemetry.Emit("local_turn_gate", "IndustrialAgentV2",
                    ("decided", gateOutcome.Decided ? "true" : "false"),
                    ("verdict", gateOutcome.Verdict.ToString()),
                    ("basis", _modelRouter.TurnGate.LastBasis ?? ""),
                    ("raw", gateOutcome.Raw.Length > 120 ? gateOutcome.Raw[..120] : gateOutcome.Raw),
                    ("raw_len", gateOutcome.Raw.Length.ToString()),
                    ("error", gateOutcome.Error ?? ""),
                    ("role", ActiveRole.Id));
            }

            if (gateOutcome.Decided && gateOutcome.Verdict == agent.modelqueue.TurnGateVerdict.Skip)
            {
                // 本地消化: 零远端 token (回复由本地 r1 生成, 失败 → 固定兜底串)
                var localReply = await _modelRouter!.ComposeLocalSkipReplyAsync(prompt.UserMessage, ct).ConfigureAwait(false);
                llmResponse = new LLMResponse
                {
                    Content = localReply,
                    Success = true,
                    Model = "local:turn-gate",
                    PromptTokens = 0,
                    CompletionTokens = 0,
                    TokensUsed = 0,
                    FinishReason = "local_turn_gate_skip",
                };
                agent.config.AgentTelemetry.Emit("phase_timing", "IndustrialAgentV2",
                    ("phase", "llm_local_gate"), ("ms", 0L), ("intent", intent));
            }
            else
            {
                // v0.11.0 R129 (PGO v2 D3): LLM 全段耗时 (含队列路由/余额检查; 与 llm_call.ms 差值 = 路由开销)
                var llmSegSw = System.Diagnostics.Stopwatch.StartNew();
                llmResponse = await _llmCaller.CallAsync(prompt, ct);
                llmSegSw.Stop();
                agent.config.AgentTelemetry.Emit("phase_timing", "IndustrialAgentV2",
                    ("phase", "llm"), ("ms", llmSegSw.ElapsedMilliseconds), ("intent", intent));
            }

            // 5.1 思考结束指令 (L.2.2 指令 2 — 前端关闭思考步骤显示并折叠)
            _logRouter?.EmitThinkingEnd(llmResponse.Content.Length);

            // R307 (L1 轻牵引): 连续 ≥2 轮偏题 → 回复尾追加一句衔接提示 (不改答案本体,
            // 提示与核心主题的衔接点 — 消费 K1 画像偏置, 实现会话内牵引不偏离核心主题)。
            _consecutiveDrift = isDrift ? _consecutiveDrift + 1 : 0;
            // R315 (拉回率): clarify 已发 + 本轮回锚 (drift=false) → pulled_back 打点并撤防;
            // 超过 2 轮未回锚 → 过期撤防 (不 emit false — 只度量成功回锚, 避免噪声)。
            if (_clarifyArmed)
            {
                if (!isDrift && _clarifyTurnsLeft > 0)
                {
                    agent.config.AgentTelemetry.Emit("topic_clarify", "IndustrialAgentV2",
                        ("pulled_back", true), ("turns_left", _clarifyTurnsLeft));
                    _clarifyArmed = false;
                }
                else
                {
                    _clarifyTurnsLeft--;
                    if (_clarifyTurnsLeft <= 0) _clarifyArmed = false;
                }
            }
            // R309b: 牵引触发阈值 config 化 (env AGENTFRAMEWORK_TOPIC_STEER_THRESHOLD, 默认 2)
            var _steerThreshold = int.TryParse(Environment.GetEnvironmentVariable("AGENTFRAMEWORK_TOPIC_STEER_THRESHOLD"), out var _st) && _st >= 1 ? _st : 2;
            var steeringPending = _consecutiveDrift >= _steerThreshold && !string.IsNullOrEmpty(coreTopic);
            // R314 (L3 主动澄清): 连续偏题达更高阈值 → 提示升级为二选一问句 (把"是否回锚"变显式对话状态)。
            // 阈值 env AGENTFRAMEWORK_TOPIC_CLARIFY_THRESHOLD (默认 4); 开关 AGENTFRAMEWORK_TOPIC_CLARIFY=0 关闭。
            var clarifyEnabled = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_TOPIC_CLARIFY") != "0";
            var clarifyThreshold = int.TryParse(Environment.GetEnvironmentVariable("AGENTFRAMEWORK_TOPIC_CLARIFY_THRESHOLD"), out var _ct2) && _ct2 >= _steerThreshold ? _ct2 : _steerThreshold + 2;
            var clarifyPending = clarifyEnabled && steeringPending && _consecutiveDrift >= clarifyThreshold;
            if (steeringPending && topicVerdict is not null)
            {
                // R308b: steering 并入 topic_relevance 打点 (steering 标志位 — 不再独立点位)。
                agent.config.AgentTelemetry.Emit("topic_relevance", "IndustrialAgentV2",
                    ("verdict", "SteerHint"), ("core", coreTopic),
                    ("consecutive", _consecutiveDrift),
                    ("stage", clarifyPending ? "clarify" : "steering"));
                if (clarifyPending) { _clarifyArmed = true; _clarifyTurnsLeft = 2; }  // R315
            }
            
            // 6. ✅ 将消息添加到会话
            await AddToSessionAsync(message, llmResponse, ct);
            
            // 7. 存储到记忆
            await StoreToMemoryAsync(message, llmResponse, intent, ct);

            // 7.5 会话长期记忆回写 (v7.14): 每轮摘要入滚动记忆, 目标句从首轮任务锚定
            try
            {
                var memSession = await _sessionManager.GetOrCreateSessionAsync(message.SessionId, message.SenderId ?? "cli-user");
                var mem = memSession.Memory;
                // v0.11.0 R39 (真缺陷 25): goal 只在空时锚定且永不更新 — 用户任务转向
                // ("算了改成X")后新方向与旧 goal 实体零重叠, 后续轮全被误隔离 (实测爬虫→API 4轮中2轮被隔离)。
                // 现策略: 任务转向显式标记 → 重新锚定 goal 跟随最新任务方向。
                var goalText = message.Content.Length > 200 ? message.Content[..200] + "…" : message.Content;
                // v0.11.0 R72 (真缺陷 31): 词表覆盖漏洞 — "不要之前的目标" 不含 "不要了" → 未 pivot → 明确
                // 放弃旧目标的请求被误隔离。补: 不要之前/放弃/重新开始/取消之前/先不做 + "写首诗/做个X" 显式新任务词
                var isPivot = PivotMarkers.Any(m => message.Content.Contains(m, StringComparison.Ordinal));
                // v0.11.0 R70 (真缺陷 30): SetGoal constraints 参数从未传入 (死代码链) — 约束陈述
                // ("只能用X/不许用Y/必须Z") 提取为结构化 Constraints, 注入 prompt 【约束】行
                var constraints = ExtractConstraints(message.Content);
                if (string.IsNullOrEmpty(mem.Goal?.GoalText) && IsGoalWorthy(message.Content))
                {
                    // v0.11.0 (打点驱动修复): goal 锚定时抽取关键实体 — 实体空导致隔离判定永不触发
                    mem.SetGoal(goalText, agent.intent.TaskRelevanceChecker.ExtractEntities(goalText), intent, constraints);
                }
                // v0.11.0 R72b: pivot 不受 IsGoalWorthy 门槛 — 显式放弃旧目标本身即强重锚信号
                // ("不要之前的目标了，给我写首诗" 无 taskMarker 曾被短路跳过 → 新任务全被误隔离)
                else if (isPivot && message.Content.Length >= 4)
                {
                    mem.SetGoal(goalText, agent.intent.TaskRelevanceChecker.ExtractEntities(goalText), intent, constraints);
                    agent.config.AgentTelemetry.Emit("goal", "IndustrialAgentV2",
                        ("op", "pivot"), ("goal", goalText.Length > 40 ? goalText[..40] + "…" : goalText));
                }
                // v0.11.0 R33: 记录用户信息本身 (前 60 字) — 意图/状态后置;
                // 旧格式 "[general] 完成: 记住我最喜欢的颜色是蓝色" 让偏好检索时被流水账前缀淹没
                var brief = message.Content.Length > 60 ? message.Content[..60] + "…" : message.Content;
                mem.Remember($"{brief} ({(llmResponse.Success ? $"{intent} 完成" : $"{intent} 失败")})");
                // v0.11.0 R66 (真缺陷 29): 里程碑记意图名 ('general') 零信息量 — 记消息摘要才有进度画像价值
                if (llmResponse.Success)
                    mem.AddMilestone(brief);
                _sessionMemoryStore.Save(memSession.Id, mem);

                // agent 画像动态学习 (④): 任务类别胜率 + 工具亲和
                var learnUid = message.SenderId is { Length: > 0 } ? message.SenderId : "main";
                _agentProfileStore.GetOrCreate(learnUid)
                    .RecordTaskOutcome(intent, llmResponse.Success);
                _agentProfileStore.Save();

                // R365 (v0.21.0): 赏罚信号接主链 — 纠正检测 (两级: L1 规则 0tok / L2 微 prompt ~140tok)
                // + 推理中止失败簇 (自体信号) + Role 成长账本写回。LLM 判定走后台 Task 不阻塞响应。
                // R365 门禁 (用户钦定): 赏罚是 Role 的能力 — 无 role (GrowthLedger null) 时整链失效:
                // 不起后台 Task / 不调 LLM / 不写失败簇 / 联想前置注入自动关闭 (null 安全空返回)。
                if (GrowthLedger is not null)
                {
                    if (llmResponse.Success)
                    {
                        var lastReply = _lastReplyBySession.GetValueOrDefault(memSession.Id);
                        var question = message.Content;
                        var domainKey = intent;
                        _ = Task.Run(async () =>
                        {
                            try
                            {
                                var verdict = await agent.roles.CorrectionDetector.JudgeAsync(
                                    question, lastReply ?? "",
                                    async (prompt, maxTokens) => await DetectViaLlm(prompt, maxTokens), ct);
                                GrowthLedger.Record(verdict.Kind, domainKey);
                            }
                            catch { /* 赏罚失败不影响主链 */ }
                        }, ct);
                        _lastReplyBySession[memSession.Id] = llmResponse.Content;
                    }
                    else
                    {
                        // LLM 失败 = 自体失败信号 → 失败簇记罚 (超时/错误类)
                        _failureClusters.RecordAbort("limit", message.Content);
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "会话记忆回写失败 (不影响本轮响应)");
            }

            if (!llmResponse.Success)
            {
                response.Content = string.Empty;
                response.Success = false;
                // LLM 失败原因必须透传 (否则 Success=False + Error 空, 调用方无从排查)
                response.Error = llmResponse.Error;
                response.AgentState = AgentState.Ready; // LLM 失败≠Agent 故障, 保持可用
            }
            else
            {
                // 返回后处理 (v7.11): 区段快速标记 → 插件路由 (UI 捕获/审查服务等, 不写死)
                response.Content = await _segmentRouter.ProcessAsync(llmResponse.Content, ct);
                // R374 (D3): 运行结果回流 — 产物机器校验失败 → 失败输出回灌模型 → 有界修复 1 轮 → 复检。
                // 诚实边界: 未修好则不替换正文 (不假装成功); 事实经 telemetry artifact_feedback 落盘。
                _artifactRepair ??= new agent.registry.ArtifactRepairLoop(_segmentRouter, _llmCaller);
                response.Content = (await _artifactRepair.RunAsync(response.Content, ct)).Content;
                // v0.22.0 exp9 D3: 计划真执行 — 产物就绪后跑本地节点 (零 token; 不再用哑执行体)。
                // 诚实边界: 本地节点结论只作审计/证据 (run.Outcomes + telemetry plan_node), 失败不阻断主链。
                if (_lastPlan is not null)
                {
                    _planRemoteReadyUs = agent.intent.Monotonic.NowUs();
                    _lastPlanRun = await RunPlanAsync(_lastPlan, response.Content, ct, _localFirst);

                    // D4b: 被出站扣减的本地子请求 → 框架自渲染结论并入回复。
                    // 这些子请求已经不在发给模型的文本里, 模型不会回答它们 ⇒ 用户可见结论必须由框架补上;
                    // 本地节点失败也如实写 (不静默), 否则等于"把用户的问题删了还不回答"。
                    if (_planAblation is { Applied: true } && _lastPlanRun is not null)
                    {
                        var outcomeById = _lastPlanRun.Outcomes.ToDictionary(o => o.NodeId, StringComparer.Ordinal);
                        var items = new List<agent.intent.LocalAnswerItem>();
                        foreach (var n in _lastPlan.LocalizedRequestNodes)
                        {
                            var ok = outcomeById.TryGetValue(n.Id, out var o)
                                && o.State == agent.intent.PlanNodeState.Completed;
                            items.Add(new agent.intent.LocalAnswerItem(n.Text, o?.Detail, ok));
                        }

                        var localSection = agent.intent.PlanLocalAnswer.Render(items);
                        if (localSection.Length > 0)
                        {
                            response.Content += localSection;
                            agent.config.AgentTelemetry.Emit("plan_local_answer", "IndustrialAgentV2",
                                ("items", items.Count), ("ok", items.Count(i => i.Ok)),
                                ("chars", localSection.Length));
                        }
                    }
                }
                // R307 (L1 轻牵引): 连续 ≥2 轮偏题 → 回复尾追加衔接提示 (区段路由后追加, 防被路由过滤)。
                if (clarifyPending)
                    response.Content += $"\n\n> 💡 需要我回到「{coreTopic}」继续, 还是继续当前话题? 直接说一声即可。";
                else if (steeringPending)
                    response.Content += $"\n\n> 💡 提示: 本轮话题与近期核心主题「{coreTopic}」有所偏离 — 如需继续核心任务随时说一声。";
                response.Success = true;

                // 任务循环完成 → 下轮预估落盘 (v7.11): 工作目录 + 按 agent UID 隔离
                var saved = agent.registry.NextTurnForecast.Save(_dataStoragePath, identity.Uid, message.Content, intent);

                // v0.11.0 R14: 用户倾向写入链路修复 — 此前 UpdateTendencyAsync 无人调用, UserTendency 源恒 0
                // v0.11.0 R34: 改同步 await — fire-and-forget 在 /exit 快速退出时被杀,
                // 落盘永不及写 (真机实测 2 轮皆空); 纯内存计算 <1ms, 不值得异步化。
                try
                {
                    var tendency = new agent.tendency.TendencyData
                    {
                        UserId = message.SenderId ?? "anonymous",
                        Timestamp = DateTime.UtcNow,
                    };
                    foreach (var kv in agent.tendency.TendencyAnalyzer.ExtractSignals(message.Content))
                    {
                        tendency.TopicScores[kv.Key] = kv.Value;
                    }
                    await _tendencyAnalyzer.UpdateTendencyAsync(tendency.UserId, tendency);
                    agent.config.AgentTelemetry.Emit("tendency", "IndustrialAgentV2",
                        ("op", "update"), ("ok", true), ("signals", tendency.TopicScores.Count));
                }
                catch (Exception tenEx)
                {
                    agent.config.AgentTelemetry.Emit("tendency", "IndustrialAgentV2",
                        ("op", "update"), ("ok", false), ("error", tenEx.GetType().Name));
                }
                response.Data = new Dictionary<string, object>
                {
                    { "intent", intent },
                    { "promptTokens", prompt.EstimatedTokens },
                    { "contextSnippets", contextResult.Snippets.Count },
                    { "llmModel", llmResponse.Model },
                    { "forecastTendency", saved.Tendency },
                    { "forecastAgentUid", saved.AgentUid },
                };
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing message");
            response = AgentResponse.ErrorResponse(ex.Message);
        }
        
        response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
        // v0.11.0 R62: 台账度量字段 — 问询数 (回复含问句) 与 executive 直达标记
        var asked = response.Content.Contains('？') || response.Content.Contains('?');
        agent.config.AgentTelemetry.Emit("loop_turn", "IndustrialAgentV2",
            ("total_ms", response.ExecutionTimeMs), ("success", response.Success),
            ("reply_chars", response.Content.Length), ("asked", asked),
            ("executive", response.Content.StartsWith('{') && response.Content.Contains("\"skill\"")));
        return response;
    }
    
    /// <summary>
    /// v0.11.0 R70 (真缺陷 30): 从任务陈述提取约束子句 ("约束：X"/"只能X"/"不许Y"/"必须Z"/"避免W")。
    /// 零 LLM 纯规则; 每约束截 60 字; 上限 8 条 (防噪声)。
    /// </summary>
    internal static List<string> ExtractConstraints(string text)
    {
        var constraints = new List<string>();
        if (string.IsNullOrWhiteSpace(text)) return constraints;
        // 冒号显式标记: "约束：..." / "限制：..." 整段
        var markers = new[] { "约束", "限制", "要求" };
        foreach (var m in markers)
        {
            var idx = text.IndexOf(m + "：", StringComparison.Ordinal);
            if (idx < 0) idx = text.IndexOf(m + ":", StringComparison.Ordinal);
            if (idx >= 0)
            {
                var seg = text[(idx + m.Length + 1)..];
                var end = seg.IndexOfAny(new[] { '。', '；', ';', '\n' });
                var constraint = (end > 0 ? seg[..end] : seg).Trim();
                if (constraint.Length > 0)
                    constraints.Add(constraint.Length > 60 ? constraint[..60] + "…" : constraint);
            }
        }
        // 助动词模式: "只能/不许/不准/必须/避免" + 分隔
        string[] auxMarkers = { "只能", "不许", "不准", "必须", "避免" };
        foreach (var aux in auxMarkers)
        {
            var idx = text.IndexOf(aux, StringComparison.Ordinal);
            if (idx < 0) continue;
            var seg = text[idx..];
            var end = seg.IndexOfAny(new[] { '。', '，', '；', ';', '\n' });
            var constraint = (end > 0 ? seg[..end] : seg).Trim();
            if (constraint.Length > 1 && !constraints.Any(c => constraint.Contains(c) || c.Contains(constraint)))
                constraints.Add(constraint.Length > 60 ? constraint[..60] + "…" : constraint);
            if (constraints.Count >= 8) break;
        }
        return constraints;
    }

    #region Core Methods
    
    /// <summary>
    /// EvidenceGate 裁定 → ClarificationBatch 真实批量问询 (v7.14 ①)。
    /// 低置信子任务 (置信度<阈值 或 MissingParameter) 生成疑问组; 有问询服务时 REPL 弹批量问题,
    /// 用户答案 (模式化, 绝不落凭据) 记入偏好库并拼为补充说明; 无服务/无疑问/问询失败 → 原样放行 (不阻断)。
    /// </summary>

    /// <summary>
    /// 1.6 影子计划 (v7.15 归拢接线 T.2-4 第一步):
    /// TaskPlanBuilder.Build + TaskPlanExecutor 以哑 nodeRunner 演练计划调度语义
    /// (依赖拓扑/敏感审批/取消/问询需求), 只记录不采纳 — 主链行为不变。
    /// 演练结果: 日志摘要 (节点数/终态); /plan JSON 可读 TaskPlanRun。
    /// 影子一致性判据 (T.4-2 定案): 本阶段只验证"计划结构可执行+问询需求已知",
    /// 节点输出对比在执行器并发化 (plan_executor_parallel) 接真 nodeRunner 后进行。
    /// </summary>
    /// <summary>
    /// /model 与 /balance 指令处理 (v7.15 模型队列): 全 JSON 输出。
    ///   /model             → 当前活跃模型 + 选模依据 (JSON)
    ///   /model &lt;id&gt;       → 手动指定 (目录校验)
    ///   /model auto        → 恢复自动
    ///   /model verify &lt;id&gt; → 目录参数真实性校验 (假 key 探测, C.6.5)
    ///   /balance [id]      → 余额查询 (scheme 分派, 诚实报错)
    /// 返回 null = 非本组指令 (放行主链)。
    /// </summary>
    /// <summary>
    /// R356-c: 前端 state.snapshot 数据源 — 聚合模型路由/会话/运行时长真实状态。
    /// 零副作用 (只读), 供 FrontendApi 消费。
    /// </summary>
    public AgentSnapshot GetSnapshot()
    {
        var active = _modelRouter?.ActiveModel;
        return new AgentSnapshot(
            SessionId: "frontend-main",
            ModelId: active?.Id,
            ModelProvider: active?.Provider,
            SelectionBasis: _modelRouter?.LastSelectionBasis ?? "none",
            SelectionMode: _modelRouter?.ManualOverride is null ? "auto" : "manual",
            ModelSwitches: _modelRouter?.Switches.Count ?? 0,
            UptimeMs: Environment.TickCount64 - _startTicks);
    }


    private AgentResponse? HandleModelCommand(string input, long elapsedMs)
    {
        var parts = input.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        var head = parts[0].ToLowerInvariant();

        // R351: /official-key 指令移除 (官方通道已废弃 — 用户钦定全 API 化)


        if (head == "/model")
        {
            if (_modelRouter is null)
            {
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "model", Ok = false, Error = "model_queue_not_configured",
                }, elapsedMs);
            }
            if (parts.Length == 1)
            {
                var active = _modelRouter.ActiveModel;
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "model",
                    Ok = true,
                    Active = active?.Id ?? "(empty)",
                    Provider = active?.Provider,
                    ReasoningScore = active?.ReasoningScore ?? 0,
                    CodingScore = active?.CodingScore ?? 0,
                    LastSelection = _modelRouter.LastSelectionBasis,
                    Switches = _modelRouter.Switches.Count,
                    Mode = _modelRouter.ManualOverride is null ? "auto" : "manual",
                }, elapsedMs);
            }

            // /model list: 可用模型列表 (序号 1-N — 序号可直接用于 /model <序号>)
            if (parts[1].Equals("list", StringComparison.OrdinalIgnoreCase))
            {
                var activeNow = _modelRouter.ActiveModel;
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "model_list",
                    Ok = true,
                    Active = activeNow?.Id ?? "(empty)",
                    Mode = _modelRouter.ManualOverride is null ? "auto" : "manual",
                    Models = _modelRouter.Catalog.Models.Select((m, i) => new ModelListItem
                    {
                        Index = i + 1,
                        Id = m.Id,
                        Description = m.Description,
                        Provider = m.Provider,
                        PriceInPerM = m.PriceInPerM,
                        PriceOutPerM = m.PriceOutPerM,
                        ReasoningScore = m.ReasoningScore,
                        CodingScore = m.CodingScore,
                        ContextWindow = m.ContextWindow,
                        IsActive = m.Id == activeNow?.Id,
                    }).ToList(),
                }, elapsedMs);
            }

            // /model <序号>: 按列表序号指定模型 (1-N; 序号即 /model list 的 Index)
            if (int.TryParse(parts[1], System.Globalization.NumberStyles.Integer,
                    System.Globalization.CultureInfo.InvariantCulture, out var idx) && idx >= 1)
            {
                var list = _modelRouter.Catalog.Models;
                if (idx <= list.Count)
                {
                    var chosen = list[idx - 1];
                    var okIdx = _modelRouter.SetManualOverride(chosen.Id);
                    if (okIdx)
                    {
                        return MakeJsonResponse(new ModelCommandPayload
                        {
                            Command = "model",
                            Ok = true,
                            Target = chosen.Id,
                            Active = chosen.Id,
                            Provider = chosen.Provider,
                            Mode = "manual",
                            Note = $"selected_by_index:{idx}",
                        }, elapsedMs);
                    }
                }
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "model",
                    Ok = false,
                    Target = parts[1],
                    Error = $"index_out_of_range (1-{list.Count}, 见 /model list)",
                }, elapsedMs);
            }
            if (parts[1].Equals("verify", StringComparison.OrdinalIgnoreCase) && parts.Length >= 3)
            {
                var v = _verifyService?.VerifyAsync(parts[2]).GetAwaiter().GetResult();
                // v0.11.0: 命令执行恒成功 (Success=true) — 校验结论在 Ok/Verdict 字段,
                // 不可达端点也如实输出 JSON (Ok:false + UNREACHABLE) 而非吞进失败渲染
                var payload = new ModelCommandPayload
                {
                    Command = "model_verify",
                    Ok = v?.Ok ?? false,
                    Active = v?.Model ?? parts[2],
                    HttpStatusCode = v?.HttpStatusCode ?? 0,
                    Verdict = NonEmpty(v?.Verdict, v?.Error, "verify_service_unavailable"),
                };
                var json = System.Text.Json.JsonSerializer.Serialize(
                    payload, ModelCommandJsonContext.Default.ModelCommandPayload);
                return new AgentResponse
                {
                    Success = true,
                    Content = json,
                    ExecutionTimeMs = elapsedMs,
                };
            }
            // R349: /model verify-all — 全目录并发校验 (免费池 52 条目真机探针; 汇总渲染)
            if (parts[1].Equals("verify-all", StringComparison.OrdinalIgnoreCase))
            {
                if (_verifyService is null)
                {
                    return MakeJsonResponse(new ModelCommandPayload
                    {
                        Command = "model_verify_all", Ok = false, Error = "verify_service_unavailable",
                    }, elapsedMs);
                }
                var all = _verifyService.VerifyAllAsync().GetAwaiter().GetResult();
                var okCount = all.Count(v => v.Ok);
                var sb = new System.Text.StringBuilder();
                sb.Append($"模型目录全量校验: {okCount}/{all.Count} 合法 (假 key 探针, HTTP 401/403/429=地址真实)\n");
                foreach (var g in all.GroupBy(v => v.Ok ? "ok" : "bad"))
                {
                    if (g.Key == "ok")
                    {
                        sb.Append($"  ✓ 合法 {okCount}: ");
                        sb.Append(string.Join(", ", g.Select(v => v.Model)));
                        sb.Append('\n');
                    }
                }
                var bad = all.Where(v => !v.Ok).ToList();
                if (bad.Count > 0)
                {
                    sb.Append("  ✗ 异常 (人工复核):\n");
                    foreach (var v in bad)
                        sb.Append($"    {v.Model}: {NonEmpty(v.Verdict, v.Error, "unknown")}\n");
                }
                return new AgentResponse
                {
                    Success = true,
                    Content = sb.ToString(),
                    ExecutionTimeMs = elapsedMs + (long)(DateTime.UtcNow - DateTime.UtcNow).TotalMilliseconds,
                };
            }
            var target = parts[1];
            var okSet = _modelRouter.SetManualOverride(target);
            if (okSet)
            {
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "model", Ok = true, Target = target, Active = target,
                }, elapsedMs);
            }
            return MakeJsonResponse(new ModelCommandPayload
            {
                Command = "model",
                Ok = false,
                Target = target,
                Active = _modelRouter.ActiveModel?.Id ?? "(empty)",
                Error = "unknown_model_id (见 config/base/models.yaml)",
            }, elapsedMs);
        }

        // v0.10.0: /token stats — 用量统计 (总 token/按模型/按 provider/预估成本/余额快照)
        if (head == "/token" && parts.Length >= 2 && parts[1].Equals("stats", StringComparison.OrdinalIgnoreCase))
        {
            if (_tokenUsageService is null)
            {
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "token_stats", Ok = false, Error = "token_usage_not_configured",
                }, elapsedMs);
            }
            var st = _tokenUsageService.GetStats();
            return MakeJsonResponse(new TokenStatsPayload
            {
                Command = "token_stats",
                Ok = true,
                TotalTokens = st.TotalTokens,
                TokensByModel = st.TokensByModel,
                TokensByProvider = st.TokensByProvider,
                EstimatedCostUsd = Math.Round(st.EstimatedCostUsd, 4),
                Balances = st.Balances.ToDictionary(
                    kv => kv.Key,
                    kv => new BalanceEntryPayload
                    {
                        Provider = kv.Value.Provider,
                        Remaining = kv.Value.TotalRemaining,
                        At = kv.Value.At,
                        FromApi = kv.Value.FromApi,
                    }),
                BalanceFlag = _modelRouter?.LastBalanceFlag,
            }, elapsedMs);
        }

        if (head == "/balance")
        {
            if (_balanceService is null)
            {
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "balance", Ok = false, Error = "model_queue_not_configured",
                }, elapsedMs);
            }
            // v0.11.0 R89b (真缺陷 36 关联): /balance 无参应查当前实际活跃模型 —
            // 原传 null 落目录首项 (gpt-4o, 无 key), 与 auto 实际调用模型脱节。
            var balTarget = parts.Length >= 2 ? parts[1] : _modelRouter?.ActiveModel?.Id;
            var b = _balanceService.QueryAsync(balTarget)
                .GetAwaiter().GetResult();
            // v0.11.0: 命令执行恒 Success=true — 余额结论在 Ok/TotalRemaining/Error 字段,
            // 查询失败 (无 scheme/无 key/网络) 也如实 JSON 输出而非吞进失败渲染
            var json = System.Text.Json.JsonSerializer.Serialize(new ModelCommandPayload
            {
                Command = "balance",
                Ok = b.Ok,
                Active = b.Model,
                Provider = b.Provider,
                TotalGranted = b.TotalGranted,
                TotalUsed = b.TotalUsed,
                TotalRemaining = b.TotalRemaining,
                Error = b.Error,
                Note = b.Note,
            }, ModelCommandJsonContext.Default.ModelCommandPayload);
            return new AgentResponse
            {
                Success = true,
                Content = json,
                ExecutionTimeMs = elapsedMs,
            };
        }

        return null;
    }

    /// <summary>
    /// /log 指令 (v7.15 L.2.1): /log dump → MemoryLogBuffer 快照存档 JSON 行文件 (data/logs/log-{ts}.jsonl)。
    /// </summary>
    private AgentResponse? HandleLogCommand(string input, string sessionId, long elapsedMs)
    {
        var parts = input.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length < 2 || !parts[1].Equals("dump", StringComparison.OrdinalIgnoreCase))
        {
            return MakeJsonResponse(new ModelCommandPayload
            {
                Command = "log", Ok = false,
                Error = "用法: /log dump (子命令: dump)",
            }, elapsedMs);
        }
        if (_logRouter is null)
        {
            return MakeJsonResponse(new ModelCommandPayload
            {
                Command = "log", Ok = false, Error = "log_router_not_configured",
            }, elapsedMs);
        }
        var entries = _logRouter.SnapshotEntries();
        var dir = System.IO.Path.Combine(_dataStoragePath, "logs");
        System.IO.Directory.CreateDirectory(dir);
        var file = System.IO.Path.Combine(dir,
            $"log-{DateTime.UtcNow:yyyyMMdd-HHmmss}.jsonl");
        using (var writer = new System.IO.StreamWriter(file, append: false))
        {
            foreach (var e in entries)
            {
                writer.WriteLine(System.Text.Json.JsonSerializer.Serialize(
                    e, agent.logging.LogJsonContext.Default.LogEntry));
            }
        }
        return MakeJsonResponse(new ModelCommandPayload
        {
            Command = "log", Ok = true, Active = file,
            Switches = entries.Count,
        }, elapsedMs);
    }

    /// <summary>模型队列指令统一响应 (强类型 payload — source-gen 序列化, AOT 铁律)</summary>
    /// <summary>首个非空字符串 (verify 判定展示: Verdict 优先, Error 兜底)</summary>
    private static string NonEmpty(params string?[] values)
    {
        foreach (var v in values)
        {
            if (!string.IsNullOrWhiteSpace(v))
                return v;
        }
        return string.Empty;
    }

    private AgentResponse MakeJsonResponse(ModelCommandPayload payload, long elapsedMs)
    {
        var json = System.Text.Json.JsonSerializer.Serialize(
            payload, ModelCommandJsonContext.Default.ModelCommandPayload);
        return new AgentResponse
        {
            Success = payload.Ok,
            Content = json,
            ExecutionTimeMs = elapsedMs,
        };
    }

    /// <summary>v0.10.0: /token stats 专用 JSON 出口 (TokenStatsPayload 上下文)</summary>
    private AgentResponse MakeJsonResponse(TokenStatsPayload payload, long elapsedMs)
    {
        var json = System.Text.Json.JsonSerializer.Serialize(
            payload, ModelCommandJsonContext.Default.TokenStatsPayload);
        return new AgentResponse
        {
            Success = payload.Ok,
            Content = json,
            ExecutionTimeMs = elapsedMs,
        };
    }

    /// <summary>
    /// 计划构建 + 确定性路由 (v0.22.0 exp9 D1+D2): 拆解 → TaskPlan → 节点位置判定 → 追加本地验证节点。
    /// 只构建不执行 —— 本地节点的执行在产物就绪后 (RunPlanAsync), 避免"无对象空跑"。
    /// </summary>
    private TaskPlan BuildRoutedPlan(string sourceText, IReadOnlyList<IntentDecomposer.SubTask> subTasks)
    {
        var plan = RoutedPlanBuilder.Build(sourceText, subTasks);
        var local = plan.Nodes.Count(n => n.Location == NodeExecutionLocation.Local);
        var hybrid = plan.Nodes.Count(n => n.Location == NodeExecutionLocation.Hybrid);
        var remote = plan.Nodes.Count(n => n.Location == NodeExecutionLocation.Remote);
        _logger.LogInformation(
            "Plan {PlanId}: {Nodes} nodes → local={Local} hybrid={Hybrid} remote={Remote}",
            plan.PlanId, plan.Nodes.Count, local, hybrid, remote);
        agent.config.AgentTelemetry.Emit("plan_route", "IndustrialAgentV2",
            ("plan_id", plan.PlanId),
            ("nodes", plan.Nodes.Count),
            ("local", local),
            ("hybrid", hybrid),
            ("remote", remote));
        return plan;
    }

    /// <summary>
    /// 计划真执行 (v0.22.0 exp9 D3): 产物就绪后跑本地节点 (真子进程/真统计, 零 LLM 调用),
    /// 并把主链已生成的正文登记为远程节点产物 (**不二次调用模型**)。
    /// 失败只记录不阻断主链; 结论写 run.Outcomes + telemetry plan_node/plan。
    /// </summary>
    private async Task<TaskPlanRun?> RunPlanAsync(TaskPlan plan, string? remoteText, CancellationToken ct,
        LocalFirstRun? localFirst = null)
    {
        try
        {
            _planRunner ??= new agent.intent.PlanRunner();
            // 同一个 ctx 对象贯穿两阶段: 本地先行阶段的节点输出不能丢 (否则下游依赖取不到)
            var ctx = _planCtx ?? agent.intent.PlanRunner.NewContext();
            _planRunner.FillFromLedger(ctx);
            ctx.RemoteText = remoteText;
            var window = _planRemoteStartUs > 0
                ? new RemoteWindow(_planRemoteStartUs, _planRemoteReadyUs)
                : (RemoteWindow?)null;
            var run = await _planRunner.RunAsync(plan, ctx, ct, localFirst, window);

            // D7b: 计划停在"等用户 / 等产出" → 落续跑三件套 (蓝图 + 运行态 + 已完成节点真产出)。
            //     没有这一步, 用户下一轮的答复就没有消费方 —— 计划的 Waiting 会永远挂着 (结构缺口)。
            var store = _planCheckpoints ??= new agent.recovery.CheckpointStore(_dataStoragePath);
            if (agent.intent.PlanResumeService.Capture(
                    store, ctx.SessionId ?? "", plan, run, ctx.NodeOutputs, plan.SourceText))
            {
                agent.config.AgentTelemetry.Emit("plan_resume_capture", "IndustrialAgentV2",
                    ("plan_id", plan.PlanId),
                    ("state", run.State.ToString()),
                    ("awaiting", agent.intent.PlanResumeService.AwaitingNodeIdOf(run, plan) ?? ""),
                    ("outputs", ctx.NodeOutputs.Count),
                    ("waits", run.Waits.Count));
            }
            var localOk = run.Outcomes.Count(o =>
                o.Location is "local" or "hybrid" && o.State == PlanNodeState.Completed);
            var failed = run.Outcomes.Count(o => o.State == PlanNodeState.Failed);
            var skipped = run.Outcomes.Count(o => o.State == PlanNodeState.Skipped);
            _logger.LogInformation(
                "Plan {PlanId} executed: local_ok={LocalOk} failed={Failed} skipped={Skipped} (executors: {Executors})",
                plan.PlanId, localOk, failed, skipped, string.Join(",", _planRunner.WiredExecutors));
            return run;
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            // 计划失败不影响主链 (审计性质) — 但不静默: 告警 + 遥测
            _logger.LogWarning(ex, "Plan execution failed (non-fatal)");
            agent.config.AgentTelemetry.Emit("plan_exec_failed", "IndustrialAgentV2",
                ("plan_id", plan.PlanId), ("error", ex.GetType().Name));
            return null;
        }
    }

    /// <summary>最近一次路由后的计划 (D1+D2 产物; /plan 与前端事件读这里)</summary>
    private TaskPlan? _lastPlan;

    /// <summary>最近一次计划真执行记录 (D3 产物)</summary>
    private TaskPlanRun? _lastPlanRun;

    /// <summary>D4: 本地先行批次句柄 (无依赖本地节点, 计划构建时即启动)</summary>
    private LocalFirstRun? _localFirst;

    /// <summary>出站文本扣减结果 (v0.22.0 exp9 D4b): 已判本地执行的子请求片段 + 扣减后的出站正文。</summary>
    private agent.intent.AblationResult? _planAblation;

    /// <summary>D4: 贯穿两阶段的执行上下文 (本地先行 + 产物就绪后回填)</summary>
    private LocalNodeContext? _planCtx;

    /// <summary>D7b: 计划检查点仓库 (懒建) —— 暂停时写它, 下一轮装载入口读它</summary>
    private agent.recovery.CheckpointStore? _planCheckpoints;

    /// <summary>
    /// D7b 跨轮唤醒 (真续跑): 检查点 → 装载 → 答复落到确定参数槽 → 从**上轮运行态**继续跑。
    /// 三条硬纪律:
    ///   ① 不重拆: 走出这条路就**不再**把这一轮消息当新任务 (用户答的就是上一轮那个问题);
    ///   ② 不伪造: 唤醒等待节点喂的是检查点里的**真产出** (缺产出快照 = 装载入口直接拒绝);
    ///   ③ 不吞: 答复落不到确定位置 (无参数名 / 多条目 / 不在选项内) → 如实告诉用户并作废该检查点,
    ///      既不静默丢弃, 也不把答复硬塞进一个猜出来的槽。
    /// </summary>
    private async Task<bool> TryResumePausedPlanAsync(Message message, AgentResponse response, CancellationToken ct)
    {
        if (string.IsNullOrEmpty(message.SessionId))
            return false;

        var store = _planCheckpoints ??= new agent.recovery.CheckpointStore(_dataStoragePath);
        if (!agent.intent.PlanResumeService.TryLoad(store, message.SessionId, out var cand, out var why) || cand is null)
        {
            // 没有未完成计划 = 常态 (普通消息都走这里): 只在"有检查点却装不回来"时留痕, 不刷噪声
            if (why != agent.intent.PlanResumeService.RefuseNoCheckpoint)
                agent.config.AgentTelemetry.Emit("plan_resume", "IndustrialAgentV2",
                    ("resumed", false), ("reason", why));
            return false;
        }

        if (!agent.intent.PlanResumeService.ApplyReply(cand, message.Content, out var applyWhy))
        {
            store.Clear(message.SessionId);
            response.Success = false;
            response.Content =
                $"上一轮计划停在等你回答: {Truncate(cand.PendingQuestion ?? "(无问题文本)", 120)}\n" +
                $"这一轮答复没有落地: {applyWhy}\n" +
                "该续跑入口已作废 —— 请把这一轮内容重新表述为完整任务, 或按上面的问题再答一次。";
            agent.config.AgentTelemetry.Emit("plan_resume", "IndustrialAgentV2",
                ("plan_id", cand.Plan.PlanId), ("resumed", false), ("reason", applyWhy));
            return true;
        }

        // 续跑: 重建 ctx (真产出注入) → 从 seedRun 继续 (Completed 节点不重跑)
        var ctx = agent.intent.PlanRunner.NewContext(
            sessionId: message.SessionId, sourceText: cand.SourceText ?? message.Content);
        foreach (var kv in cand.NodeOutputs)
            ctx.NodeOutputs[kv.Key] = kv.Value;
        _planRunner ??= new agent.intent.PlanRunner();
        _planCtx = ctx;
        _lastPlan = cand.Plan;

        var run = await _planRunner.RunAsync(cand.Plan, ctx, ct,
            localFirst: null, remoteWindow: null, seedRun: cand.Run);
        _lastPlanRun = run;

        agent.config.AgentTelemetry.Emit("plan_resume", "IndustrialAgentV2",
            ("plan_id", cand.Plan.PlanId), ("resumed", true), ("state", run.State.ToString()),
            ("nodes", cand.Plan.Nodes.Count), ("waits", run.Waits.Count),
            ("seeded_outputs", cand.NodeOutputs.Count),
            ("slot", string.Join(",", cand.AwaitingParameterNames)));

        response.Success = run.State == TaskPlanRunState.Finished;
        response.Content = RenderResumeReply(cand, run);
        response.Data = new Dictionary<string, object>
        {
            { "planResumed", true },
            { "planId", cand.Plan.PlanId },
            { "planState", run.State.ToString() },
            { "awaitingNode", cand.AwaitingNodeId },
        };

        if (run.State == TaskPlanRunState.Finished)
            store.Clear(message.SessionId); // 跑完不留悬空的续跑入口
        else
            agent.intent.PlanResumeService.Capture(store, message.SessionId, cand.Plan, run, ctx.NodeOutputs, cand.SourceText);
        return true;
    }

    /// <summary>续跑答复渲染 (零 LLM): 节点结果 + 等待台账 (等待时长含用户思考时间, 是真账不是估计)。</summary>
    private static string RenderResumeReply(agent.intent.PlanResumeCandidate cand, TaskPlanRun run)
    {
        var sb = new System.Text.StringBuilder();
        sb.Append("🔄 续跑计划 ").Append(cand.Plan.PlanId)
          .Append(" (答复落到参数槽: ").Append(string.Join(",", cand.AwaitingParameterNames)).Append(')');
        if (!string.IsNullOrEmpty(cand.PendingQuestion))
            sb.Append("\n上一轮的问题: ").Append(Truncate(cand.PendingQuestion, 100));
        sb.Append('\n');
        foreach (var o in run.Outcomes)
            sb.Append("- ").Append(o.NodeId).Append(" [").Append(o.Location).Append("] ")
              .Append(o.State).Append(": ").Append(Truncate(o.Detail ?? string.Empty, 90)).Append('\n');
        if (run.Waits.Count > 0)
        {
            var now = agent.intent.Monotonic.NowUs();
            var totalMs = run.Waits.Values.Sum(w => ((w.EndedUs ?? now) - w.StartedUs) / 1000);
            sb.Append("等待台账: ").Append(run.Waits.Count).Append(" 条, 共 ").Append(totalMs)
              .Append("ms (含你思考的时间; 等待不占并发额度)").Append('\n');
        }
        sb.Append("计划状态: ").Append(run.State);
        return sb.ToString();
    }

    /// <summary>D4: 远程窗口起点 (计划构建时刻; 用于 "本地先行与远程等待真重叠" 测量)</summary>
    private long _planRemoteStartUs;

    /// <summary>D4: 远程窗口终点 (本轮产物/正文就绪时刻)</summary>
    private long _planRemoteReadyUs;

    /// <summary>计划真执行体 (v0.22.0 exp9 D3; DI 注入失效时回退默认实现 — 有台账才能拿到产物路径)</summary>
    private agent.intent.PlanRunner? _planRunner;

    private async Task<string> RunEvidenceGateAsync(
        Message message, IReadOnlyList<IntentDecomposer.SubTask> subTasks, CancellationToken ct)
    {
        if (_promptService == null || subTasks.Count == 0)
            return string.Empty;
        try
        {
            var gate = new agent.registry.EvidenceGate();
            var verdict = gate.Evaluate(subTasks);
            // v0.11.0: evidence gate 打点 (问询触发率对比数据)
            agent.config.AgentTelemetry.Emit("evidence_gate", "IndustrialAgentV2",
                ("subtasks", subTasks.Count),
                ("suspects", subTasks.Count(t => t.Confidence < 0.60)),
                ("to_ask", verdict.ToAsk.Count),
                ("confidences", string.Join(",", subTasks.Select(t => Math.Round(t.Confidence, 2)))));
            if (verdict.ToAsk.Count == 0)
                return string.Empty;

            // 批量问询: 同组问题一次给出 (组=子任务), 符合"按内部分组直接给出多个或一个"铁律
            var prefs = new agent.registry.ClarificationPreferenceStore(_dataStoragePath);
            var answers = new List<string>();
            foreach (var req in verdict.ToAsk)
            {
                if (req.Questions.Count == 0)
                    continue;
                var batch = await agent.registry.ClarificationBatch.AskAsync(
                    _promptService, $"EvidenceGate/{req.SubTask.Intent}", req.Questions,
                    preferences: prefs, ct: ct);
                foreach (var a in batch.Answers)
                {
                    if (a.Answered && !string.IsNullOrWhiteSpace(a.Value))
                        answers.Add($"{a.Item.Question} → {a.Value}");
                }
            }
            return answers.Count > 0 ? string.Join("; ", answers) : string.Empty;
        }
        catch (OperationCanceledException) { throw; }
        catch (Exception ex)
        {
            // 问询链故障绝不阻断主流程 (降级: 带疑问直接执行, 与无 v7.14 行为一致)
            _logger.LogWarning(ex, "EvidenceGate 问询失败, 降级为直接执行");
            return string.Empty;
        }
    }

    /// <summary>R302: 数据源选择 + K1 全隔离 (env AGENTFRAMEWORK_K1_FULL_ISOLATION=1 → 剔除画像回流源)。</summary>
    private HashSet<DataSourceType> BuildEnabledSources(
        IReadOnlyList<IntentDecomposer.SubTask> subTasks, string intent)
    {
        var sources = subTasks.Count > 1
            ? new HashSet<DataSourceType>(IntentDecomposer.AggregateSources(subTasks))
            : new HashSet<DataSourceType>(IntentSourceMapping.GetSources(intent));
        if (Environment.GetEnvironmentVariable("AGENTFRAMEWORK_K1_FULL_ISOLATION") == "1")
        {
            sources.Remove(DataSourceType.Memory);
            sources.Remove(DataSourceType.Session);
            sources.Remove(DataSourceType.UserTendency);
            sources.Remove(DataSourceType.FixMemory); // v0.14.0: 自审修法记忆属经验注入, K1 对照实验须剔除
            agent.config.AgentTelemetry.Emit("k1_isolation", "IndustrialAgentV2",
                ("remaining", string.Join(",", sources)));
        }
        return sources;
    }

    private async Task<ContextAssemblyResult> AssembleContextAsync(
        Message message,
        string intent,
        IReadOnlyList<IntentDecomposer.SubTask> subTasks,
        CancellationToken ct)
    {
        var request = new ContextAssemblyRequest
        {
            UserMessage = message.Content,
            SessionId = message.SessionId,
            UserId = message.SenderId,
            Intent = intent,
            MaxTokenBudget = _maxTokenBudget,
            EnableCompression = true,
            MinRelevanceScore = 0.3,
            
            // Session 历史不在此处注入: GetConversationHistoryAsync + BuildWithHistory 是专用通道,
            // 双路注入同一批消息会浪费 token 并让 LLM 看到重复内容
            // 多子任务时数据源取并集 (search+code_gen 复合句 → 网搜+记忆全开)
            EnabledSources = BuildEnabledSources(subTasks, intent),
            // v0.11.0 R11: 工作区根传给装配器 (WorkspaceFiles 源)。
            // Workspace.Initialize 无人调用 (R11b 修复) — RootPath 空 → fallback 当前目录 (host 由 cwd 决定)。
            WorkspaceRoot = _workspace is { RootPath: { Length: > 0 } root } ? root : Environment.CurrentDirectory
        };

        // v7.14: 会话长期记忆 + 目标画像预渲染 (③) — 上下文压缩的方向锚 (⑥)
        try
        {
            var session = await _sessionManager.GetOrCreateSessionAsync(
                message.SessionId, message.SenderId);
            var mem = session.Memory;
            var rendered = mem.RenderForPrompt();
            // R302 (K1 全隔离): 隔离时 SessionMemory 也不注入 (R301 实证: 画像事实经此通道回流)。
            var k1FullIso = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_K1_FULL_ISOLATION") == "1";
            if (!string.IsNullOrEmpty(rendered) && !k1FullIso)
            {
                request.SessionMemoryBlock = rendered;
                if (!request.EnabledSources.Contains(agent.context.DataSourceType.SessionMemory))
                    request.EnabledSources.Add(agent.context.DataSourceType.SessionMemory);
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "会话记忆块渲染失败 (降级: 不注入)");
        }

        // v0.14.0 T2d: 修法记忆预渲染 (输出侧经验 — 生成前少样本注入; R302 同款 K1 隔离门)
        try
        {
            var fixMem = _fixMemory ?? agent.critique.FixMemory.Load(
                Path.Combine(_dataStoragePath, "fix-memory.json"));
            var anchorText = message.Content;
            var hits = fixMem.Recall(anchorText, topK: 3);
            if (hits.Count > 0
                && Environment.GetEnvironmentVariable("AGENTFRAMEWORK_K1_FULL_ISOLATION") != "1")
            {
                var sbFix = new StringBuilder("已确认修法 (历史评审反馈, 生成时避免重蹈):\n");
                foreach (var h in hits)
                    sbFix.Append($"- 模式『{h.Pattern}』: {h.Mechanism} → {h.Fix}\n");
                request.FixMemoryBlock = sbFix.ToString();
                if (!request.EnabledSources.Contains(agent.context.DataSourceType.FixMemory))
                    request.EnabledSources.Add(agent.context.DataSourceType.FixMemory);
                agent.config.AgentTelemetry.Emit("fix_memory", "IndustrialAgentV2",
                    ("recall_hits", hits.Count), ("anchor_chars", anchorText.Length));
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "修法记忆渲染失败 (降级: 不注入)");
        }

        // v0.15.2: 警告/铁律预渲染 (GuardrailMemory — 逻辑三元组, 域+模式双键 recall;
        // 心理学: 前置注入优于事后纠正; 同会话去重防 habituation — _injectedGuardrails)
        try
        {
            _guardrailMemory ??= agent.critique.GuardrailMemory.Load(
                Path.Combine(_dataStoragePath, "guardrails.json"));
            // 领域锚: GoalText 优先 (任务域) — coreTopic 在 L535 区已算但此作用域可见性待查, 直接用 Goal
            var grDomain = _sessionMemoryStore.Load(message.SessionId)?.Goal?.GoalText ?? "";
            var grHits = _guardrailMemory.Recall(grDomain, message.Content, topK: 2);
            var fresh = grHits.Where(h => !_injectedGuardrails.Contains(h.Id)).ToList();
            if (fresh.Count > 0
                && Environment.GetEnvironmentVariable("AGENTFRAMEWORK_K1_FULL_ISOLATION") != "1")
            {
                request.GuardrailBlock = agent.critique.GuardrailMemory.Render(fresh);
                if (!request.EnabledSources.Contains(agent.context.DataSourceType.GuardrailMemory))
                    request.EnabledSources.Add(agent.context.DataSourceType.GuardrailMemory);
                foreach (var h in fresh)
                    _injectedGuardrails.Add(h.Id); // 同会话去重 (habituation 防护)
                agent.config.AgentTelemetry.Emit("guardrail", "IndustrialAgentV2",
                    ("injected", (object)fresh.Count),
                    ("domain", (object)grDomain[..Math.Min(30, grDomain.Length)]));
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "警告铁律渲染失败 (降级: 不注入)");
        }

        // v7.14: agent 画像 + 能力清单预渲染 (④⑤)
        try
        {
            var agentUid = message.SenderId is { Length: > 0 } ? message.SenderId : "main";
            var profile = _agentProfileStore.GetOrCreate(agentUid);
            var blocks = new List<string>();
            // R362 (v0.21.0): Role 块注入 — 语风种子 + 赏罚成长实况 (排在 agent 画像之前: 角色人格优先)
            if (ActiveRole is not null)
            {
                var roleSb = new System.Text.StringBuilder($"【角色:{ActiveRole.Name}】");
                if (!string.IsNullOrEmpty(ActiveRole.ProfileSeed))
                    roleSb.Append('\n').Append(ActiveRole.ProfileSeed);
                var growthBlock = GrowthLedger?.RenderForPrompt();
                if (!string.IsNullOrEmpty(growthBlock))
                    roleSb.Append('\n').Append(growthBlock);
                // R365 (v0.21.0): 推理中止失败簇前置注入 — 命中该问题所属簇罚分 ≥3 时注入策略警告
                // (先澄清边界 → 降级方案 → 诚实说明做不到的部分)。无 role 时不进入此分支 (整链失效)。
                var abortWarning = _failureClusters.RenderWarning(message.Content);
                if (!string.IsNullOrEmpty(abortWarning))
                    roleSb.Append('\n').Append(abortWarning);
                blocks.Add(roleSb.ToString());
            }
            var profileRendered = profile.RenderForPrompt();
            if (!string.IsNullOrEmpty(profileRendered))
                blocks.Add(profileRendered);
            var capRendered = _capabilityScanner.RenderForPrompt();
            if (!string.IsNullOrEmpty(capRendered))
                blocks.Add(capRendered);
            if (blocks.Count > 0)
            {
                request.AgentContextBlock = string.Join("\n\n", blocks);
                if (!request.EnabledSources.Contains(agent.context.DataSourceType.AgentContext))
                    request.EnabledSources.Add(agent.context.DataSourceType.AgentContext);
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Agent 上下文块渲染失败 (降级: 不注入)");
        }
        
        return await _contextAssembler.AssembleAsync(request, ct);
    }
    
    /// <summary>
    /// R379 缓存前缀稳定化: 会话历史"全量正序回放"。
    /// · 不再倒序 Take(N) —— 窗口滑动会丢头部, 让 provider 的缓存前缀从丢弃点断裂;
    /// · 回放 SentContent (当初真正发出去的字节, 含本轮内联上下文), 保证逐字节一致;
    /// · OrderBy 用稳定排序 (LINQ OrderBy 稳定) 且不加随机 tie-breaker, 同刻消息保持追加序。
    /// 超预算的治理交给 PromptBuilder (整轮丢弃 + 打点), 不在此处静默截断。
    /// </summary>
    private async Task<List<Message>> GetConversationHistoryAsync(
        string sessionId,
        CancellationToken ct)
    {
        if (string.IsNullOrEmpty(sessionId))
            return new List<Message>();

        var session = await _sessionManager.GetSessionAsync(sessionId);
        if (session == null)
            return new List<Message>();

        return session.Messages
            .Where(m => m.Role != MessageRole.System)
            .OrderBy(m => m.Timestamp)
            .Select(m => new Message
            {
                Id = m.Id,
                SessionId = m.SessionId,
                SenderId = m.SenderId,
                Role = m.Role,
                Type = m.Type,
                Timestamp = m.Timestamp,
                Content = m.SentContent ?? m.Content,
            })
            .ToList();
    }
    
    private Task<string> RecognizeIntentAsync(string content, CancellationToken ct)
    {
        // 规则化意图识别 (v7.6): 词边界匹配消除子串误判 (sales→ls, category→cat 已修复)
        return Task.FromResult(IntentRecognizer.Recognize(content));
    }
    
    private async Task StoreToMemoryAsync(
        Message input,
        LLMResponse output,
        string intent,
        CancellationToken ct)
    {
        try
        {
            // 失败/空响应不进记忆 (空答案对后续检索是纯噪声)
            if (!output.Success || string.IsNullOrEmpty(output.Content))
            {
                _logger.LogDebug("Skip memory store: LLM response unsuccessful");
                return;
            }

            var entry = new VectorDocument
            {
                Content = $"Q: {input.Content}\nA: {output.Content}",
                Summary = output.Content.Length > 100
                    ? output.Content[..100] + "..."
                    : output.Content,
                Keywords = new List<string> { intent },
                Metadata = new Dictionary<string, object>
                {
                    { "intent", intent },
                    { "sessionId", input.SessionId ?? string.Empty },
                    { "memoryType", "Episodic" },
                    { "source", $"intent:{intent}" }
                }
            };

            await _vectorStore.StoreAsync(entry);

            // v0.11.0 R6 (召回率定量发现): 双存储割裂修复 — ContextAssembler.Memory 源读 IRAGRecall,
            // 只写 IVectorStore 导致召回率恒 0%。双写保证召回链路有数据。
            if (_ragRecall != null)
            {
                await _ragRecall.IndexAsync(new rag.RAGDocument
                {
                    Id = entry.Id,
                    Content = entry.Content,
                    Summary = entry.Summary,
                    // v0.11.0 R44 (真缺陷 27): Keywords 只传 {intent} → 查询 Jaccard 恒 0 (关键词分失活);
                    // 留空让 RAGRecall 自动 ExtractKeywords(内容) — 内容词 (如 rust) 才能与查询相交
                    Keywords = new List<string>(),
                    Metadata = entry.Metadata,
                    DocumentType = "conversation",
                });
                agent.config.AgentTelemetry.Emit("memory", "IndustrialAgentV2",
                    ("op", "store"), ("rag", true), ("len", entry.Content.Length));
            }
            else
            {
                agent.config.AgentTelemetry.Emit("memory", "IndustrialAgentV2",
                    ("op", "store"), ("rag", false), ("len", entry.Content.Length));
            }
        }
        catch (Exception ex)
        {
            // 记忆存储失败不应阻断对话主流程
            _logger.LogWarning(ex, "Failed to store interaction to memory");
        }
    }
    
    /// <summary>
    /// ✅ 将消息添加到会话（带消息数量限制）
    /// </summary>
    private async Task AddToSessionAsync(
        Message userMessage,
        LLMResponse llmResponse,
        CancellationToken ct)
    {
        try
        {
            if (string.IsNullOrEmpty(userMessage.SessionId))
                return;
            
            // 会话不存在时自动创建 (此前静默 return → 多轮对话历史永远为空)
            var session = await _sessionManager.GetOrCreateSessionAsync(
                userMessage.SessionId,
                string.IsNullOrEmpty(userMessage.SenderId) ? "anonymous" : userMessage.SenderId);
            
            // ✅ 限制消息数量，防止无限增长
            const int MaxMessages = 100;
            while (session.Messages.Count > MaxMessages)
            {
                // 移除最早的非关键消息（保留前几条）
                var toRemove = session.Messages
                    .Where(m => m.Role != MessageRole.System)
                    .OrderBy(m => m.Timestamp)
                    .Take(10)
                    .ToList();
                
                foreach (var msg in toRemove)
                {
                    session.Messages.Remove(msg);
                }
                
                _logger.LogDebug("Trimmed session {SessionId} messages, now {Count}", 
                    session.Id, session.Messages.Count);
            }
            
            // 添加用户消息
            session.Messages.Add(userMessage);
            
            // 仅在 LLM 成功时记录助手响应 (失败/空响应入历史会污染后续对话上下文)
            if (llmResponse.Success && !string.IsNullOrEmpty(llmResponse.Content))
            {
                session.Messages.Add(new Message
                {
                    Id = Guid.NewGuid().ToString(),
                    SessionId = session.Id,
                    SenderId = "assistant",
                    Role = MessageRole.Assistant,
                    Content = llmResponse.Content,
                    Type = MessageType.Text,
                    Timestamp = DateTime.UtcNow
                });
            }
            
            // 更新会话
            await _sessionManager.UpdateSessionAsync(session);
            
            _logger.LogDebug("Added messages to session {SessionId}, total {Count}", 
                session.Id, session.Messages.Count);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to add messages to session");
            // 不抛出异常，会话记录失败不应该影响主流程
        }
    }
    
    /// <summary>FNV-1a 32bit 内容摘要 (日志只记哈希不记全文 — L.3 凭据/长度约束)</summary>
    private static string FnvHash(string text)
    {
        uint hash = 2166136261;
        foreach (var ch in text)
        {
            hash ^= ch;
            hash *= 16777619;
        }
        return hash.ToString("x8", System.Globalization.CultureInfo.InvariantCulture);
    }

    private int EstimateTokens(string text)
    {
        if (string.IsNullOrEmpty(text)) return 0;
        
        var chineseChars = text.Count(c => c >= 0x4E00 && c <= 0x9FFF);
        var englishWords = text.Split(' ', StringSplitOptions.RemoveEmptyEntries).Length;
        
        return (int)(chineseChars * 1.5 + englishWords * 1.3);
    }
    
    #endregion
}

/// <summary>
/// LLM 调用器接口
/// </summary>
public interface ILLMCaller
{
    /// <summary>
    /// 调用 LLM
    /// </summary>
    Task<LLMResponse> CallAsync(Prompt prompt, CancellationToken ct = default);
}

/// <summary>
/// OpenAI chat completion 请求 DTO (AOT: source-gen 序列化, 禁匿名类型反射)
/// </summary>
public sealed class OpenAIChatRequest
{
    [JsonPropertyName("model")]
    public string Model { get; set; } = string.Empty;

    [JsonPropertyName("messages")]
    public List<OpenAIChatMessage> Messages { get; set; } = new();

    [JsonPropertyName("max_tokens")]
    public int MaxTokens { get; set; } = 2000;

    [JsonPropertyName("temperature")]
    public double Temperature { get; set; } = 0.7;

    /// <summary>v0.11.0 R21: glm 推理档位 (low=轻思考)。null=模型默认 (复杂任务保留深推理)。
    /// 实测: 简单题 compl 49tok vs 默认 8910ch reasoning; 复杂题 low 档 wall -55%。
    /// null 时 JSON 忽略 (LLMJsonContext 全局 WhenWritingNull)。</summary>
    [JsonPropertyName("reasoning_effort")]
    public string? ReasoningEffort { get; set; }
}

[JsonConverter(typeof(agent.ChatMessagePartsConverter))]
public sealed class OpenAIChatMessage
{
    [JsonPropertyName("role")]
    public string Role { get; set; } = string.Empty;

    [JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;

    /// <summary>
    /// v0.12.0 A2: 图像附件 (image_url/base64 data URL) — 非空时该消息序列化为 parts[] 多段形态
    /// (由 VisionJsonContext + OpenAIMultimodalMessage 承担, 本字段不直接序列化)。
    /// </summary>
    [JsonIgnore]
    public List<string>? ImageUrls { get; set; }

    [JsonIgnore]
    public bool HasImages => ImageUrls is { Count: > 0 };
}

/// <summary>
/// LLM 响应
/// </summary>
public class LLMResponse
{
    public string Content { get; set; } = string.Empty;
    public bool Success { get; set; } = true;
    public string? Error { get; set; }
    public string Model { get; set; } = "unknown";
    public int TokensUsed { get; set; }
    public double LatencyMs { get; set; }
    
    /// <summary>输入 Token 数</summary>
    public int PromptTokens { get; set; }
    
    /// <summary>输出 Token 数</summary>
    public int CompletionTokens { get; set; }
    
    /// <summary>完成原因（stop, length, content_filter, etc）</summary>
    public string? FinishReason { get; set; }

    /// <summary>v0.21.1: 推理模型思考链 (reasoning_content); 非推理模型为 null。</summary>
    public string? ReasoningContent { get; set; }

    /// <summary>R377: prompt 缓存命中 token (provider 未上报 → null)。</summary>
    public int? CacheHitTokens { get; set; }

    /// <summary>R377: prompt 缓存未命中 token (provider 未上报 → null)。</summary>
    public int? CacheMissTokens { get; set; }

    /// <summary>响应 ID</summary>
    public string? ResponseId { get; set; }
    
    /// <summary>时间戳</summary>
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
}

/// <summary>
/// OpenAI LLM 调用器示例
/// </summary>
public class OpenAILLMCaller : ILLMCaller
{
    private readonly HttpClient _httpClient;
    private readonly string _apiKey;
    private readonly string _model;
    
    private readonly string _baseUrl;

    public OpenAILLMCaller(
        HttpClient httpClient,
        string apiKey,
        string model = "gpt-4",
        string baseUrl = "https://api.openai.com/v1")
    {
        _httpClient = httpClient;
        _apiKey = apiKey;
        _model = model;
        _baseUrl = baseUrl.TrimEnd('/');
    }
    
    public async Task<LLMResponse> CallAsync(Prompt prompt, CancellationToken ct = default)
    {
        try
        {
            var messages = new List<OpenAIChatMessage>();
            
            // System
            if (!string.IsNullOrEmpty(prompt.SystemPrompt))
            {
                messages.Add(new OpenAIChatMessage { Role = "system", Content = prompt.SystemPrompt });
            }
            
            // Context as system context
            if (!string.IsNullOrEmpty(prompt.ContextPrompt))
            {
                var contextMessage = $"以下是你可以参考的相关上下文信息，请结合这些信息回答用户问题：\n\n{prompt.ContextPrompt}";
                messages.Add(new OpenAIChatMessage { Role = "system", Content = contextMessage });
            }
            
            // History
            foreach (var msg in prompt.History)
            {
                messages.Add(new OpenAIChatMessage
                {
                    Role = msg.Role == MessageRole.User ? "user" : "assistant",
                    Content = msg.Content
                });
            }
            
            // Current message
            // v0.12.0 A2: 图像附件 → user 消息多段 content (text + image_url × N)
            var userMsg = new OpenAIChatMessage { Role = "user", Content = prompt.UserMessage };
            if (prompt.ImageUrls.Count > 0)
            {
                userMsg.ImageUrls = prompt.ImageUrls
                    .Select(u => u.StartsWith("data:") || u.StartsWith("http", StringComparison.OrdinalIgnoreCase)
                        ? u
                        : VisionChatHelper.ToDataUrl(u))
                    .ToList();
            }
            messages.Add(userMsg);
            
            // v0.11.0 R21: 显式 DTO (source-gen 零反射) + 推理档位 (简单任务 low 档轻思考)
            var requestBody = new OpenAIChatRequest
            {
                Model = _model,
                Messages = messages,
                // v0.11.0 R19 修复: reasoning 模型 (glm/deepseek) 的思维链计入 max_tokens,
                // 2000 曾被 reasoning 吃满 → content 空回复 (C03 实测 2000 tok 全 reasoning)。
                // 上限只是截断保护, 实际输出长度由 System Prompt 输出纪律约束。
                MaxTokens = 8192,
                Temperature = 0.7,
                ReasoningEffort = prompt.ReasoningEffort,
            };
            
            // v0.12.0 A2: 任一消息带图 → 多段形态序列化 (VisionJsonContext, 手写 converter AOT 安全)
            string jsonBody;
            if (messages.Any(m => m.HasImages))
            {
                jsonBody = JsonSerializer.Serialize(requestBody, VisionJsonContext.Default.OpenAIChatRequest);
            }
            else
            {
                jsonBody = JsonSerializer.Serialize(requestBody, LLMJsonContext.Default.OpenAIChatRequest);
            }
            var request = new HttpRequestMessage(HttpMethod.Post, _baseUrl + "/chat/completions");
            request.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", _apiKey);
            request.Content = new StringContent(jsonBody, Encoding.UTF8, "application/json");
            
            var httpResponse = await _httpClient.SendAsync(request, ct);
            var responseJson = await httpResponse.Content.ReadAsStringAsync(ct);
            
            if (!httpResponse.IsSuccessStatusCode)
            {
                return new LLMResponse
                {
                    Success = false,
                    Error = $"API Error: {httpResponse.StatusCode} - {responseJson}"
                };
            }
            
            using var doc = System.Text.Json.JsonDocument.Parse(responseJson);
            var content = doc.RootElement
                .GetProperty("choices")[0]
                .GetProperty("message")
                .GetProperty("content")
                .GetString() ?? "";
            
            var usage = doc.RootElement.GetProperty("usage");
            
            // 提取额外字段
            var responseId = doc.RootElement.TryGetProperty("id", out var idProp) ? idProp.GetString() : null;
            var finishReason = doc.RootElement.TryGetProperty("choices", out var choices) && 
                              choices.GetArrayLength() > 0 &&
                              choices[0].TryGetProperty("finish_reason", out var fr) ? fr.GetString() : null;
            
            return new LLMResponse
            {
                Content = content,
                Success = true,
                Model = _model,
                TokensUsed = usage.TryGetProperty("total_tokens", out var total) ? total.GetInt32() : 0,
                PromptTokens = usage.TryGetProperty("prompt_tokens", out var pt) ? pt.GetInt32() : 0,
                CacheHitTokens = usage.TryGetProperty("prompt_cache_hit_tokens", out var ch) ? ch.GetInt32() : null,
                CacheMissTokens = usage.TryGetProperty("prompt_cache_miss_tokens", out var cm) ? cm.GetInt32() : null,
                CompletionTokens = usage.TryGetProperty("completion_tokens", out var completion) ? completion.GetInt32() : 0,
                ResponseId = responseId,
                FinishReason = finishReason,
                Timestamp = DateTime.UtcNow
            };
        }
        catch (Exception ex)
        {
            return new LLMResponse
            {
                Success = false,
                Error = ex.Message
            };
        }
    }
}

/// <summary>
/// 空 LLM 调用器（未配置 API Key 时的 fallback）
/// 返回明确的提示而不是抛异常，保证 DI 图完整、程序可启动
/// </summary>
public class NullLLMCaller : ILLMCaller
{
    public Task<LLMResponse> CallAsync(Prompt prompt, CancellationToken ct = default)
    {
        var response = new LLMResponse
        {
            Success = false,
            Content = string.Empty,
            Error = "LLM 未配置: 请设置环境变量 AGENT_OPENAI_KEY (或在 config/base/core.yaml 的 openai.api_key_env 指定变量名) 后重启。",
            Model = "none",
            TokensUsed = 0,
            LatencyMs = 0,
            Timestamp = DateTime.UtcNow
        };
        return Task.FromResult(response);
    }
}
