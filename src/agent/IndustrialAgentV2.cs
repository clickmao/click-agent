using Microsoft.Extensions.Logging;
using agent.core;
using agent.workspace;
using agent.codegen;
using agent.planner;
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
        agent.userinteraction.IUserPromptService? promptService = null) : base(logger, handlers)
    {
        _promptService = promptService;
        _workspace = workspace;
        _codeGenerator = codeGenerator;
        _recoverySystem = recoverySystem;
        _vectorStore = vectorStore;
        _memoryRecall = memoryRecall;
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
    
    protected override async Task<AgentResponse> OnProcessAsync(Message message, CancellationToken ct)
    {
        var startTime = DateTime.UtcNow;
        var response = new AgentResponse();
        
        try
        {
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
            if (subTasks.Count > 1)
            {
                _logger.LogInformation(
                    "Intent decomposed into {Count} sub-tasks, primary={Intent}, intents=[{Intents}]",
                    subTasks.Count, intent, string.Join(",", subTasks.Select(t => t.Intent)));
            }
            
            // 1.5 EvidenceGate 裁定 → ClarificationBatch 真实批量问询 (v7.14 ①):
            // 低置信子任务生成疑问 → REPL 弹批量问题 → 答案并入本轮任务描述 (不带疑问硬执行)
            var clarifiedAddendum = await RunEvidenceGateAsync(message, subTasks, ct);
            if (!string.IsNullOrEmpty(clarifiedAddendum))
            {
                message.Content = $"{message.Content}\n[用户补充说明]\n{clarifiedAddendum}";
                _logger.LogInformation("EvidenceGate 补充了 {Count} 字用户说明", clarifiedAddendum.Length);
            }

            // 2. 多数据源上下文组装（失败时降级为空上下文，不阻断对话）
            var contextResult = await AssembleContextAsync(message, intent, subTasks, ct);
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
            
            // 5. ✅ 调用 LLM（传入完整 Prompt）
            var llmResponse = await _llmCaller.CallAsync(prompt, ct);
            
            // 6. ✅ 将消息添加到会话
            await AddToSessionAsync(message, llmResponse, ct);
            
            // 7. 存储到记忆
            await StoreToMemoryAsync(message, llmResponse, intent, ct);

            // 7.5 会话长期记忆回写 (v7.14): 每轮摘要入滚动记忆, 目标句从首轮任务锚定
            try
            {
                var memSession = await _sessionManager.GetOrCreateSessionAsync(message.SessionId, message.SenderId);
                var mem = memSession.Memory;
                if (string.IsNullOrEmpty(mem.Goal?.GoalText))
                    mem.SetGoal(message.Content.Length > 200 ? message.Content[..200] + "…" : message.Content);
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
        return response;
    }
    
    #region Core Methods
    
    /// <summary>
    /// EvidenceGate 裁定 → ClarificationBatch 真实批量问询 (v7.14 ①)。
    /// 低置信子任务 (置信度<阈值 或 MissingParameter) 生成疑问组; 有问询服务时 REPL 弹批量问题,
    /// 用户答案 (模式化, 绝不落凭据) 记入偏好库并拼为补充说明; 无服务/无疑问/问询失败 → 原样放行 (不阻断)。
    /// </summary>
    private async Task<string> RunEvidenceGateAsync(
        Message message, IReadOnlyList<IntentDecomposer.SubTask> subTasks, CancellationToken ct)
    {
        if (_promptService == null || subTasks.Count == 0)
            return string.Empty;
        try
        {
            var gate = new agent.registry.EvidenceGate();
            var verdict = gate.Evaluate(subTasks);
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
                : IntentSourceMapping.GetSources(intent)
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
    
    public OpenAILLMCaller(
        HttpClient httpClient,
        string apiKey,
        string model = "gpt-4")
    {
        _httpClient = httpClient;
        _apiKey = apiKey;
        _model = model;
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
            
            var requestBody = new
            {
                model = _model,
                messages = messages,
                max_tokens = 2000,
                temperature = 0.7
            };
            
            var request = new HttpRequestMessage(HttpMethod.Post, "https://api.openai.com/v1/chat/completions");
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
