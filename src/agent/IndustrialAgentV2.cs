using Microsoft.Extensions.Logging;
using agent.core;
using agent.workspace;
using agent.codegen;
using agent.recovery;
using agent.vectormemory;
using agent.memory;
using agent.templates;
using agent.search;
using agent.session;
using agent.context;
using agent.rag;
using agent.tendency;
using agent.tokencompression;
using agent.registry;

using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text;

using agent.intent;
using agent.userinteraction;

namespace agent;

public partial class IndustrialAgentV2 : AgentBase
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

    /// <summary>R466 优先级开关 —— **默认开** (生产行为: 复述回放优先于承接反问); 置 "0"
    /// 复原 R465 行为 (承接反问覆盖回放), 供**同一二进制**上的单变量负控 (判据必须绑机制)。</summary>
    private static readonly bool ContinuationRepeatPriorityOn =
        Environment.GetEnvironmentVariable("AGENTFRAMEWORK_CONTINUATION_REPEAT_PRIORITY") != "0";

    /// <summary>R458 承接轮: 本轮注入的真实产物事实 (非承接轮恒为 null)。</summary>
    private IReadOnlyList<agent.context.ArtifactFact>? _continuationFacts;

    /// <summary>R466: 本轮**本地确定结算**的类别 (与 skip 层打点同源; null = 本轮未经本地结算)。
    /// 只由前置门 Skip 支写入 ⇒ "为什么这轮不走远端" 在收口面可复查。</summary>
    private string? _localSettleKind;
    // R478: 本轮回复的因果绑定 (llmResponse 在 try 作用域内 ⇒ 出域前捕获到字段, 供 loop_turn 打点)
    private string _replyRequestId = "";
    private string _replyFinishReason = "";
    private bool _replyEmptyBody;

    /// <summary>R458 承接轮: 本轮用户原话 (兜底反问里引用)。</summary>
    private string? _continuationUserText;

    /// <summary>R460: 本轮扫描到的产物**总项数** (菜单「汇总现有 N 项」用; 与块内截断标注同源)。</summary>
    private int _continuationTotal;
    private readonly ICodeGenerator _codeGenerator;
    private readonly agent.registry.AgentRegistry _agentRegistry;
    private readonly agent.registry.ResponseSegmentRouter _segmentRouter;
    private readonly agent.registry.ClarificationService _clarificationService;
    private readonly agent.core.IUserPromptService? _promptService; // v7.14: EvidenceGate→批量问询驱动 (null=静默跳过)
    private readonly string _dataStoragePath;
    private readonly IRecoverySystem _recoverySystem;
    private readonly IVectorStore _vectorStore;
    private readonly IRAGRecall? _ragRecall;
    private readonly agent.contextgradient.ITextEmbedder? _textEmbedder;
    private readonly string _instanceId = Guid.NewGuid().ToString("N")[..8];
    private agent.exploration.ThinkMemory? _thinkMemory;
    /// <summary>v0.13.3 R275: 联想库为**进程级**单例 (V2 实例可能每轮重建 — host 生命周期语义), 跨轮保留。
    private static readonly agent.exploration.ThinkMemory _thinkMemoryGlobal = LoadThinkMemory();

    /// <summary>R444: 门前置消融开关 —— **默认开** (Ack 前置 = 生产行为); 置 "0" 复原 R443 的
    /// 后置否决行为, 供同网格单变量对照 (默认值即被测行为, 开关只用于消融)。</summary>
    private static readonly bool GatePrefilterOn =
        Environment.GetEnvironmentVariable("AGENTFRAMEWORK_GATE_PREFILTER") != "0";

    /// <summary>R465: 纯复述族直 Skip —— **默认开** (生产行为); 置 "off" 复原 R464 行为,
    /// 供同网格单变量对照 (开关只用于消融, 默认值即被测行为)。</summary>
    private static readonly bool GateRepeatSkipOn =
        Environment.GetEnvironmentVariable("AGENTFRAMEWORK_GATE_REPEAT_SKIP") != "off";

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
        [];
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

    /// <summary>R365/R426: 纠正检测微 prompt 的系统行 — 远端与本地**同一输入面** (不许两套提示)。</summary>
    private const string CorrectionJudgeSystem = "只输出一个字母。";

    /// <summary>R365: 纠正检测微 prompt 通道 (走模型队列; ~140 tok/次)。</summary>
    private async Task<(string Content, int TokensUsed)> DetectViaLlm(string prompt, int maxTokens)
    {
        var resp = await _modelRouter!.CallAsync(new agent.modelqueue.QueuePrompt
        {
            SystemPrompt = CorrectionJudgeSystem,
            UserMessage = prompt,
            EstimatedTokens = prompt.Length / 2,
        }, agent.modelqueue.TaskKindHint.ContextCompression, "general", CancellationToken.None);
        return (resp.Success ? resp.Content : "", prompt.Length / 2 + resp.Content.Length / 2);
    }

    /// <summary>R414: 失败轮的可见正文裁定 —— 只有被上游标记为"面向用户"的文案才透出, 其余失败一律空白。
    /// 该函数是"失败必须可见 vs 内部信息不得外泄"两难的单一裁定点 (源级回归钉死见 UserFacingFailureTests)。</summary>
    internal static string UserFacingFailureContent(LLMResponse llmResponse)
        => llmResponse.ContentIsUserFacing ? (llmResponse.Content ?? string.Empty) : string.Empty;

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
        var skipped = 0;
        foreach (var st in subTasks)
        {
            var mq = new agent.exploration.MicroQuestion
            {
                Question = st.Text ?? string.Empty,
                ForwardRefs = new List<string>(),
                InjectedContext = string.Empty,
            };
            // R485 微问询形态分流: 隔离通道无前文 ⇒ 回指不可解, 命中即**预发送**拦截 (省一次必然无效的远端调用)。
            // 拦截不打 answer/正文, 只落 (reason, marker, len) 供审计; 被拦截者不产生回注摘要。
            var isoGate = agent.exploration.MicroStepIsolationGate.Decide(st.Text);
            if (!isoGate.Send)
            {
                skipped++;
                agent.config.AgentTelemetry.Emit("micro_step_skipped", "IndustrialAgentV2",
                    ("id", mq.Id), ("reason", isoGate.Reason), ("marker", isoGate.Marker),
                    ("len", (st.Text ?? string.Empty).Length));
                continue;
            }
            var sw = System.Diagnostics.Stopwatch.StartNew();
            string answer;
            try
            {
                var microPrompt = new Prompt
                {
                    UserMessage = $"[微步骤隔离问询] {mq.Question}\n(只回答本微问题, 不引申)",
                    SystemPrompt = "你是隔离执行的微步骤助手: 只回答给出的微问题本身, 不引用任何外部会话历史。",
                    EstimatedTokens = 100,
                    // R494: 隔离通道**结构标记** —— 隔离通道没有工作区 (上下文为空, system 明示不引用外部会话),
                    // 却因意图键为空而被 R490 意图轴的"未知意图保守下发"分支宣告了 4 个工作区工具:
                    // R493 真机 B 臂 4/9 空正文调用全部来自本通道 (上游对幻觉路径 `d data` 反复 list/read,
                    // 4 轮全为工具往返, 7,305 tok / 该臂 7.22%)。此处置位后由声明面通道轴收口。
                    IsolatedChannel = true,
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
            ("count", subTasks.Count), ("failures", session.ConsecutiveFailures), ("skipped", skipped));
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
        agent.core.IUserPromptService? promptService = null,
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
            var key = roleMasterKey ?? CredentialEncryption.LoadOrCreateMasterKey("data");
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
        // R449 验收补 (2026-09-15): think-memory 档位必须**在遥测面可机检** —— 计划 §4 机检② 预注册了
        // `think_memory_boot` 必带 enabled/mode/loaded 字段, 但首版只发了 embedder_injected/available/instance
        // ⇒ 开关只改行为、不可观测 ⇒ 消融 C5(各档打点形状互不相同) 无法机检。此处按预注册补齐 (加性, 不改旧字段):
        //   mode    = on|off|recall0|write0  (进程级档位实读值, 非手抄)
        //   enabled = mode != "off"          (off 档三闸全关)
        //   loaded  = 进程内累计入库条数      (反空心: on 档 0 ⇒ 库没读到, 与 off 档可区分)
        // 读数纪律: 缺任一字段 ⇒ 该轮「开关生效」结论记 n/a, 不得以「没打点」冒充「档位无效」。
        agent.config.AgentTelemetry.Emit("think_memory_boot", "IndustrialAgentV2",
            ("embedder_injected", textEmbedder is not null),
            ("available", textEmbedder is { IsAvailable: true }),
            ("instance", Guid.NewGuid().ToString("N")[..8]),
            ("mode", _thinkMemory?.ModeName ?? "unknown"),
            ("enabled", !string.Equals(_thinkMemory?.ModeName, "off", StringComparison.Ordinal)),
            ("loaded", agent.exploration.ThinkMemoryStats.Snapshot().Loaded),
            ("records", _thinkMemory?.Count ?? -1));
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
        _capabilities.AddRange(Array.Empty<string>());
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
        [];
        if (taskMarkersPre.Any(m => content.Contains(m, StringComparison.Ordinal)))
            return true;
        string[] memoryMarkers = [];
        if (memoryMarkers.Any(m => content.Contains(m, StringComparison.Ordinal)))
            return false;
        string[] taskMarkers =
        [];
        return taskMarkers.Any(m => content.Contains(m, StringComparison.Ordinal));
    }

    protected override async Task<AgentResponse> OnProcessAsync(Message message, CancellationToken ct)
    {
        // R527 候选②: 有界抽取 —— 轮起始清零 + 活动心跳 (原位同序搬出, 行为等价; 夹具 eval/rover/r527/equiv_local_commands.py)
        var startTime = BeginTurn(message);
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
                // v0.22.0 L2-待办① (R420): /recall <查询> [topK] — 跨会话检索接线
                // (SessionHistorySearch 自 R370 交付后生产 0 消费 = L7-G1 缺口; 本轮回接本地指令出口, 零 LLM)
                if (localCommand.Command == "recall")
                {
                    response.Success = true;
                    try
                    {
                        var recallArg = (localCommand.Argument ?? string.Empty).Trim();
                        if (recallArg.Length == 0)
                        {
                            response.Content = "用法: /recall <查询词> [topK]  (检索面 = 已落盘会话记忆摘要; 零 LLM 调用)";
                        }
                        else
                        {
                            var q = recallArg;
                            var topK = 5;
                            var lastSpace = recallArg.LastIndexOf(' ');
                            if (lastSpace > 0 &&
                                int.TryParse(recallArg[(lastSpace + 1)..], System.Globalization.NumberStyles.None,
                                    System.Globalization.CultureInfo.InvariantCulture, out var k) && k > 0 && k <= 50)
                            {
                                topK = k;
                                q = recallArg[..lastSpace].Trim();
                            }
                            var recallSearch = new agent.session.SessionHistorySearch(
                                new agent.session.SessionHistorySearch.StoreSource(_sessionMemoryStore));
                            var hits = recallSearch.Search(q, topK);
                            response.Content = agent.session.SessionHistorySearch.Render(hits, q, topK);
                            // 通道级打点 (行为类 KPI 不用文本启发式): hits=0 也如实记账
                            agent.config.AgentTelemetry.Emit("recall_query", "IndustrialAgentV2",
                                ("query_len", q.Length), ("topk", topK), ("hits", hits.Count));
                        }
                    }
                    catch (Exception ex) { response.Content = $"跨会话检索失败: {ex.Message}"; }
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
                var warningMarkers = Array.Empty<string>();
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
                    // R524 (用户 2026-09-17 定向「常量/可缓存内容作稳定前缀前置」+「user 轮只留题面」):
                    //   技能知识参考 = 同任务族的**逐字节常量** (真机实测 4,171 字符, 跨窗口/跨臂不变) ⇒ 焊进常量前缀,
                    //   此后每轮命中缓存; 不再内联进 user 轮 (原 R326-f 假设它"每轮变化" —— 实测不成立)。
                    var skillConst = _pendingSkillKnowledge.Length > 0
                        ? "\n[技能知识参考]\n" + _pendingSkillKnowledge : string.Empty;
                    var initial = systemPrompt + "\n\n" + baseline
                                  + (staticText.Length > 0 ? "\n[会话静态上下文]\n" + staticText : string.Empty)
                                  + skillConst;
                    if (skillConst.Length > 0) _pendingSkillKnowledge = string.Empty;
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

            // R458 承接轮人性化 (用户令: 「突然说一句"继续"，另一个人肯定反问"继续什么"」):
            // 判据复用意图层既有分支 (WeakIntent/TooVague 且无更具体缺口), 命中则把**工作区真实产物**
            // 逐项接地后反问。块只进本轮 user 内容 ⇒ 缓存前缀字节不变; 事实全来自磁盘扫描 ⇒ 零编造。
            if (agent.context.ContinuationBrief.IsContinuationTurn(subTasks))
            {
                _continuationUserText = message.Content;
                _continuationFacts = agent.context.ContinuationBrief.ScanArtifacts(
                    _workspace is { RootPath: { Length: > 0 } root } ? root : Environment.CurrentDirectory,
                    agent.context.ContinuationBrief.MaxArtifacts, out var artTotal);
                _continuationTotal = artTotal;
                var brief = agent.context.ContinuationBrief.BuildBlock(_continuationFacts, artTotal);
                inlineBlocks.Add(brief);
                agent.config.AgentTelemetry.Emit("continuation_brief", "IndustrialAgentV2",
                    ("artifacts", _continuationFacts.Count), ("total", artTotal), ("chars", brief.Length),
                    ("state", _continuationFacts.Count > 0 ? "grounded" : "empty"));
            }
            else
            {
                _continuationUserText = null;
                _continuationFacts = null;
                _continuationTotal = 0;
            }

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
            string? gateRoleSeed = null;   // R430: 门判实际使用的角色种子 (仅「询问 r1」的分支才非空)
            string? gateGrowthBlock = null; // R431: 门判实际挂载的 role 额外数据 (成长经历; 空=未挂载)
            if (System.Threading.Interlocked.Exchange(ref _gateConfigEmitted, 1) == 0)
            {
                agent.config.AgentTelemetry.Emit("local_turn_gate_config", "IndustrialAgentV2",
                    ("router_present", (_modelRouter is not null).ToString()),
                    ("turn_gate_enabled", (_modelRouter?.TurnGateEnabled ?? false).ToString()),
                    ("local_channel_ready", (_modelRouter?.LocalChannelReady ?? false).ToString()),
                    // R431: 挂载前置条件 (域 = 0 ⇒ 成长块恒空 ⇒ 挂载与不挂载逐位同一; -1 = 无 role/未建账本)
                    ("role_growth_domains", (GrowthLedger?.DomainCount ?? -1).ToString()),
                    // R465: 复述族直 Skip 开关状态 (默认 on; 消融臂须可见, 否则「省了没省」不可归因)
                    ("repeat_skip", GateRepeatSkipOn ? "on" : "off"),
                    ("role", ActiveRole?.Id ?? "(null)"));
            }
            // R475: 复述轮回放候选 —— 在门控块内确定 (必须先于 local_turn_gate 打点),
            // 供块外的 Skip 执行支复用 (两处各自取历史会漂移, R466 单源教训)。
            var repeatTurnFlag = false;
            string? repeatPrevReply = null;
            // R498 候选③ (R413 主线): 同义改写族 —— 与复述族**互斥** (IsPureParaphrase 内含 ¬IsPureRepeat),
            // 故两者不会同时为真, 历史只取一次。本地消化 = 用 r1 改写上一条实质答复, 过守卫否则降级远端。
            var paraphraseTurnFlag = false;
            // 改写成功 ⇒ 结算类选 SettleLocalParaphrase; 答复正文**复用** repeatPrevReply 单一载体 (A4 门禁)。
            var localRewriteIsParaphrase = false;
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
                // R444: **廉价必要条件前置** —— 不变量「r1 的 Skip 只在 MechanicalAck 成立时生效」
                // (见下方后置否决) 蕴含 Skip ⇒ Ack; 其逆否 ¬Ack ⇒ 无论 r1 判什么都终局 Pass。
                // 故对 ¬Ack 轮直接 Pass: 不建 prompt、不问 r1 ⇒ 省掉该轮本地 r1 成本 (R443 真值口径
                // ≈ 638.8 tok/轮), 而判决/远端走向/内联块/落盘内容与后置否决路径**逐位等价**。
                // 依据: eval/rover/r444/precheck-prefilter.json (8 运行 99 门行, Skip⇒Ack 反例 0)。
                else if (GatePrefilterOn && GateRepeatSkipOn && agent.modelqueue.TurnGateJudge.IsPureRepeat(message.Content))
                {
                    // R465: 纯复述族 (只要求把上一条答复原样重来, 无新诉求) ⇒ 前置门直接 Skip。
                    // 本地消化 = **回放上一条答复原文** (见下 Skip 支), 零 r1、零远端调用、零 token。
                    // 安全性靠上面 MechanicalPass 优先 + IsPureRepeat 的字符白名单 (任何内容字/问号 ⇒ 不吸收)。
                    _modelRouter.TurnGate.RecordMechanicalRepeat();
                    gateOutcome = agent.modelqueue.TurnGateOutcome.Decide(
                        agent.modelqueue.TurnGateVerdict.Skip, "mechanical:repeat");
                }
                // R498 候选③ (R413 主线补口): 同义改写族 (「换个说法」「用别的方式说一遍」) ⇒ 前置门 Skip,
                // 本地消化 = 用 r1 **改写**上一条实质答复 (内容承载的本地生成, 非回放非模板)。
                // 位置纪律: 必须在复述族**之后** (互斥, 复述优先)、在 ¬Ack 前置**之前** —— 与 R465 同序,
                // 否则改写族会被 else-if 链吞掉 ⇒ 静默不生效 (「接线了但没生效」是本仓反复踩过的坑)。
                // 闸默认关 (LocalParaphraseChannel.IsEnabled() == false) ⇒ 全链逐位不变。
                else if (GatePrefilterOn && agent.modelqueue.LocalParaphraseChannel.ShouldAbsorb(
                             message.Content, agent.modelqueue.LocalParaphraseChannel.IsEnabled()))
                {
                    _modelRouter.TurnGate.RecordMechanicalParaphrase();
                    gateOutcome = agent.modelqueue.TurnGateOutcome.Decide(
                        agent.modelqueue.TurnGateVerdict.Skip, "mechanical:paraphrase");
                }
                else if (GatePrefilterOn && !agent.modelqueue.TurnGateJudge.MechanicalAck(message.Content))
                {
                    _modelRouter.TurnGate.RecordMechanicalNonAck();
                    gateOutcome = agent.modelqueue.TurnGateOutcome.Decide(
                        agent.modelqueue.TurnGateVerdict.Pass, "mechanical:nonack");
                }
                else
                {
                    gateRoleSeed = ActiveRole.Id + "|" + agent.modelqueue.TurnGateJudge.Clip(ActiveRole.ProfileSeed, 80);
                    // R431: role 额外数据 (成长经历) 有界挂载 —— 管道早就支持 (BuildPrompt 内二次 clip 300),
                    // 但调用点一直传 null; R431 前置机检: 真机臂 role 的 growth 域 = 0 ⇒ 挂载与不挂载在
                    // 当前真实负载上逐位同一 (所以此前的「已挂载」是不可能被读数区分的空操作)。
                    // 有界性: RenderForPrompt ≤400 → BuildPrompt clip ≤300 ⇒ 不可能挤爆生成预算 (R413 教训)。
                    gateGrowthBlock = GrowthLedger?.RenderForPrompt();
                    gateOutcome = await _modelRouter.JudgeTurnAsync(
                        message.Content, gateRoleSeed, gateGrowthBlock, ct).ConfigureAwait(false);
                }
                // R434 双条件: r1 的 Skip 只在**结构确认为「认可族」**时生效。真机实测根因: 残余带内
                // r1 对「再讲一遍。」「讲细一点。」「从头再说。」这类短促真诉求误判 Skip ⇒ 3/4 真诉求轮
                // 被跳成空话 (质量硬线失守)。非认可族 ⇒ 降级 Pass ⇒ 照常走远端 (宁可多走一次远端)。
                // 位置纪律: 必须在下面 local_turn_gate 打点**之前** —— 否则遥测 basis 会写 r1 的原始
                // 判决 (skip→local), 与被测行为的真实走向相反 (R433 同类: 读数不得自报假形态)。
                // R501: 改写族豁免 —— 与 r1 的误判 Skip **同形但不同源**: 改写族是**前置门自己**在 1607 支作的
                // Skip 决策 (basis=mechanical:paraphrase)。R500 真机 3/3 实证: 不豁免 ⇒ 吸收后立即被本支改写成
                // Pass("gate:skip_rejected_nonack") ⇒ 通道成死代码 (遥测特征 r1_raw_len == len("mechanical:paraphrase") == 21,
                // 且同时落 gate_prefilter_invariant_violation)。豁免条件用**同一判据**(ShouldAbsorb ∧ IsEnabled),
                // 闸关时 IsEnabled()==false ⇒ 逐位不变 (R466 单变量纪律)。
                if (gateOutcome.Decided && gateOutcome.Verdict == agent.modelqueue.TurnGateVerdict.Skip
                    && !agent.modelqueue.TurnGateJudge.MechanicalAck(message.Content)
                    && !agent.modelqueue.TurnGateJudge.IsPureRepeat(message.Content)
                    && !agent.modelqueue.LocalParaphraseChannel.ShouldAbsorb(
                           message.Content, agent.modelqueue.LocalParaphraseChannel.IsEnabled()))
                {
                    // R444: 前置门开启时本支**不可达** (¬Ack 已在调用前 Pass) ⇒ 命中 = 不变量被破坏。
                    // 必须 fail-closed 落盘 (静默降级 = 读数与真实走向相反, R433 教训)。
                    if (GatePrefilterOn)
                    {
                        _modelRouter!.TurnGate.RecordPrefilterViolation();
                        agent.config.AgentTelemetry.Emit("gate_prefilter_invariant_violation", "IndustrialAgentV2",
                            ("msg_sha16", agent.modelqueue.LocalInputFingerprint.Sha16(message.Content)),
                            ("msg_len", message.Content.Length.ToString()),
                            ("r1_raw_len", gateOutcome.Raw.Length.ToString()));
                    }
                    _modelRouter!.TurnGate.RecordSkipRejected();
                    agent.config.AgentTelemetry.Emit("local_turn_gate_reject", "IndustrialAgentV2",
                        ("reason", "skip_not_ack_family"),
                        ("msg_sha16", agent.modelqueue.LocalInputFingerprint.Sha16(message.Content)),
                        ("msg_len", message.Content.Length.ToString()),
                        ("r1_raw_len", gateOutcome.Raw.Length.ToString()));
                    gateOutcome = agent.modelqueue.TurnGateOutcome.Decide(
                        agent.modelqueue.TurnGateVerdict.Pass, "gate:skip_rejected_nonack");
                }
                // R475: 纯复述族 = **明确指代** (「再讲一遍。」) ⇒ 本地消化 (回放上一条答复原文) 只在
                // **存在可回放的实质答复**时成立。取不到 (空/模板/空正文徽标) ⇒ 撤销 Skip 降级远端 ——
                // 不得以模板冒充答复 (R474 真端点实测: R 臂 12 轮 6 轮模板 + 3 轮用户可见横幅, 实质回答仅 3/12,
                // 同轮 Arole 12/12 全实质)。判据单源: 用户轮 IsPureRepeat + Assistant 侧 IsReplayableReply。
                repeatTurnFlag = gateOutcome.Decided
                    && gateOutcome.Verdict == agent.modelqueue.TurnGateVerdict.Skip
                    && agent.modelqueue.TurnGateJudge.IsPureRepeat(message.Content);
                // R498 候选③: 同义改写族 = **本地生成** (需源 + 需过守卫) ⇒ 与复述族同形地在此定终局。
                // 两族互斥 (IsPureParaphrase 内含 ¬IsPureRepeat) ⇒ **历史只取一次** (R466/R475 单源纪律;
                // A4 门禁: 本文件里带消息会话的那次历史读取至多两处)。
                paraphraseTurnFlag = gateOutcome.Decided
                    && gateOutcome.Verdict == agent.modelqueue.TurnGateVerdict.Skip
                    && agent.modelqueue.LocalParaphraseChannel.ShouldAbsorb(
                        message.Content, agent.modelqueue.LocalParaphraseChannel.IsEnabled());
                if (repeatTurnFlag || paraphraseTurnFlag)
                {
                    var hist0 = await GetConversationHistoryAsync(message.SessionId, ct).ConfigureAwait(false);
                    for (var hi = hist0.Count - 1; hi >= 0; hi--)
                    {
                        var h0 = hist0[hi];
                        if (h0.Role != MessageRole.Assistant) continue;
                        if (!agent.modelqueue.ModelQueueRouter.IsReplayableReply(h0.Content)) continue;
                        repeatPrevReply = h0.Content;
                        break;
                    }
                    if (repeatPrevReply is null)
                    {
                        if (repeatTurnFlag)
                        {
                            _modelRouter!.TurnGate.RecordRepeatDegrade();
                            agent.config.AgentTelemetry.Emit("repeat_degrade_remote", "IndustrialAgentV2",
                                ("msg_sha16", agent.modelqueue.LocalInputFingerprint.Sha16(message.Content)),
                                ("msg_len", message.Content.Length.ToString()),
                                ("reason", "no_replayable_prev"));
                            // RF0002 §2.2 评分回执: 形状命中却仍需远端 ⇒ 该形状无用 ⇒ 剔除 (用户令「没用就扔掉」)。
                            agent.nlp.NlpGate.ReportOutcome(message.Content, agent.nlp.NlpGate.FaceRepeat, useful: false);
                            gateOutcome = agent.modelqueue.TurnGateOutcome.Decide(
                                agent.modelqueue.TurnGateVerdict.Pass, "gate:repeat_no_replayable_prev");
                        }
                        else
                        {
                            _modelRouter!.TurnGate.RecordParaphraseDegrade();
                            agent.config.AgentTelemetry.Emit("paraphrase_degrade_remote", "IndustrialAgentV2",
                                ("msg_sha16", agent.modelqueue.LocalInputFingerprint.Sha16(message.Content)),
                                ("msg_len", message.Content.Length.ToString()),
                                ("reason", "no_replayable_prev"));
                            // RF0002 §2.2 评分回执: 形状命中却仍需远端 ⇒ 该形状无用 ⇒ 剔除。
                            agent.nlp.NlpGate.ReportOutcome(message.Content, agent.nlp.NlpGate.FaceParaphrase, useful: false);
                            gateOutcome = agent.modelqueue.TurnGateOutcome.Decide(
                                agent.modelqueue.TurnGateVerdict.Pass, "gate:paraphrase_no_replayable_prev");
                        }
                    }
                    else if (paraphraseTurnFlag)
                    {
                        // 改写 = 用 r1 把上一条实质答复**换一种说法**生成, 过守卫才成立; 守卫破一条即拒。
                        var rewritten = await _modelRouter!.TryComposeLocalParaphraseAsync(repeatPrevReply, ct).ConfigureAwait(false);
                        if (rewritten is null)
                        {
                            // 守卫拒收原因必须落遥测 —— 否则「接了改写通道」与「通道恒被拒」在读数上不可分。
                            _modelRouter.TurnGate.RecordParaphraseDegrade();
                            agent.config.AgentTelemetry.Emit("paraphrase_degrade_remote", "IndustrialAgentV2",
                                ("msg_sha16", agent.modelqueue.LocalInputFingerprint.Sha16(message.Content)),
                                ("msg_len", message.Content.Length.ToString()),
                                ("reason", _modelRouter.LocalParaphrase.LastRejectReason ?? "engine_degrade"),
                                ("src_len", repeatPrevReply.Length.ToString()));
                            // RF0002 §2.2 评分回执: 形状命中却仍需远端 (本地改写被守卫拒) ⇒ 该形状无用 ⇒ 剔除。
                            agent.nlp.NlpGate.ReportOutcome(message.Content, agent.nlp.NlpGate.FaceParaphrase, useful: false);
                            gateOutcome = agent.modelqueue.TurnGateOutcome.Decide(
                                agent.modelqueue.TurnGateVerdict.Pass, "gate:paraphrase_guard_rejected");
                            repeatPrevReply = null;
                        }
                        else
                        {
                            localRewriteIsParaphrase = true;   // 结算类选择 (SettleLocalParaphrase)
                            repeatPrevReply = rewritten;        // **单源载体**: 执行支只读这一个变量 (A4 门禁)
                        }
                    }
                }
                // R444: 本轮是否真的走过本地 r1 (机械判定轮 = 未走) —— 决定真值字段是 -1 还是实测值。
                var gateLocalCall = !(_modelRouter.TurnGate.LastBasis ?? "").StartsWith("mechanical", System.StringComparison.Ordinal);
                agent.config.AgentTelemetry.Emit("local_turn_gate", "IndustrialAgentV2",
                    ("decided", gateOutcome.Decided ? "true" : "false"),
                    ("verdict", gateOutcome.Verdict.ToString()),
                    ("basis", _modelRouter.TurnGate.LastBasis ?? ""),
                    ("raw", gateOutcome.Raw.Length > 120 ? gateOutcome.Raw[..120] : gateOutcome.Raw),
                    ("raw_len", gateOutcome.Raw.Length.ToString()),
                    ("error", gateOutcome.Error ?? ""),
                    // R429: 决策路径缓存钉死可观测 —— cache_n 应恒为 0 (关前缀缓存), pinned = 累计钉死次数
                    ("cache_n", (gateLocalCall ? _modelRouter.TurnGate.LastCachedTokens : -1).ToString()),
                    ("pinned", _modelRouter.TurnGate.CachePinned.ToString()),
                    // R430: 判定输入指纹 (只观测) — 逐轮 raw 不同时, 先机械区分「输入不同」与「引擎不确定」
                    ("prompt_sha", _modelRouter.TurnGate.LastPromptSha ?? ""),
                    ("request_sha", _modelRouter.TurnGate.LastRequestSha ?? ""),
                    ("req_fields", _modelRouter.TurnGate.LastRequestFields ?? ""),
                    ("role_seed_sha", _modelRouter.TurnGate.LastRoleSeedSha ?? ""),
                    // R431: 挂载形状 (取自实发 prompt, 非二次重建) — 「role 额外数据挂没挂」必须可机检:
                    // 未挂载臂 growth_chars == 0 ∧ prompt_len == 冻结基线, 挂载臂 growth_chars > 0。
                    ("gate_prompt_len", (gateLocalCall ? _modelRouter.TurnGate.LastPromptChars : -1).ToString()),
                    ("role_seed_chars", _modelRouter.TurnGate.LastRoleSeedChars.ToString()),
                    ("growth_chars", _modelRouter.TurnGate.LastGrowthChars.ToString()),
                    ("growth_lines", _modelRouter.TurnGate.LastGrowthLines.ToString()),
                    // R443: 本地 r1 成本的 **tokenizer 真值** (llama-server 上报; -1 = 该轮未走 r1)。
                    // 口径: tokens_evaluated = prompt 总长, prompt_new = 新评估, gen = 生成长度。
                    // R444 修: 契约「-1 = 该轮未走 r1」必须**逐轮**成立 —— 机械判定轮 (mechanical:pass /
                    // mechanical:nonack) 既未建 prompt 也未问 r1, 若直接读 LastXxx 会继承**上次调用的粘滞值**
                    // ⇒ 前置门臂的本地成本被虚增 (实测 M20: 6 行 × (319+78) = 2382 tok, 把 33.31% 压成 29.43%)。
                    ("tokens_evaluated", (gateLocalCall ? _modelRouter.TurnGate.LastEvalTokens : -1).ToString()),
                    ("prompt_new", (gateLocalCall ? _modelRouter.TurnGate.LastNewTokens : -1).ToString()),
                    ("gen_tokens", (gateLocalCall ? _modelRouter.TurnGate.LastGenTokens : -1).ToString()),
                    // R444: 前置门形状 (可机检) — prefilter=1 且 basis=mechanical:nonack→remote 的轮
                    // 就是「本来会花一次 r1、现在零成本」的轮; 不变量破坏数必须恒 0。
                    ("prefilter", GatePrefilterOn ? "1" : "0"),
                    ("prefilter_nonack", _modelRouter.TurnGate.MechanicalNonAcks.ToString()),
                    ("prefilter_repeat", _modelRouter.TurnGate.MechanicalRepeats.ToString()),
                    ("prefilter_repeat_degrade", _modelRouter.TurnGate.RepeatDegrades.ToString()),
                    // R498 候选③: 改写族吸收/降级必须可与复述族分列读数 (合算 ⇒ 归属不可辨)
                    ("prefilter_paraphrase", _modelRouter.TurnGate.MechanicalParaphrases.ToString()),
                    ("prefilter_paraphrase_degrade", _modelRouter.TurnGate.ParaphraseDegrades.ToString()),
                    ("prefilter_violations", _modelRouter.TurnGate.PrefilterViolations.ToString()),
                    ("role", ActiveRole.Id));
            }

            // R495 本地决策台账: 每轮闸判定**单点**落盘 (pass/skip 都记) —— 台账是 r1 侧真值的落盘面,
            // 挂载块 (远端调用前渲染) 引用它 ⇒ 「链自己做过什么决策」成为下游可核的本地真值。
            // 幂等 (同 turn/kind/chars 重复只记一条); 无会话 (一次性请求) 不记。
            {
                // 只读一次会话 id (可空流分析: 不在此处触碰成员的 not-null 状态)
                var ledgerSession = message.SessionId;
                var decisionKind = gateOutcome.Decided
                    ? (gateOutcome.Verdict == agent.modelqueue.TurnGateVerdict.Skip ? "skip" : "pass")
                    : "undecided";
                var ledgerCode = agent.modelqueue.LocalDecisionLedger.Record(
                    ledgerSession, prompt.TurnIndex, decisionKind, gateOutcome.Raw);
                agent.config.AgentTelemetry.Emit("local_decision_ledger", "IndustrialAgentV2",
                    ("turn", prompt.TurnIndex),
                    ("kind", decisionKind),
                    ("decided", gateOutcome.Decided ? "true" : "false"),
                    ("n", agent.modelqueue.LocalDecisionLedger.Count(ledgerSession)),
                    // R497 候选① (真值收口): 打点面**只留指纹** —— 旧写法把 raw 码 (LCM-<12hex>) 写进
                    // host.jsonl ⇒ 臂可读工作区 (data/telemetry/) 里就有真值, 台账「真值不落盘」被遥测面
                    // 反向破口 (R496 nonrecompute Q4 实测命中)。改为 code8 (码的 sha8) + key_id (进程密钥指纹):
                    // 二者都不足以反推码 ⇒ 掉一条信息都不影响判真伪, 却把打点面从真值面移出。
                    ("code8", agent.modelqueue.LocalDecisionLedger.Code8(ledgerCode)),
                    ("key_id", agent.modelqueue.LocalDecisionLedger.KeyId()),
                    ("session8", agent.modelqueue.LocalDecisionLedger.Sha8(ledgerSession ?? string.Empty)),
                    ("mount_axis", agent.modelqueue.LocalDecisionLedger.IsEnabled() ? "1" : "0"),
                    ("recorded", agent.modelqueue.LocalDecisionLedger.Recorded),
                    ("file_errors", agent.modelqueue.LocalDecisionLedger.FileErrors));
            }

            if (gateOutcome.Decided && gateOutcome.Verdict == agent.modelqueue.TurnGateVerdict.Skip)
            {
                // v0.58.0 R438 (本地消化 × R379 回放不变量的交互缺陷修复):
                // 本轮**没有任何远端调用** ⇒ 本轮内联块 (下轮预估/会话记忆/召回/技能知识) 从未发往任何 provider
                // ⇒ 它不是任何 provider 缓存前缀的一部分, **不得落进会话历史**。
                // 此前 SentContent 在 1267 行无条件写入 (含块), 经 GetConversationHistoryAsync (SentContent ?? Content)
                // 落盘, 被此后每一次远端调用逐字回放 = 纯白付账 (实测 p12: 4 个跳过轮 × 6 次调用 = 2238 token ≈ 8.1 pt)。
                // 回放铁律的正确读法: 「发送字节=回放字节」只约束**真正发出去的**轮次; 本地消化轮的规范形态
                // = 用户轮原文 (扣框架子请求, 与首轮同形——首轮无块可挂)。
                // R443: 反事实消融臂 (默认关 = 生产行为)。开 ⇒ 显式回放「本地消化轮」的内联块,
                // 把「被跳轮不回放」这条改动做成同网格**单变量**对照 (与 R442 的离线代数分解互为独立通道)。
                var replaySkipped = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_GATE_REPLAY_SKIPPED") == "1";
                message.SentContent = replaySkipped ? sentUserContent : outboundText;
                agent.config.AgentTelemetry.Emit("local_gate_skip_history", "IndustrialAgentV2",
                    ("persisted_chars", (long)message.SentContent.Length),
                    ("would_be_chars", (long)sentUserContent.Length),
                    ("dropped_chars", (long)(sentUserContent.Length - message.SentContent.Length)),
                    ("replay_skipped", replaySkipped ? "1" : "0"),
                    ("intent", intent));
                // 本地消化: 零远端 token (回复由本地 r1 生成, 失败 → 固定兜底串)
                // R465: 纯复述族 ⇒ 本地消化 = **回放上一条答复原文** (用户要的就是原样重来, 不需要新内容)。
                // R475: 回放候选在 Skip 判定点已按 `IsReplayableReply` 过滤 (实质答复才可回放) ⇒
                //       走到这里时 `repeatTurnFlag ⇒ repeatPrevReply != null`; 无实质上一条的复述轮已在上面降级远端。
                //       取不到 (非复述轮) ⇒ 退回既有兜底串 (仍零远端调用, 与 Ack 轮同形)。
                var localReply = repeatPrevReply ?? await _modelRouter!.ComposeLocalSkipReplyAsync(prompt.UserMessage, ct).ConfigureAwait(false);
                // R466: 结算类**单源** —— 打点与收口面优先级读同一个变量 (两处各写一份字符串必漂移)
                var replyKind = localRewriteIsParaphrase ? agent.context.ContinuationBrief.SettleLocalParaphrase
                    : repeatPrevReply is not null ? agent.context.ContinuationBrief.SettleRepeatVerbatim
                    : (repeatTurnFlag ? "repeat_no_prev" : "template");
                _localSettleKind = replyKind;
                // RF0002 §2.2 评分回执 (用户令「下次使用时有用就留, 没用就扔掉」): 形状命中且**本地消化真成立**
                // ⇒ 该形状有用 ⇒ 保留并加分 (上限 +4); 无用分支在各降级点剔除。
                if (repeatTurnFlag || paraphraseTurnFlag)
                {
                    var shapeUseful = replyKind == agent.context.ContinuationBrief.SettleRepeatVerbatim
                                      || replyKind == agent.context.ContinuationBrief.SettleLocalParaphrase;
                    agent.nlp.NlpGate.ReportOutcome(message.Content,
                        repeatTurnFlag ? agent.nlp.NlpGate.FaceRepeat : agent.nlp.NlpGate.FaceParaphrase,
                        useful: shapeUseful);
                }
                agent.config.AgentTelemetry.Emit("local_gate_skip_reply", "IndustrialAgentV2",
                    ("kind", replyKind),
                    ("chars", (long)localReply.Length),
                    ("msg_sha16", agent.modelqueue.LocalInputFingerprint.Sha16(message.Content)));
                llmResponse = new LLMResponse
                {
                    Content = localReply,
                    Success = true,
                    Model = "local:turn-gate",
                    // R478: 本地消化轮**不是**远端调用 ⇒ 用显式标记替代空值 (join 时与远端 id 不相混)
                    ResponseId = "local:turn-gate",
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

            // R527 候选②: 有界抽取 —— 因果绑定 + 偏题/牵引/澄清状态推进 (原位同序搬出, 行为等价)
            var (steeringPending, clarifyPending) =
                BindReplyAndAdvanceTopicState(llmResponse, isDrift, coreTopic, topicVerdict);

            // R575 回补点 (W2): 「LLM 返回后回补闸数据」的唯一调用点 —— 本轮**真走了远端**且成功 ⇒
            // 按输入所属结构面登记回补签名 (agent.nlp.NlpGate) ⇒ 下次同形状输入可在本地面成立。
            // 本地消化轮 (Skip) 无需回补; 族外输入不登记 (回补只在白名单族内生效)。
            if (!(gateOutcome.Decided && gateOutcome.Verdict == agent.modelqueue.TurnGateVerdict.Skip))
                agent.modelqueue.TurnGateJudge.LearnOnSuccess(message.Content, llmResponse.Success);
            
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
                                // R426: 关系判官 caller 选择 —— 开关开且端口在 ⇒ 本地优先 (r1),
                                // 本地不可用/失败/未解析出字母 ⇒ 远端兜底 (绝不静默给结论)。
                                var judgeSource = "remote";
                                var judgePromptLen = 0;
                                var judgeMs = 0L;
                                var judgeLetter = "";
                                // R443: 本地判官的 prompt/生成 tokenizer 真值 (远端兜底 ⇒ -1)
                                var judgeEvalTokens = -1;
                                var judgeNewTokens = -1;
                                var judgeGenTokens = -1;
                                var verdict = await agent.roles.CorrectionDetector.JudgeAsync(
                                    question, lastReply ?? "",
                                    async (prompt, maxTokens) =>
                                    {
                                        judgePromptLen = prompt.Length;
                                        var t0 = Environment.TickCount64;
                                        if (_modelRouter?.RelationJudgeEnabled == true)
                                        {
                                            // 本地调用不随单轮 ct 取消 (与远端同语义: 后台赏罚任务不能被轮生命周期掐掉,
                                            // 否则 CorrectionDetector 会把取消吞成 NEUTRAL 而非降级)。
                                            var local = await _modelRouter.JudgeRelationLocalAsync(
                                                CorrectionJudgeSystem, prompt, CancellationToken.None);
                                            if (local is not null)
                                            {
                                                judgeSource = "local";
                                                judgeLetter = local.Letter;
                                                judgeMs = Environment.TickCount64 - t0;
                                                judgeEvalTokens = local.PromptTokens;
                                                judgeNewTokens = local.PromptNewTokens;
                                                judgeGenTokens = local.CompletionTokens;
                                                return (local.Letter, local.CompletionTokens);
                                            }
                                            judgeSource = "remote_fallback";
                                        }
                                        var remote = await DetectViaLlm(prompt, maxTokens);
                                        judgeLetter = (remote.Content ?? string.Empty).Trim();
                                        judgeMs = Environment.TickCount64 - t0;
                                        return remote;
                                    }, ct);
                                GrowthLedger.Record(verdict.Kind, domainKey);
                                agent.config.AgentTelemetry.Emit("correction_judge", "IndustrialAgentV2",
                                    ("source", judgeSource), ("kind", verdict.Kind.ToString()), ("signal", verdict.Signal),
                                    ("letter", judgeLetter), ("prompt_len", judgePromptLen), ("ms", judgeMs),
                                    // R435: 本地判官状态/失败原因入遥测 (R434 缺口: fallback 时 letter 被远端文本覆盖,
                                    // 归因不可见)。local_state 取值: local | remote_fallback:unparsed:<reason> | ...
                                    ("local_state", _modelRouter?.RelationJudge.LastSource ?? ""),
                                    ("tokens", verdict.TokensUsed),
                                    // R443: 本地判官 tokenizer 真值 (source=local 时有效; 远端/兜底 = -1)
                                    ("tokens_evaluated", judgeEvalTokens.ToString()),
                                    ("prompt_new", judgeNewTokens.ToString()),
                                    ("gen_tokens", judgeGenTokens.ToString()),
                                    ("msg_head", question.Length > 18 ? question.Substring(0, 18) : question),
                                    ("session", memSession.Id), ("domain", domainKey));
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
                // R414 (真缺陷闭合): 上游在"空正文重试后仍失败"这类**可命名失败**里写入的是**面向用户的降级文案**;
                // 此处曾一律丢弃 (string.Empty) ⇒ router 侧"绝不静默返回空白"的契约在链上被推翻, 用户可见回复为空且无任何文案。
                // 真机证据 (eval/rover/r371d7, empty_always 臂): 轮 1 reply_len=0 / loop_turn.reply_chars=0, 轮 2 才见到文案。
                // 只透出被上游**显式标记**为面向用户的内容: 未标记的 Content 仍是内部片段/原始报错, 不得外泄。
                response.Content = UserFacingFailureContent(llmResponse);
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
        
        if (_resumeVoidNotice is not null)
        {
            // R457: 上一轮检查点已作废, 本轮按新任务执行 —— 前置如实告知, 不静默吞掉。
            // R458: 告知已改为人话一句 (PlanResumeService.HumanizeVoidNotice), 内部术语只进遥测。
            response.Content = _resumeVoidNotice + response.Content;
            _resumeVoidNotice = null;
        }

        // R461: 契约声明 (clickproof 围栏/裸块/no_formal 行) 只进验证面与遥测, **不上前台**。
        // 位置: 在全部内容变更 (段路由 / 产物修复 / 承接兜底) 之后, 收口判定之前 —— 验证面此时已消费过声明,
        // 剥离不影响机检; 剥离后为空时 SplitFacing 内部 fail-safe 返回原文 (宁可少剥, 不给用户空回复)。
        var facingSplit = agent.context.FormalPromptContract.SplitFacing(response.Content);
        if (facingSplit.Declaration.Length > 0)
        {
            response.Content = facingSplit.Visible;
            agent.config.AgentTelemetry.Emit("contract_declaration_hidden", "IndustrialAgentV2",
                ("decl_chars", facingSplit.Declaration.Length), ("facing_chars", facingSplit.Visible.Length));
        }

        // R458 收口 (fail-closed): 承接轮的回复必须接地 —— 空回复, 或既无问句又不含任何真实产物名
        // ⇒ 链自身用同一批真实事实组装反问 (绝不编造; 事实为空时只反问, 不提任何文件名)。
        // R466 优先级 (修 R465 C3): 本地**已确定性结算**的轮次 (纯复述 ⇒ 回放上一条答复原文)
        // 答复对象就是会话里的真实上一条答复 ⇒ 承接反问的前提不成立, 不得覆盖 (判据单源:
        // ContinuationBrief.ShouldApplyFallback)。开关默认开; 置 0 复原 R465 行为, 供同二进制负控。
        if (_continuationFacts is not null)
        {
            var settleKind = ContinuationRepeatPriorityOn ? _localSettleKind : null;
            var grounded = !agent.context.ContinuationBrief.NeedsFallback(response.Content, _continuationFacts);
            var applyFallback = agent.context.ContinuationBrief.ShouldApplyFallback(
                settleKind, response.Content, _continuationFacts);
            if (applyFallback)
                response.Content = agent.context.ContinuationBrief.ComposeFallback(
                    _continuationUserText, _continuationFacts, _continuationTotal);
            agent.config.AgentTelemetry.Emit("continuation_closure", "IndustrialAgentV2",
                ("grounded", grounded), ("apply_fallback", applyFallback),
                ("settle_kind", settleKind ?? ""),
                // 本会覆盖却被优先级抑制 ⇒ 必须可见 (静默抑制 = 读数与真实走向相反, R433 教训)
                ("suppressed", (!grounded && !applyFallback)),
                ("priority", ContinuationRepeatPriorityOn ? "on" : "off"),
                ("artifacts", _continuationFacts.Count),
                ("chars", response.Content.Length));
        }
        response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
        // v0.11.0 R62: 台账度量字段 — 问询数 (回复含问句) 与 executive 直达标记
        var asked = response.Content.Contains('？') || response.Content.Contains('?');
        agent.config.AgentTelemetry.Emit("loop_turn", "IndustrialAgentV2",
            ("total_ms", response.ExecutionTimeMs), ("success", response.Success),
            ("reply_chars", response.Content.Length), ("asked", asked),
            // R478: 本轮答复**因果绑定**到具体调用 (R477 P4: 时间窗归属把 5 次调用判成"窗口外")
            ("request_id", _replyRequestId),
            ("finish_reason", _replyFinishReason),
            ("empty_body", _replyEmptyBody),
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

        // 显式槽位结构 (语言无关, **无词表**) — 原「约束/限制」标记表 + 「只能/不许/必须/避免」助动词表
        // 已随中文词表一并移除。现只认「短头 + 冒号」结构信号: X：Y ⇒ Y 段为显式槽位;
        // 其余约束由结构化槽位链 (LLM 回执 → 槽位) 承担, 机械面不再凭词面猜。
        for (var i = 0; i < text.Length; i++)
        {
            var ch = text[i];
            if (ch != '：' && ch != ':') continue;
            if (i + 1 < text.Length && text[i + 1] == '/') continue;   // "https://" 协议头不是槽位
            var head = text[..i].TrimEnd();
            var cut = head.LastIndexOfAny(['，', ',', '。', '；', ';', '\n', ' ', '\u3000']);
            var label = (cut >= 0 ? head[(cut + 1)..] : head).Trim();
            if (label.Length == 0 || label.Length > 6) continue;
            var slotSeg = text[(i + 1)..];
            var slotEnd = slotSeg.IndexOfAny(['。', '；', ';', '\n']);
            var slotText = (slotEnd > 0 ? slotSeg[..slotEnd] : slotSeg).Trim();
            if (slotText.Length > 1 && !constraints.Any(c => slotText.Contains(c) || c.Contains(slotText)))
                constraints.Add(slotText.Length > 60 ? slotText[..60] + "…" : slotText);
            if (constraints.Count >= 8) break;
        }

        // 以下两段为词表时代的遗留结构 (标记表/助动词表均已为空 ⇒ 不产出), 保留是因为它们
        // 的「去重 + 60 字截断」口径已由上方结构面等价承担。
        var markers = Array.Empty<string>();
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
        string[] auxMarkers = [];
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

    
    /// <summary>
    /// EvidenceGate 裁定 → ClarificationBatch 真实批量问询 (v7.14 ①)。
    /// 低置信子任务 (置信度<阈值 或 MissingParameter) 生成疑问组; 有问询服务时 REPL 弹批量问题,
    /// 用户答案 (模式化, 绝不落凭据) 记入偏好库并拼为补充说明; 无服务/无疑问/问询失败 → 原样放行 (不阻断)。
    /// </summary>

    /// <summary>
    /// 1.6 影子计划 (v7.15 归拢接线 T.2-4 第一步):
    /// TaskPlanBuilder.Build + TaskPlanExecutor 以哑 nodeRunner 演练计划调度语义
    /// <summary>R527 候选② 有界抽取: 轮起始状态清零 + 活动心跳 (自 OnProcessAsync 原位搬出, 语义不变)。</summary>
    private DateTime BeginTurn(Message message)
    {
        var startTime = DateTime.UtcNow;
        // R458: 承接轮状态逐轮清零 (早退路径也走这里 ⇒ 不会把上一轮的产物事实/原话带到别的轮)
        _continuationFacts = null;
        _continuationUserText = null;
        // R466: 本地结算类同批清零 —— 上一轮的 repeat_verbatim 不得粘到本轮 (否则本轮承接反问被误抑制)
        _localSettleKind = null;
        _replyRequestId = "";
        _replyFinishReason = "";
        _replyEmptyBody = false;
        // v0.17.2-a (R336): 活动心跳 — 每轮注册本进程活动 (任务摘要), 退出由 10s TTL 过期自清
        try { Activity().Heartbeat(message.Content); } catch { /* 活动感知不阻塞主链 */ }
        return startTime;
    }
    /// <summary>R527 候选② 有界抽取: 回复因果绑定 + 偏题计数/牵引/澄清状态推进 (自 OnProcessAsync 原位搬出, 语义不变)。</summary>
    private (bool SteeringPending, bool ClarifyPending) BindReplyAndAdvanceTopicState(
        LLMResponse llmResponse, bool isDrift, string coreTopic,
        agent.intent.TopicRelevanceEvaluator.TopicRelevanceVerdict? topicVerdict)
    {
        // R478: 因果绑定捕获 (R477 P4: 时间窗归属把 5 次调用判成"窗口外" ⇒ 改用同值 id join)
        _replyRequestId = llmResponse.ResponseId ?? "";
        _replyFinishReason = llmResponse.FinishReason ?? "";
        _replyEmptyBody = string.IsNullOrEmpty(llmResponse.Content);

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
        return (steeringPending, clarifyPending);
    }
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
    
}
