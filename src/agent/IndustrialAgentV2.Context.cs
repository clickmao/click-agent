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

public partial class IndustrialAgentV2 : AgentBase
{

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
                request.SessionMemoryBlock = agent.core.RecallRealityGate.Verify(
                    rendered,
                    _workspace is { RootPath: { Length: > 0 } gateRoot } ? gateRoot : Environment.CurrentDirectory);
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

            // R461: 记忆只存**面向用户的正文** —— 契约声明 (clickproof 围栏/裸块/no_formal) 是给本地验证器看的,
            // 存进记忆后会被下一轮原样召回 (R460 实测: 召回块里带 no_formal: 行) ⇒ 既污染上下文又白付 token。
            var facing = agent.context.FormalPromptContract.SplitFacing(output.Content).Visible;

            var entry = new VectorDocument
            {
                Content = $"Q: {input.Content}\nA: {facing}",
                Summary = facing.Length > 100
                    ? facing[..100] + "..."
                    : facing,
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
}
