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
public class IndustrialAgentV2 : AgentBase
{
    private readonly IWorkspace _workspace;
    private readonly ICodeGenerator _codeGenerator;
    private readonly agent.registry.AgentRegistry _agentRegistry;
    private readonly agent.registry.ResponseSegmentRouter _segmentRouter;
    private readonly agent.registry.ClarificationService _clarificationService;
    private readonly agent.userinteraction.IUserPromptService? _promptService; // v7.14: EvidenceGate→批量问询驱动 (null=静默跳过)
    private readonly string _dataStoragePath;
    private readonly IRecoverySystem _recoverySystem;
    private readonly IVectorStore _vectorStore;
    private readonly IRAGRecall? _ragRecall;  // v0.11.0 R6: 存储召回同源修复
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
    private readonly agent.subagent.IsolatedTaskRunner? _isolatedTaskRunner;
    private readonly agent.modelqueue.ModelQueueRouter? _modelRouter;
    private readonly agent.modelqueue.BalanceQueryService? _balanceService;
    private readonly agent.modelqueue.TokenUsageService? _tokenUsageService;
    private readonly agent.modelqueue.ModelVerifyService? _verifyService;
    private readonly agent.logging.LogRouter? _logRouter;

    /// <summary>
    /// R21: 简单意图启发式 — 问候/闲聊/单句解释/事实问答走轻思考 (省 reasoning token 与延迟)。
    /// 复杂信号 (多步/代码/分析/对比/计划/长输入) 一律保留默认深推理, 宁可多花不可降智。
    /// </summary>
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
        IRAGRecall? ragRecall = null) : base(logger, handlers)
    {
        _isolatedTaskRunner = isolatedTaskRunner;
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
        var response = new AgentResponse();
        
        try
        {
            // 0.-1 /plan 计划查询 (v7.15 T.4-4): 输出最近一次影子计划 TaskPlanRun JSON (面板全 JSON 惯例)
            if (message.Content.Trim().Equals("/plan", StringComparison.OrdinalIgnoreCase))
            {
                response.Success = true;
                if (_lastShadowRun is null)
                {
                    response.Content = "{\"plan\": null, \"hint\": \"\u5c1a\u65e0\u8ba1\u5212\u6f14\u7ec3\u8bb0\u5f55 \u2014 \u53d1\u9001\u4e00\u6761\u591a\u5b50\u4efb\u52a1\u6d88\u606f\u540e\u518d\u67e5\"}";
                }
                else
                {
                    response.Content = TaskPlanJsonContext.ToJson(_lastShadowRun);
                }
                response.Data = new Dictionary<string, object> { { "localCommand", "plan" } };
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
                if (skillResult is { Success: true } && (skillResult.ForceUse || skillResult.Content.Length > 0))
                {
                    _logger.LogInformation("Skill {SkillId} activated ({Mode}, {Ms}ms)",
                        skillResult.SkillId, skillResult.ForceUse ? "force_use" : "executive", skillResult.ElapsedMs);
                    response.Success = true;
                    response.Content = skillResult.Content;
                    response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
                    return response;
                }
                // 未命中/失败/禁语拦截 → 静默降级普通推理 (S.5: 用户无感)
            }

            // 0. 非 LLM 本地强制指令拦截 (v7.11): /stop /continue 等, 不进意图识别/LLM
            var localCommand = agent.registry.LocalCommandRouter.TryRoute(message.Content);
            if (localCommand.Handled)
            {
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

            // 1. 意图识别 + 子任务拆解 (v7.9): 复合句拆为有序子任务, 主意图驱动模板选择
            var subTasks = IntentDecomposer.Decompose(message.Content);
            var intent = IntentDecomposer.PrimaryIntent(subTasks);
            agent.config.AgentTelemetry.Emit("intent", "IndustrialAgentV2",
                ("primary", intent), ("subtask_count", subTasks.Count),
                ("input_chars", message.Content.Length),
                ("sensitive", agent.intent.InjectedInstructionClassifier.IsSensitiveIntent(intent)));
            if (subTasks.Count > 1)
            {
                _logger.LogInformation(
                    "Intent decomposed into {Count} sub-tasks, primary={Intent}, intents=[{Intents}]",
                    subTasks.Count, intent, string.Join(",", subTasks.Select(t => t.Intent)));
            }
            
            // 1.4 隔离任务判定 (v7.15 I.2): 单任务 + 判定与主目标无关 → 隔离子执行, 不进主链
            // (首轮无 GoalProfile 锚 → 不隔离; 多子任务=当前目标链的一部分 → 不隔离)
            if (_isolatedTaskRunner != null && subTasks.Count == 1)
            {
                var goalMemory = _sessionMemoryStore.Load(message.SessionId);
                var goal = goalMemory?.Goal;
                var goalEntities = goal?.KeyEntities ?? new List<string>();
                // 首轮 (无目标锚) 不隔离 — 无"当前任务"可言
                if (goal != null && goalEntities.Count > 0)
                {
                    // v0.11.0 R14 修复: 第2参是 goalIntent, 原传 GoalText 原文 → 意图相同也误判"意图不同"+1
                    var (isIsolated, score, reason) = agent.intent.TaskRelevanceChecker.Check(
                        goalEntities, goal.GoalIntent, message.Content, subTasks[0].Intent);
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

            // 1.6 影子计划演练 (v7.15 归拢 T.2-4): Build+Execute 调度语义, 只记录不采纳, 不阻断主链
            _lastShadowRun = await RunShadowPlanAsync(message.Content, subTasks, ct);

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
            
            // 3. 获取对话历史
            var history = await GetConversationHistoryAsync(message.SessionId, 10, ct);
            
            // 4. ✅ 关键：构建真正发给 LLM 的 Prompt
            var systemPrompt = IntentPromptTemplates.GetSystemPrompt(intent);

            // 下轮预估读回 (v7.11): 上轮循环落盘的预估 → 指示 LLM 用户本轮输入倾向
            var identity = _agentRegistry.Get(message.SenderId is { Length: > 0 } ? message.SenderId : "main")
                            ?? _agentRegistry.Main;
            var forecast = agent.registry.NextTurnForecast.Load(_dataStoragePath, identity.Uid);
            var forecastHeader = agent.registry.NextTurnForecast.ToPromptHeader(forecast);
            if (forecastHeader.Length > 0)
                systemPrompt = systemPrompt + "\n" + forecastHeader;

            var prompt = _promptBuilder.BuildWithHistory(
                message,
                contextResult,
                systemPrompt,
                history);
            
            _logger.LogInformation(
                "Built prompt: {Tokens} tokens (Context: {ContextTokens})",
                prompt.EstimatedTokens,
                EstimateTokens(prompt.ContextPrompt));

            // v0.11.0: prompt 构成打点 (历史/上下文/系统占比 — token 治理对比数据)
            agent.config.AgentTelemetry.Emit("prompt_build", "IndustrialAgentV2",
                ("total_tokens", prompt.EstimatedTokens),
                ("history_msgs", prompt.History.Count),
                ("history_tokens", prompt.History.Sum(h => EstimateTokens(h.Content))),
                ("context_tokens", EstimateTokens(prompt.ContextPrompt)));
            
            // 4.5 思考流 (v7.15 L.2.2): 推理前发 page_switch + 构建摘要分片; LLM 返回后发 thinking_end
            if (_logRouter != null)
            {
                _logRouter.Write("IndustrialAgentV2", "info", agent.logging.LogChannel.Thinking,
                    $"prompt 构建完成: ~{prompt.EstimatedTokens} tokens, 意图={intent}",
                    contentFingerprint: FnvHash(prompt.UserMessage), contentLength: prompt.UserMessage.Length);
            }

            // 5. ✅ 调用 LLM（传入完整 Prompt）
            // v0.11.0 R21: 推理档位路由 — 简单任务轻思考省 token/延迟, 复杂任务保留默认深推理。
            // 实测 (glm-5.3-flash): 简单题 reasoning 0 vs 8910ch; 复杂题 low 档 wall -55%。
            prompt.ReasoningEffort = IsSimpleIntentForReasoning(intent, prompt.UserMessage) ? "low" : null;
            var llmResponse = await _llmCaller.CallAsync(prompt, ct);

            // 5.1 思考结束指令 (L.2.2 指令 2 — 前端关闭思考步骤显示并折叠)
            _logRouter?.EmitThinkingEnd(llmResponse.Content.Length);
            
            // 6. ✅ 将消息添加到会话
            await AddToSessionAsync(message, llmResponse, ct);
            
            // 7. 存储到记忆
            await StoreToMemoryAsync(message, llmResponse, intent, ct);

            // 7.5 会话长期记忆回写 (v7.14): 每轮摘要入滚动记忆, 目标句从首轮任务锚定
            try
            {
                var memSession = await _sessionManager.GetOrCreateSessionAsync(message.SessionId, message.SenderId);
                var mem = memSession.Memory;
                if (string.IsNullOrEmpty(mem.Goal?.GoalText) && IsGoalWorthy(message.Content))
                {
                    var goalText = message.Content.Length > 200 ? message.Content[..200] + "…" : message.Content;
                    // v0.11.0 (打点驱动修复): goal 锚定时抽取关键实体 — 实体空导致隔离判定永不触发
                    mem.SetGoal(goalText, agent.intent.TaskRelevanceChecker.ExtractEntities(goalText), intent);
                }
                mem.Remember($"[{intent}] {(llmResponse.Success ? "完成" : "失败")}: " +
                    (message.Content.Length > 120 ? message.Content[..120] + "…" : message.Content));
                if (llmResponse.Success)
                    mem.AddMilestone(intent);
                _sessionMemoryStore.Save(memSession.Id, mem);

                // agent 画像动态学习 (④): 任务类别胜率 + 工具亲和
                var learnUid = message.SenderId is { Length: > 0 } ? message.SenderId : "main";
                _agentProfileStore.GetOrCreate(learnUid)
                    .RecordTaskOutcome(intent, llmResponse.Success);
                _agentProfileStore.Save();
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
                response.Success = true;

                // 任务循环完成 → 下轮预估落盘 (v7.11): 工作目录 + 按 agent UID 隔离
                var saved = agent.registry.NextTurnForecast.Save(_dataStoragePath, identity.Uid, message.Content, intent);

                // v0.11.0 R14: 用户倾向写入链路修复 — 此前 UpdateTendencyAsync 无人调用, UserTendency 源恒 0
                _ = Task.Run(() =>
                {
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
                        return _tendencyAnalyzer.UpdateTendencyAsync(tendency.UserId, tendency);
                    }
                    catch { return Task.CompletedTask; } // 倾向写入失败不阻断主链
                });
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
        agent.config.AgentTelemetry.Emit("loop_turn", "IndustrialAgentV2",
            ("total_ms", response.ExecutionTimeMs), ("success", response.Success),
            ("reply_chars", response.Content.Length));
        return response;
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
    ///   /official-key &lt;k&gt;  → 官方通道 key 注入 (内存; 需求1 — ⚠ 指令名代拟, 用户未定名)
    ///   /official-key off  → 清除
    /// 返回 null = 非本组指令 (放行主链)。
    /// </summary>
    private AgentResponse? HandleModelCommand(string input, long elapsedMs)
    {
        var parts = input.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        var head = parts[0].ToLowerInvariant();

        if (head == "/official-key")
        {
            if (_modelRouter is null)
            {
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "official_key", Ok = false, Error = "model_queue_not_configured",
                }, elapsedMs);
            }
            // 无参 → 查询注入状态 (不回显 key 本身 — 凭据铁律)
            if (parts.Length == 1)
            {
                return MakeJsonResponse(new ModelCommandPayload
                {
                    Command = "official_key",
                    Ok = true,
                    OfficialKeyPresent = _modelRouter.OfficialKeys.IsAvailable(),
                }, elapsedMs);
            }
            var isOff = parts[1].Equals("off", StringComparison.OrdinalIgnoreCase);
            _modelRouter.SetOfficialKey(isOff ? null : parts[1]);
            return MakeJsonResponse(new ModelCommandPayload
            {
                Command = "official_key",
                Ok = true,
                OfficialKeyPresent = !isOff,
                Verdict = isOff ? "official_key_cleared" : "official_key_set (memory only)",
            }, elapsedMs);
        }

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
            var b = _balanceService.QueryAsync(parts.Length >= 2 ? parts[1] : null)
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

    private async Task<TaskPlanRun?> RunShadowPlanAsync(
        string sourceText, IReadOnlyList<IntentDecomposer.SubTask> subTasks, CancellationToken ct)
    {
        try
        {
            var plan = TaskPlanBuilder.Build(sourceText, subTasks);
            var executor = new TaskPlanExecutor(
                // 哑执行体: 影子不产真输出, 节点标 Skipped (只演练调度语义, 不烧 LLM)
                (node, _) => Task.FromResult(new NodeExecutionResult
                {
                    NodeId = node.Id, FinalState = PlanNodeState.Skipped, Output = null
                }));
            var run = await executor.ExecuteAsync(plan, pollInjections: null, ct);
            _logger.LogInformation(
                "Shadow plan {PlanId}: {Nodes} nodes → {State}; awaiting={Awaiting}, dropped={Dropped}",
                plan.PlanId, plan.Nodes.Count, run.State,
                run.NodeStates.Values.Count(s => s == PlanNodeState.AwaitingClarification),
                run.DroppedForEvidenceLimit.Count);
            return run;
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            // 影子失败不影响主链 (演练性质)
            _logger.LogWarning(ex, "Shadow plan failed (non-fatal)");
            return null;
        }
    }

    private TaskPlanRun? _lastShadowRun;

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
            EnabledSources = subTasks.Count > 1
                ? IntentDecomposer.AggregateSources(subTasks)
                : IntentSourceMapping.GetSources(intent),
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
            if (!string.IsNullOrEmpty(rendered))
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

        // v7.14: agent 画像 + 能力清单预渲染 (④⑤)
        try
        {
            var agentUid = message.SenderId is { Length: > 0 } ? message.SenderId : "main";
            var profile = _agentProfileStore.GetOrCreate(agentUid);
            var blocks = new List<string>();
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
    
    private async Task<List<Message>> GetConversationHistoryAsync(
        string sessionId,
        int maxMessages,
        CancellationToken ct)
    {
        if (string.IsNullOrEmpty(sessionId))
            return new List<Message>();
        
        var session = await _sessionManager.GetSessionAsync(sessionId);
        if (session == null)
            return new List<Message>();
        
        return session.Messages
            .Where(m => m.Role != MessageRole.System)
            .OrderByDescending(m => m.Timestamp)
            .Take(maxMessages)
            .Reverse()
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
                    Keywords = entry.Keywords.ToList(),
                    Metadata = entry.Metadata,
                    DocumentType = "conversation",
                });
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

public sealed class OpenAIChatMessage
{
    [JsonPropertyName("role")]
    public string Role { get; set; } = string.Empty;

    [JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;
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
            messages.Add(new OpenAIChatMessage { Role = "user", Content = prompt.UserMessage });
            
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
            
            var request = new HttpRequestMessage(HttpMethod.Post, _baseUrl + "/chat/completions");
            request.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", _apiKey);
            request.Content = new StringContent(
                JsonSerializer.Serialize(requestBody, LLMJsonContext.Default.OpenAIChatRequest),
                Encoding.UTF8,
                "application/json");
            
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
