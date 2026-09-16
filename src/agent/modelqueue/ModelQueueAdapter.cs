using agent.core;
using agent.modelqueue;
using agent.templates;

namespace agent;

/// <summary>
/// 模型队列适配器 (v7.15 C.3.3): ILLMCaller → ModelQueueRouter。
/// 协议转换: agent Prompt → QueuePrompt; QueueResponse → LLMResponse。
/// DI: ILLMCaller = ModelQueueAdapter (内部持 Router); /model /balance 指令直接用 Router/服务。
/// R456: 动作环在此收口 —— 声明 tools → 解析 tool_calls → 执行(端口) → 回灌 → 再调用 (≤MaxSteps)。
/// </summary>
public sealed class ModelQueueAdapter : ILLMCaller, agent.subagent.ILLMCallerForIsolated
{
    private readonly ModelQueueRouter _router;
    private readonly IActionPort? _actionPort;
    private readonly Action<int, ActionToolCall, ActionExecutionResult>? _onAction;

    public ModelQueueAdapter(ModelQueueRouter router, IActionPort? actionPort = null)
    {
        _router = router;
        _actionPort = actionPort;
        _onAction = actionPort is agent.action.WorkspaceActionPort wap ? wap.Audit : null;
    }

    /// <summary>R456: 最近一次动作环结果 (遥测/证据用; 无动作环时为 null)。</summary>
    public ActionLoopOutcome? LastActionOutcome { get; private set; }

    /// <summary>
    /// R379: Prompt → QueuePrompt 协议转换 (自 CallAsync 抽出为单一事实源, 缓存前缀机检直接消费)。
    /// 契约: History 按时间正序**全量**映射 (倒序窗口/截断都会让 provider 缓存前缀失配)。
    /// R490 例外 (唯一): **本地模板答复** (零远端调用轮次的产物, 从未发往任何 provider)
    /// 不是缓存前缀的一部分 ⇒ 剔除 (见 <see cref="IsLocalTemplateReply"/>)。
    /// </summary>
    public static QueuePrompt ToQueuePrompt(Prompt prompt)
        => ToQueuePrompt(prompt, ReplayPairTrim.IsEnabled());

    /// <summary>R491: 判据表可直接吃两态 (门开/门关), 无需改环境变量即可机检。</summary>
    public static QueuePrompt ToQueuePrompt(Prompt prompt, bool pairTrim)
    {
        var qp = new QueuePrompt
        {
            SystemPrompt = prompt.SystemPrompt,
            ContextPrompt = prompt.ContextPrompt,
            UserMessage = prompt.UserMessage,
            EstimatedTokens = prompt.EstimatedTokens,
            SessionId = prompt.SessionId,
            TurnIndex = prompt.TurnIndex,
            // v0.11.0 R22: 推理档位透传 (deepseek 实测 low 档 reasoning 24ch vs 90ch)
            ReasoningEffort = prompt.ReasoningEffort,
            // v0.12.0 A2: 图像附件透传 (Router 带图强制云端 + parts[] — 本地 qwen 无视觉, 缺陷 62)
            ImageUrls = prompt.ImageUrls,
            Intent = prompt.Intent,
            // R494: 隔离通道标记透传 (声明面通道轴的唯一输入; 由隔离调用点显式置位)
            IsolatedChannel = prompt.IsolatedChannel,
        };
        var trimmedLocalTemplates = 0;
        var trimmedLocalUserTurns = 0;
        for (var i = 0; i < prompt.History.Count; i++)
        {
            var msg = prompt.History[i];
            var role = msg.Role == MessageRole.User ? "user" : "assistant";
            // R490 回放剪裁: 本地模板答复 (「收到。」= 零远端调用 Skip 轮的产物) **不是任何 provider 的产出**,
            // 从未发往任何 provider ⇒ 不是任何缓存前缀的一部分。此前被逐字回放 (R489 实测: 51 次请求体内
            // 共 100 条 assistant 「收到。」) ⇒ 纯白付账 + 上下文噪声 (R438 只修了 user 侧, assistant 侧是缺口)。
            // 注: 复述轮 (R465/R475) 的本地答复 = **回放上一条实质答复原文** (provider 产出) ⇒ 不在此列。
            if (role == "assistant" && IsLocalTemplateReply(msg.Content))
            {
                trimmedLocalTemplates++;
                // R491 配对剪裁 (闸默认关): 该轮 user 侧同样是零远端调用的输入,
                // 从未随任何请求发出 ⇒ 留着只会造成 user→user 相邻 + 白付 token。
                if (pairTrim && qp.History.Count > 0 && qp.History[qp.History.Count - 1].Role == "user")
                {
                    qp.History.RemoveAt(qp.History.Count - 1);
                    trimmedLocalUserTurns++;
                }
                continue;
            }
            qp.History.Add(new QueueHistoryMessage
            {
                Role = role,
                Content = msg.Content,
            });
        }
        qp.ReplayTrimmedLocalTemplates = trimmedLocalTemplates;
        qp.ReplayTrimmedLocalUserTurns = trimmedLocalUserTurns;
        return qp;
    }

    /// <summary>
    /// R490: 本地模板答复判别 (回放剪裁的唯一判据)。
    /// 只吃产品自身常量 <see cref="ModelQueueRouter.LocalSkipFallback"/> (= 零 token 模板串),
    /// 非用户文本关键词表 (R458 铁律)。复述轮回放的**实质原文**与模板串不等 ⇒ 不受影响。
    /// </summary>
    public static bool IsLocalTemplateReply(string? content)
        => content is not null && content.Trim() == ModelQueueRouter.LocalSkipFallback;

    public async Task<LLMResponse> CallAsync(Prompt prompt, CancellationToken ct = default)
    {
        var qp = ToQueuePrompt(prompt);
        // R373: 意图透传 (此前硬编码 "general" → 首轮预算策略永远匹配不上, 真机铁证:
        // 代码任务首轮 completion_tokens=8192 被推理吃满 → content 空/半截, 每题 2 次调用)。
        var intent = string.IsNullOrWhiteSpace(prompt.Intent) ? "general" : prompt.Intent!;
        QueueResponse r;
        if (_actionPort is not null && ActionLoopRunner.IsEnabled())
        {
            // R456 声明面: 仅在动作环开启时注入 tools —— 关闭时请求体与旧版逐字节相同 (零回归)
            // R490 声明面按需: 门开 (AGENTFRAMEWORK_TOOL_DECL_GATE) 时只对**工作区动作类意图**下发。
            // 门关 (未设) ⇒ 恒下发 ⇒ 与 R456..R489 逐字节相同。
            // R494 通道轴: 隔离通道 (微步骤隔离问询 / 一次性隔离子任务) 结构上没有工作区 ⇒
            // 通道轴开时恒不下发 (轴上判据只吃调用点显式置位的结构量, 非文本)。
            if (ToolDeclGate.ShouldDeclare(prompt.Intent, ToolDeclGate.IsEnabled(),
                    qp.IsolatedChannel, ToolDeclGate.IsChannelGateEnabled()))
                qp.ToolsJson = ActionToolDecl.ToolsJson;
            var (resp, outcome) = await ActionLoopRunner.RunAsync(
                qp,
                (p, c) => _router.CallAsync(p, TaskKindHint.General, intent, c),
                _actionPort,
                ActionLoopRunner.MaxSteps(),
                ct,
                _onAction).ConfigureAwait(false);
            r = resp;
            LastActionOutcome = outcome;
        }
        else
        {
            r = await _router.CallAsync(qp, TaskKindHint.General, intent, ct);
            LastActionOutcome = null;
        }
        return new LLMResponse
        {
            Content = r.Content,
            Success = r.Success,
            Error = r.Error,
            Model = r.Model,
            PromptTokens = r.PromptTokens,
            TokensUsed = r.TokensUsed,
            CacheHitTokens = r.CacheHitTokens,
            CacheMissTokens = r.CacheMissTokens,
            ReasoningContent = r.ReasoningContent,
            // R414: "失败但有面向用户的文案"的契约位必须透传 (否则链侧无从区分"可展示文案"与"内部片段")
            ContentIsUserFacing = r.ContentIsUserFacing,
            // R478: 逐调用因果 id + 上游 finish_reason 透传 (loop_turn.request_id 与 llm_call.request_id 同值可 join)
            ResponseId = r.RequestId,
            FinishReason = r.FinishReason,
        };
    }
}
