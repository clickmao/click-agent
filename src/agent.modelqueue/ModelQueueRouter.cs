using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.modelqueue;

/// <summary>队列调用请求 (协议自洽 — 不依赖 agent 主程序集, adapter 负责转换)</summary>
public sealed class QueuePrompt
{
    public string SystemPrompt { get; set; } = string.Empty;
    public string ContextPrompt { get; set; } = string.Empty;

    /// <summary>(role, content) 历史</summary>
    public List<QueueHistoryMessage> History { get; set; } = new();
    public string UserMessage { get; set; } = string.Empty;

    /// <summary>预估输入 token (费用估算/选模)</summary>
    public int EstimatedTokens { get; set; }

    /// <summary>R379: 会话标识 + 轮次 (缓存前缀 KPI 逐轮归属; 空/0 = 一次性请求)</summary>
    public string? SessionId { get; set; }
    public int TurnIndex { get; set; }

    /// <summary>v0.11.0 R22: 推理档位建议 (null=默认深推理; low=轻思考)。</summary>
    public string? ReasoningEffort { get; set; }

    /// <summary>v0.12.0 A2: 图像附件 (URL/base64 data URL) — 非空时路由强制云端 + user 消息 parts[] 形态。</summary>
    public List<string> ImageUrls { get; set; } = new();
    public int ImageCount => ImageUrls.Count;

    /// <summary>R456 声明面: 工具声明 JSON (OpenAI function-calling 形态; null/空 = 不带工具, 行为与旧版逐字节一致)。</summary>
    public string? ToolsJson { get; set; }

    /// <summary>R456 回灌面: user 之后的追加消息 (assistant(tool_calls) / tool(...)) —— 前缀不变, 只增长尾部。</summary>
    public List<QueuePostUserMessage> PostUser { get; set; } = new();
}

public sealed class QueueHistoryMessage
{
    public string Role { get; set; } = "user";
    public string Content { get; set; } = string.Empty;
}

/// <summary>队列调用响应 (协议自洽)</summary>
public sealed class QueueResponse
{
    public string Content { get; set; } = string.Empty;
    public bool Success { get; set; } = true;
    public string? Error { get; set; }
    public string Model { get; set; } = "unknown";
    public int PromptTokens { get; set; }
    public int TokensUsed { get; set; }

    /// <summary>v0.21.1: 推理模型思考链 (reasoning_content); 非推理模型为 null。</summary>
    public string? ReasoningContent { get; set; }

    /// <summary>v0.10.0: 输出 token 数 (TokensUsed = prompt + completion)</summary>
    public int CompletionTokens => Math.Max(0, TokensUsed - PromptTokens);

    /// <summary>R377: prompt 缓存命中 token (provider 未上报 → null, 不得当 0)。</summary>
    public int? CacheHitTokens { get; set; }

    /// <summary>R377: prompt 缓存未命中 token (provider 未上报 → null)。</summary>
    public int? CacheMissTokens { get; set; }

    /// <summary>R456 解析面: 模型请求的工具调用 (空 = 纯文本回复, 与旧版行为一致)。</summary>
    public List<ActionToolCall>? ToolCalls { get; set; }

    /// <summary>R456: 上游 finish_reason (tool_calls/stop/length — 归因用)。</summary>
    public string? FinishReason { get; set; }

    /// <summary>R414: 本响应的 Content 是否为**面向用户的最终文案**(降级说明等) —— Success=false 时也必须在链上透出。
    /// false = Content 只是内部片段/原始报错, 链侧不得当作用户可见正文(避免错误正文/内部信息外泄)。</summary>
    public bool ContentIsUserFacing { get; set; }
}

/// <summary>模型队列调用端口 (adapter 在 agent 主程序集实现 ILLMCaller 时消费)</summary>
public interface IModelQueueCaller
{
    Task<QueueResponse> CallAsync(QueuePrompt prompt, TaskKindHint kind, string intent, CancellationToken ct = default);
}

/// <summary>模型切换审计事件 (C.4: 自动切换记录切换事件, /status JSON 可读)</summary>
public sealed class ModelSwitchRecord
{
    public string From { get; set; } = string.Empty;
    public string To { get; set; } = string.Empty;

    /// <summary>切换原因 (consecutive_failures / manual / cost_routing)</summary>
    public string Reason { get; set; } = string.Empty;

    public DateTime At { get; set; } = DateTime.UtcNow;
}

/// <summary>
/// 模型队列路由器 (v7.15 C.3.3): ILLMCaller 实现 — 内部按策略从模型目录选模型,
/// 主模型连续失败 N 次自动切备 (取消永不触发切换), 手动 /model 指定最高优先。
/// 序列化全走 source-gen fast-path (AOT 铁律)。
/// </summary>
public sealed class ModelQueueRouter : IModelQueueCaller
{
    private readonly ModelCatalog _catalog;
    /// <summary>
    /// R380: 会话 → 上一轮已发 prompt tokens (「需要命中的部分」的基准)。
    /// 有效命中率 = 本轮 hit / min(本轮 prompt, 上一轮 prompt) —— 本轮新增不计入分母。
    /// </summary>
    private readonly System.Collections.Concurrent.ConcurrentDictionary<string, int> _lastPromptTokens = new(StringComparer.Ordinal);

    /// <summary>R380: 取该会话"上一轮已发 prompt token 数"(无 → 0)。三处打点共用, 避免作用域各自重算。</summary>
    private int LastPromptTokensFor(string? sessionId)
        => string.IsNullOrEmpty(sessionId) ? 0 : (_lastPromptTokens.TryGetValue(sessionId, out var v) ? v : 0);

    private readonly ModelSelectionPolicy _policy;
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly Microsoft.Extensions.Logging.ILogger _logger;
    private readonly TokenUsageService? _tokenUsage;
    private readonly FallbackConfig _fallback;

    /// <summary>R413: 本地生成执行面 (null = 未注册 ⇒ 判据必拒, 全走远端 = 零回归)。</summary>
    private readonly ILocalGenerationPort? _localPort;

    /// <summary>R115 (缺陷 43): 余额快照惰性 fire-once 同步器 (进程内仅一次)</summary>
    private sealed class LazyBalanceSync
    {
        private Task? _task;
        private readonly object _lock = new();

        public Task EnsureStartedAsync(TokenUsageService service)
        {
            lock (_lock)
            {
                _task ??= Task.Run(async () =>
                {
                    try { await service.InitializeAsync().ConfigureAwait(false); }
                    catch { /* 初始化失败不阻断 — 余额未知不判定语义 */ }
                });
                return _task;
            }
        }
    }

    private readonly LazyBalanceSync _balanceSyncOnce = new();

    /// <summary>通道调度 (R351: 仅远端目录通道; 本地/官方已移除 — 用户钦定全 API 化)</summary>
    public ChannelScheduler Scheduler { get; }

    /// <summary>手动覆盖 (null = 自动); /model &lt;id&gt; 设置, /model auto 清除</summary>
    private string? _manualOverride;

    /// <summary>当前活跃模型 (自动粘性: 失败切换后固定到新模型, 成功不回切)</summary>
    private string? _activeModelId;

    private int _consecutiveFailures;
    public const int MaxConsecutiveFailures = 3;

    /// <summary>切换审计 (面板/CLI 可读)</summary>
    public List<ModelSwitchRecord> Switches { get; } = new();

    /// <summary>上一次选模依据 (审计/调试)</summary>
    public string LastSelectionBasis { get; private set; } = "init";

    private readonly object _lock = new();

    public ModelQueueRouter(
        ModelCatalog catalog,
        IHttpClientFactory httpClientFactory,
        Microsoft.Extensions.Logging.ILogger logger,
        ChannelScheduler? scheduler = null,
        TokenUsageService? tokenUsage = null,
        FallbackConfig? fallbackConfig = null,
        ILocalGenerationPort? localPort = null)
    {
        _fallback = fallbackConfig ?? new FallbackConfig();
        _catalog = catalog;
        _policy = new ModelSelectionPolicy();
        _httpClientFactory = httpClientFactory;
        _logger = logger;
        _dumpLogger = logger;   // R450: 落盘闸为静态方法 ⇒ 借最近构造实例的 logger 记告警 (仅诊断用)
        _tokenUsage = tokenUsage;
        _localPort = localPort;
        Scheduler = scheduler ?? new ChannelScheduler();
    }

    /// <summary>R413: 本地生成通道计数 (可观测/对账; Attempted==0 ⇒ 未尝试, 不得当"通过")。</summary>
    public LocalChannelCounters LocalChannel { get; } = new();

    /// <summary>R413: 最近一次本地通道决策 (ok / rejected:原因 / degraded:原因→remote)。</summary>
    public string? LocalChannelLastBasis { get; private set; }

    /// <summary>R413: 本地生成执行面端口 (null = 未注册)。</summary>
    public ILocalGenerationPort? LocalPort => _localPort;

    /// <summary>R413 前置门: 本地端口已注册 且 配置 <c>local.turn_gate=true</c> (默认 false ⇒ 零回归)。</summary>
    public bool TurnGateEnabled => _localPort is not null && _catalog.LocalChannel.TurnGate;

    /// <summary>
    /// 本地通道配置就绪 (gguf 存在) — 遥测可观测: 判定「门没开」到底是配置问题还是角色问题,
    /// 不靠猜 (R413 事故: 臂B 静默退化成臂A, 只因门未启用而无任何可观测证据)。
    /// </summary>
    public bool LocalChannelReady => _catalog.LocalChannel.IsReady;

    /// <summary>R413 前置门计数/依据 (可观测)。</summary>
    public TurnGateCounters TurnGate { get; } = new();

    /// <summary>
    /// R413 前置门判别: 本地端口判定「本轮是否携带新增诉求」。
    /// 失败/空回/记账违规/无法解析 ⇒ <c>Decided=false</c> (调用方必须降级远端, 绝不静默跳过); 取消上抛。
    /// </summary>
    /// <summary>
    /// R450: 门判**实发 prompt** 落盘闸 —— 器具锚的唯一权威源。
    /// 动机 (R449 实测): 源码派生重建器与产品实发文本漂移 (重建 480 vs 遥测 452 字符;
    ///   seed sha 逐位相同、模板源码未变) ⇒ 拿重建 prompt 做外部效度探针会得到
    ///   **产品不产生的行为** (探针 gen=6 直接出字母 vs 产品长思考, 正控 3/7 而产品 7/7)。
    /// 契约: 未设/空 ⇒ **完全关闭** (零产品变更: 不落盘、不建目录、不读文件);
    ///   设 = 追加 JSONL 一行 {seq,len,sha16,prompt}; 任何 IO 异常吞掉(记 warning)
    ///   —— 仪器绝不改变决策路径。
    /// </summary>
    internal static void DumpGatePrompt(string prompt)
    {
        var path = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_GATE_PROMPT_DUMP");
        if (string.IsNullOrWhiteSpace(path)) return;
        try
        {
            var sha16 = Convert.ToHexString(
                System.Security.Cryptography.SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(prompt)))[..16];
            var seq = System.Threading.Interlocked.Increment(ref _gateDumpSeq);
            // R450 修正: AOT 下 STJ 反射序列化被禁用 (实测 InvalidOperationException)
            //   ⇒ 手写 JSON 字符串转义 (零反射; 铁律: STJ Source Generator 或不用)
            var line = "{\"seq\":" + seq + ",\"len\":" + prompt.Length + ",\"sha16\":\"" + sha16 + "\",\"prompt\":\""
                       + JsonEscape(prompt) + "\"}\n";
            // R450: UTF8 必须显式 no-BOM —— `Encoding.UTF8` 建文件时会写 BOM, 下游 JSONL 解析器会炸
            System.IO.File.AppendAllText(path, line, new System.Text.UTF8Encoding(false));
        }
        catch (Exception ex)
        {
            _dumpLogger?.LogWarning(ex, "R450: 门判 prompt 落盘失败 (已忽略, 不影响决策)");
        }
    }

    private static Microsoft.Extensions.Logging.ILogger? _dumpLogger;
    private static int _gateDumpSeq;

    /// <summary>R450: 零反射 JSON 字符串转义 (AOT 安全; 覆盖 \" \\ 与 &lt;0x20 控制字符)。</summary>
    internal static string JsonEscape(string s)
    {
        var sb = new System.Text.StringBuilder(s.Length + 8);
        foreach (var c in s)
        {
            switch (c)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                default:
                    if (c < 0x20)
                        sb.Append("\\u").Append(((int)c).ToString("x4"));
                    else
                        sb.Append(c);
                    break;
            }
        }
        return sb.ToString();
    }

    public async Task<TurnGateOutcome> JudgeTurnAsync(string userMessage, string? roleSeed, string? growthBlock, CancellationToken ct = default)
    {
        var port = _localPort;
        if (port is null)
        {
            TurnGate.RecordDegraded("no_local_port");
            return TurnGateOutcome.Undecided("no_local_port");
        }
        TurnGate.RecordJudged();
        TurnGate.RecordRoleSeed(roleSeed);   // R430: 先记种子指纹 (区分「种子漂移」与「引擎不确定」)
        // R431: prompt 只构造一次 —— 形状读数取自实发文本 (二次重建会与真发内容漂移)。
        var gatePrompt = TurnGateJudge.BuildPrompt(userMessage, roleSeed, growthBlock);
        TurnGate.RecordPromptShape(gatePrompt.Length, roleSeed?.Length ?? 0, growthBlock);
        DumpGatePrompt(gatePrompt);   // R450: 门判实发 prompt 落盘闸 (默认关 ⇒ 现网零变更)
        try
        {
            var outcome = await port.GenerateAsync(new LocalGenerationRequest
            {
                SessionKey = "r413:turn-gate",
                TurnIndex = 1,
                Turns = new List<LocalChatTurn> { new("user", gatePrompt) },
                // R413 实测: 8/16 token 会被 r1 思考链吃光 ⇒ 字母没出来 (raw 取证)。128 足够判别句收尾。
                MaxTokens = 512,   // 实测: 真链里思考链可达 250-350 tok (192 会截断在推理中途) ⇒ 给足上限, 解析只认闭合标记后的结论区
                // R429: 决策路径钉死缓存态 —— 同一 prompt 在「全量评估」与「部分前缀复用」下 token 序列不等
                // (传输级实测 180/97/215, 可致 S/P 翻转) ⇒ 门判不得依赖前缀缓存复用。
                CacheReuse = false,
            }, ct).ConfigureAwait(false);
            TurnGate.RecordCachePinned(outcome.CachedTokens, outcome.PromptSha16, outcome.RequestSha16, outcome.RequestFields,
                outcome.TokensEvaluated, outcome.PromptNewTokens, outcome.GeneratedTokens);

            if (!outcome.Success || string.IsNullOrWhiteSpace(outcome.Content))
            {
                TurnGate.RecordDegraded("failed_or_empty");
                return TurnGateOutcome.Undecided(outcome.Error ?? "empty_content", outcome.Content ?? string.Empty);
            }
            if (!outcome.AccountingConsistent)
            {
                TurnGate.RecordAccountingViolation("tokens_evaluated != prompt_n + cache_n");
                return TurnGateOutcome.Undecided("accounting_inconsistent", outcome.Content ?? string.Empty);
            }

            var verdict = TurnGateJudge.Parse(outcome.Content);
            if (!verdict.Decided)
            {
                TurnGate.RecordDegraded("unparsed:" + (verdict.Raw.Length > 40 ? verdict.Raw[..40] : verdict.Raw));
                return verdict;
            }
            if (verdict.Verdict == TurnGateVerdict.Skip) TurnGate.RecordSkipped();
            else TurnGate.RecordPassed();
            return verdict;
        }
        catch (OperationCanceledException) { throw; }
        catch (Exception ex)
        {
            TurnGate.RecordDegraded("exception:" + ex.GetType().Name);
            return TurnGateOutcome.Undecided("exception:" + ex.GetType().Name);
        }
    }

    /// <summary>
    /// R426: 关系判官 (CorrectionDetector L2 微判定) 本地优先 —
    /// 本地端口已注册 且 配置 <c>local.relation_judge=true</c> (默认 false ⇒ 零回归)。
    /// </summary>
    public bool RelationJudgeEnabled => _localPort is not null && _catalog.LocalChannel.RelationJudge;

    /// <summary>R426: 关系判官计数/依据 (可观测: Local==0 ∧ Fallback&gt;0 ⇒ 本地未生效, 不靠猜)。</summary>
    public RelationJudgeCounters RelationJudge { get; } = new();

    /// <summary>
    /// R426: 本地关系判官 (r1)。<c>null</c> ⇒ 本地不可用/失败/记账违规/未解析出字母 ⇒
    /// 调用方**必须远端兜底** (绝不静默给结论)。
    ///
    /// 预算: 调用方 (CorrectionDetector) 给远端的是 64/128 tok — 那是远端 API 的保守值;
    /// r1 的思考链会把 64 tok 吃光 (R413 实测: 8/16 tok 截断在推理中途 ⇒ 恒未判定),
    /// 故本地**不复用**调用方预算而用 512 (与前置门同值, 实测思考链 250–350 tok)。
    /// 取消: 本路径由后台赏罚任务调用 (与远端同语义: 不随单轮 ct 取消, 否则会静默降级成 NEUTRAL)。
    /// </summary>
    public async Task<RelationJudgeOutcome?> JudgeRelationLocalAsync(
        string systemPrompt, string judgePrompt, CancellationToken ct = default)
    {
        var port = _localPort;
        if (port is null)
        {
            RelationJudge.RecordFallback("no_local_port");
            return null;
        }
        var cfg = _catalog.LocalChannel;
        // R435: 预算**保持 512** —— 实测证伪了「512 不够」的假设 (且不是承重变量):
        //   旧 prompt: 512 → 1/7 (turn5/8 思考链未闭合耗尽), 1024 → 2/7, 且 turn5 在 1024 仍耗尽
        //   ⇒ 加预算只换来 1 例、还让最坏延迟翻倍 (turn1: 32s → 86s)。
        //   新 prompt: 512 与 1024 **逐例完全同解** (6/7, 同字母) ⇒ 一旦结论区形状对了, 512 足够。
        //   证据: eval/rover/r435/probe-j2-classified.json (A0/A2/A1/A3)。
        var maxTokens = Math.Max(cfg.MaxTokens, 512);

        RelationJudge.RecordAttempt();
        try
        {
            var turns = new List<LocalChatTurn>();
            if (!string.IsNullOrEmpty(systemPrompt))
                turns.Add(new LocalChatTurn("system", systemPrompt));
            turns.Add(new LocalChatTurn("user", judgePrompt));

            var outcome = await port.GenerateAsync(new LocalGenerationRequest
            {
                SessionKey = "r426:relation-judge",
                TurnIndex = 1,
                Turns = turns,
                MaxTokens = maxTokens,
                // R429: 关系判官同为决策路径 ⇒ 同样钉死缓存态。
                CacheReuse = false,
            }, ct).ConfigureAwait(false);
            RelationJudge.RecordCachePinned();

            if (!outcome.Success || string.IsNullOrWhiteSpace(outcome.Content))
            {
                RelationJudge.RecordFallback("failed_or_empty");
                return null;
            }
            if (!outcome.AccountingConsistent)
            {
                RelationJudge.RecordAccountingViolation("tokens_evaluated != prompt_n + cache_n");
                return null;
            }
            if (!RelationLetterJudge.TryNormalize(outcome.Content, out var letter, out var parseReason))
            {
                // R435: 失败原因入计数 (可机检归因; R434 只能看到「降级了」, 看不到为什么)
                RelationJudge.RecordFallback("unparsed:" + parseReason);
                return null;
            }

            RelationJudge.RecordLocal(letter);
            return new RelationJudgeOutcome(letter, outcome.Content ?? string.Empty, outcome.GeneratedTokens,
                outcome.TokensEvaluated, outcome.PromptNewTokens);
        }
        catch (OperationCanceledException) { throw; }
        catch (Exception ex)
        {
            RelationJudge.RecordFallback("exception:" + ex.GetType().Name);
            return null;
        }
    }

    /// <summary>被跳过轮的本地回复 (本地生成; 失败 → 固定兜底串, 保持"有回复"不变式)。</summary>
    /// <summary>
    /// R413: 被跳过轮的回复 —— **非 LLM 模板** (确定性、零 token、零延迟)。
    ///
    /// 为什么不本地生成: 真机实证 (2026-09-14 臂B) — 让 r1 生成"确认语"会退化:
    /// turn4 用户说「收到，谢谢。」它回「收到，谢谢。测试命令是什么？」(复读前文并反问),
    /// turn6 用户说「嗯。」它回「测试命令是什么？」。纯确认轮不含新信息, 生成没有信息可加,
    /// 只会引入幻觉; 模板串既安全又可机检 (用户 OOB 口径: 本地匹配 → 非 LLM 修/组装)。
    /// </summary>
    public Task<string> ComposeLocalSkipReplyAsync(string userMessage, CancellationToken ct = default)
    {
        TurnGate.RecordTemplateAck();
        return Task.FromResult(LocalSkipFallback);
    }

    /// <summary>被跳过轮的回复模板 (非 LLM; 保证"有回复"不变式, 且不新增任何内容)。</summary>
    public const string LocalSkipFallback = "收到，继续按当前方向推进，本轮不重新规划。";

    /// <summary>当前手动覆盖模型 id (null = auto 自动选模模式) — /model 指令与 /status 展示</summary>
    public string? ManualOverride => _manualOverride;

    /// <summary>v0.10.0: 最近一次余额不足提示 (model:xxx flags:余额不足 协议 — 前端展示用)</summary>
    public string? LastBalanceFlag { get; private set; }

    /// <summary>模型目录 (只读暴露: /model list 序号化列表的数据源)</summary>
    public ModelCatalog Catalog => _catalog;

    /// <summary>当前活跃模型条目 (null = 目录空)</summary>
    public ModelCatalogEntry? ActiveModel
    {
        get
        {
            lock (_lock)
            {
                return _catalog.Find(_manualOverride ?? _activeModelId) ?? _catalog.Models.FirstOrDefault();
            }
        }
    }

    /// <summary>手动指定模型 (返回 false = 目录无此 id); id="auto" 恢复自动</summary>
    public bool SetManualOverride(string? modelId)
    {
        lock (_lock)
        {
            if (modelId is null || modelId.Equals("auto", StringComparison.OrdinalIgnoreCase))
            {
                if (_manualOverride != null)
                    Switches.Add(new ModelSwitchRecord
                        { From = _manualOverride, To = "auto", Reason = "manual" });
                _manualOverride = null;
                _activeModelId = null; // 清粘性: auto = 完全回到自动 (粘性只在失败切换时重建)
                _consecutiveFailures = 0;
                return true;
            }
            var entry = _catalog.Find(modelId);
            if (entry is null)
                return false;
            var prev = _manualOverride ?? _activeModelId ?? "(auto)";
            _manualOverride = entry.Id;
            _activeModelId = entry.Id;
            _consecutiveFailures = 0;
            Switches.Add(new ModelSwitchRecord { From = prev, To = entry.Id, Reason = "manual" });
            LastSelectionBasis = $"manual:{entry.Id}";
            return true;
        }
    }

    /// <summary>
    /// R413: 本地生成尝试。成功 → 直接可用的 <see cref="QueueResponse"/>; 失败/空回/记账违规 → null (调用方降级远端)。
    /// 纪律: 取消必须上抛 (绝不把取消当降级); 空内容不得当成功; 记账恒等 (tokens_evaluated == prompt_n + cache_n)
    /// 不成立 ⇒ 结果**不采信** (R411 口径, 防"自算错而自洽")。
    /// </summary>
    private async Task<QueueResponse?> TryLocalAsync(QueuePrompt prompt, TaskKindHint kind, CancellationToken ct)
    {
        var port = _localPort!;
        var cfg = _catalog.LocalChannel;

        var turns = new List<LocalChatTurn>();
        if (!string.IsNullOrEmpty(prompt.SystemPrompt))
            turns.Add(new LocalChatTurn("system", prompt.SystemPrompt));
        if (!string.IsNullOrEmpty(prompt.ContextPrompt))
            turns.Add(new LocalChatTurn("system", prompt.ContextPrompt));
        foreach (var h in prompt.History)
            turns.Add(new LocalChatTurn(h.Role, h.Content));
        turns.Add(new LocalChatTurn("user", prompt.UserMessage));

        var request = new LocalGenerationRequest
        {
            SessionKey = prompt.SessionId,
            TurnIndex = prompt.TurnIndex <= 0 ? 1 : prompt.TurnIndex,
            Turns = turns,
            MaxTokens = cfg.MaxTokens > 0 ? cfg.MaxTokens : 256,
        };

        LocalChannel.RecordAttempt();
        LocalGenerationOutcome outcome;
        try
        {
            outcome = await port.GenerateAsync(request, ct).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception ex)
        {
            LocalChannel.RecordDegrade($"exception:{ex.GetType().Name}");
            LocalChannelLastBasis = $"local:degraded:exception:{ex.GetType().Name}→remote";
            _logger.LogWarning("ModelQueue: 本地生成异常 ({Kind}) → 降级远端: {Msg}", kind, ex.Message);
            return null;
        }

        if (!outcome.Success)
        {
            LocalChannel.RecordDegrade(outcome.Error ?? "failed");
            LocalChannelLastBasis = $"local:degraded:{outcome.Error ?? "failed"}→remote";
            return null;
        }

        if (string.IsNullOrWhiteSpace(outcome.Content))
        {
            // 空回不是成功 (本地小模型静默空输出的真实失效形态)
            LocalChannel.RecordDegrade("empty_content");
            LocalChannelLastBasis = "local:degraded:empty_content→remote";
            return null;
        }

        if (!outcome.AccountingConsistent)
        {
            var reason = $"tokens_evaluated({outcome.TokensEvaluated}) != prompt_n({outcome.PromptNewTokens}) + cache_n({outcome.CachedTokens})";
            LocalChannel.RecordAccountingViolation(reason);
            LocalChannelLastBasis = "local:degraded:accounting_inconsistent→remote";
            _logger.LogWarning("ModelQueue: 本地记账恒等违规 → 结果不采信, 降级远端: {Reason}", reason);
            return null;
        }

        LocalChannel.RecordSuccess();
        LocalChannelLastBasis = $"local:ok:{port.BackendId}";
        LastSelectionBasis = $"local:{port.BackendId}";
        return new QueueResponse
        {
            Content = outcome.Content,
            Success = true,
            Model = string.IsNullOrEmpty(outcome.Model) ? $"local:{port.BackendId}" : outcome.Model,
            PromptTokens = outcome.TokensEvaluated,
            TokensUsed = outcome.TokensEvaluated + outcome.GeneratedTokens,
            CacheHitTokens = outcome.CachedTokens,
            CacheMissTokens = outcome.PromptNewTokens,
        };
    }

    public async Task<QueueResponse> CallAsync(QueuePrompt prompt, TaskKindHint kind, string intent, CancellationToken ct = default)
    {
        // R413: 本地生成通道 (计划节点: 重新整理所有能力 → 精炼合理化链管道 → 提高 KPI)。
        // R351 (用户钦定) 移除的是**旧的「本地 LLM 使用」路径** (全走远端 API), 与本通道无关 —
        // 新增 r1 本地生成是计划内节点 (用户 2026-09-14 口径纠正)。
        // 判据 (预注册): 通道就绪 ∧ 非带图 ∧ 种类允许 ∧ prompt 不超限 ∧ 端口真实可用。
        var localDecision = LocalChannelPolicy.Evaluate(prompt, kind, _catalog.LocalChannel, _localPort);
        if (localDecision.Allowed)
        {
            var local = await TryLocalAsync(prompt, kind, ct).ConfigureAwait(false);
            if (local is not null)
                return local;
            // 失败/记账违规 ⇒ 已计数并落 LocalChannelLastBasis, 继续走远端 (降级永不静默)
        }
        else
        {
            LocalChannel.RecordReject(localDecision.ReasonText);
            LocalChannelLastBasis = $"local:rejected:{localDecision.ReasonText}";
        }

        // R351 (用户钦定): 旧的本地 LLM 推理通道移除 — 远端调用全部经 API (远端目录)。
        // 需求1 混合调度: 手动/粘性优先 → 通道优先级 (远端目录)
        var sticky = _catalog.Find(_manualOverride ?? _activeModelId);
        var entry = sticky
                    ?? _policy.Select(null, kind, intent,
                        prompt.EstimatedTokens, prompt.EstimatedTokens / 3, _catalog)
                    ?? SelectByChannelPriority(kind, intent, prompt.EstimatedTokens);
        // R356-c: 选模依据实时可观测 (snapshot/state 消费; sticky 命中原来不更新 → 恒显 init)
        LastSelectionBasis = sticky is not null
            ? $"sticky:{entry!.Id}"
            : $"auto:{entry?.Id ?? "(none)"}";
        if (entry is null)
        {
            return new QueueResponse
            {
                Success = false,
                Error = "模型目录为空: 请在 config/base/models.yaml 配置至少一个模型",
            };
        }

        // v0.12.0 A3 (真缺陷 64): 带图请求必须落在 image_input 模型 —
        // 手动/粘性/策略选中 text-only 模型 (glm-4-plus/deepseek 等) 时重路由到首个可用视觉模型
        // (视觉模型 key 可用性同 policy 判据; 无视觉候选 → 保持原 entry, 让 API 错误如实暴露)。
        if (prompt.ImageUrls.Count > 0 && !entry.Capabilities.ImageInput)
        {
            var vision = _catalog.Models.FirstOrDefault(m =>
                m.Capabilities.ImageInput &&
                (m.ApiKeyEnv is null ||
                 !string.IsNullOrEmpty(Environment.GetEnvironmentVariable(m.ApiKeyEnv))));
            if (vision is not null)
            {
                Switches.Add(new ModelSwitchRecord
                    { From = entry.Id, To = vision.Id, Reason = "vision_required" });
                LastSelectionBasis = $"vision_required:{vision.Id} (原 {entry.Id} 无 image_input, 带图请求)";
                _logger.LogWarning("ModelQueue: {From} 无 image_input 且请求带图 → 重路由 {To}", entry.Id, vision.Id);
                entry = vision;
            }
        }

        // v0.11.0 R115 (真缺陷 43): TokenUsageService.InitializeAsync 此前无调用点 — 余额快照
        // 恒空 → EstimateBalance 恒 (null,true) → MIN_BALANCE 阈值切模整条链路死代码。
        // 惰性 fire-once 启动同步 (后台, 不阻断首调用; 失败静默走"余额未知不判定"语义)。
        if (_tokenUsage is not null)
        {
            var syncTask = _balanceSyncOnce.EnsureStartedAsync(_tokenUsage);
            try { await syncTask.WaitAsync(TimeSpan.FromSeconds(3), ct).ConfigureAwait(false); }
            catch (TimeoutException) { /* 首同步 >3s 不阻断对话, 本轮按余额未知处理 */ }
        }

        // v0.10.0: 余额预估检查 — 不足 → 切换其他模型 + flags:余额不足 提示
        if (_tokenUsage is not null)
        {
            var (remaining, sufficient) = _tokenUsage.EstimateBalance(entry.Provider, prompt.EstimatedTokens);
            if (!sufficient)
            {
                var alt = SelectAlternativeByBalance(entry, prompt.EstimatedTokens);
                if (alt is not null && alt.Id != entry.Id)
                {
                    Switches.Add(new ModelSwitchRecord
                        { From = entry.Id, To = alt.Id, Reason = "insufficient_balance" });
                    _activeModelId = alt.Id;
                    LastSelectionBasis = $"balance_fallback:{alt.Id} ({entry.Id} 余额不足)";
                    LastBalanceFlag = $"model:{alt.Id} flags:余额不足 (原 {entry.Id} 预估余额 ${remaining:F2})";
                    _logger.LogWarning("ModelQueue: {From} 余额不足 (${Remain:F2}) → 切换 {To}",
                        entry.Id, remaining ?? 0, alt.Id);
                    entry = alt;
                }
                else
                {
                    // 无备选 → 继续原模型但带上提示
                    LastBalanceFlag = $"model:{entry.Id} flags:余额不足 (预估剩余 ${remaining:F2}, 无备选继续)";
                    _logger.LogWarning("ModelQueue: {Id} 余额不足但无备选 — 继续原模型", entry.Id);
                }
            }
        }

        // v0.11.0 R129 (PGO v2 D3): 热路径计时 — llm_call 真耗时 (成功/失败均打), 与 wall 的差值
        // 即排队/路由开销; 依据 assembly 打点既有 ms 风格 (IndustrialAgentV2.cs:383)。
        var llmSw = System.Diagnostics.Stopwatch.StartNew();
        try
        {
            // R373: 首轮预算按任务类型给足 (真机 D1/D7 同源根因: 推理与正文共享 max_tokens)
            var firstBudget = InitialMaxTokens(kind, intent);
            var resp = await CallEntryAsync(entry, prompt, ct, firstBudget).ConfigureAwait(false);
            // R371 真缺陷 (空正文): 推理模型把输出预算全花在思维链 → content 空但 success=true,
            // 用户侧表现为"执行 ~30s 后回复空白" (E2E 铁证: completion 8192/8192, content_len=0, reasoning_len=22633,
            // loop_turn reply_chars=0 且 success=true)。旧修 (R19: max_tokens 2000→8192) 只是抬高天花板 —
            // 推理可吃满任意上限 → 改为"检测 + 有界恢复 + 诚实降级"。
            if (string.IsNullOrWhiteSpace(resp.Content) && !string.IsNullOrWhiteSpace(resp.ReasoningContent))
                resp = await RecoverFromEmptyContentAsync(entry, prompt, resp, ct).ConfigureAwait(false);
            // R371 D7 真缺陷 (真机 RUN3 实证): 正文被输出预算**截断** (completion=8192 上限, content=1209 字符,
            // 断在 `start_len: int =` 的半行) 却 success=true → 用户拿到半份实现, 且 artifact 命中率看起来只是"抖动"。
            // 判据纯语法 (与模型无关): 尾部是未完结构 (= ( [ { , + - * / \ : 或未闭合三引号/围栏)。
            // 处置: 有界**续写一次** (升预算 + 明确断点提示) → 去重重拼; 失败则保留原文 (绝不假装完整)。
            if (LooksTruncated(resp.Content))
                resp = await RecoverFromTruncatedAsync(entry, prompt, resp, ct).ConfigureAwait(false);
            llmSw.Stop();
            lock (_lock)
            {
                _consecutiveFailures = 0;
                // v0.11.0 R89 (真缺陷 36): auto 选模成功后同步粘性 id — 原 _activeModelId 只在
                // failover/手动切换时更新, /model 与 /balance 查询时 ActiveModel getter
                // 落到目录首项 (gpt-4o), 与实际调用模型 (glm) 不一致 (真机 /model 实证)。
                if (_manualOverride is null) _activeModelId = entry.Id;
            }
            // v0.10.0: 用量本地累计
            _tokenUsage?.RecordUsage(resp.Model, entry.Provider, resp.PromptTokens, resp.CompletionTokens);
            // R377: prompt 缓存命中率 KPI (未上报 → -1, 与"命中 0"区分)
            var cacheKv = PromptCacheKpi.Fields(resp.CacheHitTokens, resp.CacheMissTokens);
            // R380 (用户钦定**口径修订**, 首要 KPI): 命中率只算"需要命中的部分" —— 本轮新增不计入
            //  (新增是首次发送, 必然不命中; 计入分母会把"前缀复用度"与"本轮新发量"混为一谈 → 指标被稀释)。
            //  有效命中率 = hit / min(本轮 prompt, 上一轮已发 prompt); 会话首轮无"需要命中"部分 → -1。
            var sessKey = prompt.SessionId ?? string.Empty;
            var lastPrompt = 0;
            if (sessKey.Length > 0 && _lastPromptTokens.TryGetValue(sessKey, out var lp)) lastPrompt = lp;
            var effKv = PromptCacheKpi.EffectiveFields(resp.CacheHitTokens, resp.PromptTokens, LastPromptTokensFor(sessKey));
            var effRate = (double)(effKv[1].Value ?? -1d);
            agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                ("model", entry.Id), ("provider", entry.Provider),
                // R379: 逐轮归属 (红线判据: 多轮第 2 轮起命中率 ≥ PromptCacheRedline.Threshold, 现 97%) — 无此字段则无法把 KPI 追到"第几轮"
                ("agent_session", prompt.SessionId ?? ""), ("turn", prompt.TurnIndex),
                ("prompt_tokens", resp.PromptTokens), ("completion_tokens", resp.CompletionTokens),
                ("total_tokens", resp.TokensUsed), ("success", resp.Success),
                ("empty_reply", string.IsNullOrEmpty(resp.Content)),
                ("error_kind", resp.Error ?? ""),
                // v0.11.0 R19: 内容长度诊断 (C03 曾现 completion 2000 tok 但回复渲染空 — 定位内容丢在链路哪段)
                ("content_len", resp.Content?.Length ?? 0),
                // v0.21.1: 推理模型思考链长度诊断 (reasoning_content 是否被真实返回 / 占多少)
                ("reasoning_len", resp.ReasoningContent?.Length ?? 0),
                // R371 D7: 每次调用都记录是否**结构未闭合** (截断) — 无此字段, "半份实现"只能靠人肉看输出才发现
                ("truncated", LooksTruncated(resp.Content)),
                // R373 归因铁律 (R372 教训): 命中/失败必须能追溯到**机制** — 记录首轮预算与意图,
                // 否则"预算策略是否真生效"又只能靠猜 (本轮真机首跑即踩: 适配器硬编码 intent 使策略成死代码)。
                ("first_budget", firstBudget), ("intent", intent ?? ""),
                // v0.11.0 R129 (D3): LLM 真耗时 ms
                ("ms", llmSw.ElapsedMilliseconds),
                cacheKv[0], cacheKv[1], cacheKv[2], effKv[0], effKv[1]);
            // R380 (+R379 逐轮归属) 红线闸门 —— 用户逐字: "一旦越过红线必然检查问题为什么发生并修复"。
            // 越线不得只记数字: 必须同时落盘**可执行诊断**(按 R379 实测四类破坏点排序) + 响亮告警。
            if (sessKey.Length > 0)
            {
                if (_lastPromptTokens.Count > 512) _lastPromptTokens.Clear();   // 有界: 防长驻进程无界增长
                _lastPromptTokens[sessKey] = resp.PromptTokens;
            }
            var cacheable = (int)(effKv[0].Value ?? 0);
            if (PromptCacheRedline.Violated(prompt.TurnIndex, cacheable, effRate))
            {
                var diag = PromptCacheRedline.Diagnose(prompt.TurnIndex, resp.PromptTokens, cacheable,
                    PromptCacheKpi.HitTokens(resp.CacheHitTokens), PromptCacheKpi.MissTokens(resp.CacheMissTokens), lastPrompt);
                _logger.LogWarning("ModelQueue: prompt 缓存红线越线 — {Diag}", diag);
                agent.config.AgentTelemetry.Emit("cache_redline_violation", "ModelQueueRouter",
                    ("agent_session", sessKey), ("turn", prompt.TurnIndex),
                    ("effective_hit_rate", effRate), ("cacheable_tokens", cacheable),
                    ("hit", PromptCacheKpi.HitTokens(resp.CacheHitTokens)),
                    ("miss", PromptCacheKpi.MissTokens(resp.CacheMissTokens)),
                    ("prompt_tokens", resp.PromptTokens), ("last_prompt_tokens", lastPrompt),
                    ("threshold", PromptCacheRedline.Threshold), ("diagnosis", diag));
            }
            // 阈值再同步 (fire-and-forget, 不阻塞主链)
            if (_tokenUsage is not null && _tokenUsage.NeedsResync(entry.Provider))
                _ = _tokenUsage.TryResyncAsync(entry.Provider, CancellationToken.None);
            return resp;
        }
        catch (HttpRequestException ex)
        {
            llmSw.Stop();
            agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                ("model", entry.Id), ("provider", entry.Provider), ("success", false), ("error_kind", "http"), ("error", ex.Message),
                ("ms", llmSw.ElapsedMilliseconds));
            return await OnTransientFailureAsync(entry, prompt, kind, intent, ct, $"网络错误: {ex.Message}").ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            // HttpClient 超时 (非用户取消) = 瞬态
            llmSw.Stop();
            agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                ("model", entry.Id), ("provider", entry.Provider), ("success", false), ("error_kind", "timeout"),
                ("ms", llmSw.ElapsedMilliseconds));
            return await OnTransientFailureAsync(entry, prompt, kind, intent, ct, "请求超时").ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            // 用户取消永不触发模型切换 (C.4 验收)
            throw;
        }
    }

    private async Task<QueueResponse> OnTransientFailureAsync(
        ModelCatalogEntry entry, QueuePrompt prompt, TaskKindHint kind, string intent,
        CancellationToken ct, string why, int attempt = 1)
    {
        // v0.11.0 R23 修复 (真 bug 21): 原"连续失败"计数跨请求, 单请求瞬态失败 (超时/网络抖动)
        // 直接报错给用户且从不切备 — failover 名存实亡 (实测 C03 三子任务超时 101s 后空手而归)。
        // 现策略: 同请求内 ①同模型重试 1 次 (attempt 1→2) ②仍败切备选模型重试 1 次 ③备选也败才返回失败。
        if (attempt <= 2)
        {
            // v0.13.3 R242 (KPI-2 优化①, audit 数据驱动): 429 限流 = 速率窗口问题, 窗口内同模型
            // 重试必再 429 (直探 429/20s 交替实证) 且重发全 prompt (~1000 tok/次浪费, KPI-2 报告:
            // C07 2355 tok 中 ~1000 是重试链)。改为: 429 跳过同模型重试直接进切备链 —
            // 备模型不同 key/端点, 不受该窗口影响。非 429 瞬态 (网络/超时) 仍同模型重试。
            if (why.Contains("429") || why.Contains("Too Many Requests"))
            {
                agent.config.AgentTelemetry.Emit("llm_retry", "ModelQueueRouter",
                    ("model", entry.Id), ("attempt", attempt), ("why", why), ("skipped", true));
                return await OnTransientFailureAsync(entry, prompt, kind, intent, ct, why + " (429 跳过同模型重试)", attempt + 2)
                    .ConfigureAwait(false);
            }
            _logger.LogWarning("ModelQueue: {Model} 瞬态失败 ({Why}) — 请求内重试 {Attempt}/2", entry.Id, why, attempt);
            agent.config.AgentTelemetry.Emit("llm_retry", "ModelQueueRouter",
                ("model", entry.Id), ("attempt", attempt), ("why", why));
            try
            {
                // v0.12.0 R223 (真缺陷 65): 请求内重试成功路径此前不补 llm_call 打点 —
                // bigmodel 429/瞬态 首调失败→重试成功时, telemetry 只剩失败点 (ms≈200/tokens=0),
                // KPI tok/case 被系统性低估 (批187 实测 7/9 用例首调 429 → 126/case 假性 KPI_BREACH)。
                // 补成功打点 (attempt=2) — 用量/耗时/模型三观与主成功路径对齐。
                var retrySw = System.Diagnostics.Stopwatch.StartNew();
                var retried = await CallEntryAsync(entry, prompt, ct).ConfigureAwait(false);
                retrySw.Stop();
                if (retried.Success)
                {
                    lock (_lock) _consecutiveFailures = 0;
                    LastSelectionBasis = $"retry_ok:{entry.Id} (attempt {attempt + 1})";
                    _tokenUsage?.RecordUsage(retried.Model, entry.Provider, retried.PromptTokens, retried.CompletionTokens);
                    var cacheKv = PromptCacheKpi.Fields(retried.CacheHitTokens, retried.CacheMissTokens);
                    // R380: 重试路径同样只算"需要命中的部分" (否则 KPI 漏掉重试调用)
                    var effKv = PromptCacheKpi.EffectiveFields(retried.CacheHitTokens, retried.PromptTokens, LastPromptTokensFor(prompt.SessionId));
                    agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                        ("model", entry.Id), ("provider", entry.Provider),
                        ("prompt_tokens", retried.PromptTokens), ("completion_tokens", retried.CompletionTokens),
                        ("total_tokens", retried.TokensUsed), ("success", true),
                        ("content_len", retried.Content?.Length ?? 0),
                        ("reasoning_len", retried.ReasoningContent?.Length ?? 0),
                        ("ms", retrySw.ElapsedMilliseconds), ("attempt", attempt + 1),
                        cacheKv[0], cacheKv[1], cacheKv[2], effKv[0], effKv[1]);
                    return retried;
                }
                // 软失败 (Success=false 但未抛异常) 也算本次失败, 继续走切备
                return await OnTransientFailureAsync(entry, prompt, kind, intent, ct,
                    retried.Error ?? "重试仍失败", attempt + 1).ConfigureAwait(false);
            }
            catch (HttpRequestException ex2)
            {
                return await OnTransientFailureAsync(entry, prompt, kind, intent, ct, $"重试网络错误: {ex2.Message}", attempt + 1).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (!ct.IsCancellationRequested)
            {
                return await OnTransientFailureAsync(entry, prompt, kind, intent, ct, "重试超时", attempt + 1).ConfigureAwait(false);
            }
        }

        // 重试耗尽 → 切备选模型链 (v0.13.1 F1 用户钦定: 存在备选时启用兜底服务,
        // 逐个按性价比序 (cost_quality=auto 同源判据: 质量档降序, 同档低价优先; catalog=旧目录序)
        // 失败兜底, 每个兜底回复过 FallbackConfig.VerifyReply 校验; 校验失败继续链内下一个 —
        // 最多 PerRequestMaxFallbacks 个。capability 硬过滤语义不变 (R226 文本优先 / R227 硬过滤)。
        lock (_lock) _consecutiveFailures++;
        List<ModelCatalogEntry> backupChain;
        lock (_lock)
        {
            var candidates = _catalog.Models.Where(m =>
                !string.Equals(m.Id, entry.Id, StringComparison.OrdinalIgnoreCase) &&
                (prompt.ImageUrls.Count > 0 ? m.Capabilities.ImageInput : m.Capabilities.Text) &&
                (m.ApiKeyEnv is null ||
                 !string.IsNullOrEmpty(Environment.GetEnvironmentVariable(m.ApiKeyEnv))));
            if (string.Equals(_fallback.Order, "cost_quality", StringComparison.OrdinalIgnoreCase))
                candidates = candidates
                    .OrderByDescending(m => m.Capabilities.ImageInput == false)
                    .ThenByDescending(m => m.ReasoningScore + m.CodingScore)
                    .ThenBy(m => m.PriceInPerM + m.PriceOutPerM);
            backupChain = candidates.Take(_fallback.PerRequestMaxFallbacks).ToList();
        }
        QueueResponse? lastFail = null;
        foreach (var backup in backupChain)
        {
            var attemptN = backupChain.IndexOf(backup) + 1;
            _logger.LogWarning("ModelQueue: {From} 重试耗尽 → 切备 {To} (兜底链 {N}/{Max})",
                entry.Id, backup.Id, attemptN, backupChain.Count);
            agent.config.AgentTelemetry.Emit("fallback_attempt", "ModelQueueRouter",
                ("from", entry.Id), ("to", backup.Id),
                ("attempt_n", attemptN), ("chain_size", backupChain.Count), ("why", why));
            try
            {
                var backupSw = System.Diagnostics.Stopwatch.StartNew();
                var backupResp = await CallEntryAsync(backup, prompt, ct).ConfigureAwait(false);
                backupSw.Stop();
                // v0.13.1 F1 兜底校验: 失败 = 此备选无效 → 继续下一个 (用户钦定"逐个...兜底"):
                if (_fallback.VerifyReply(backupResp))
                {
                    lock (_lock)
                    {
                        Switches.Add(new ModelSwitchRecord
                            { From = entry.Id, To = backup.Id, Reason = "transient_failover" });
                        _activeModelId = backup.Id;
                        _manualOverride = null;
                        _consecutiveFailures = 0;
                        LastSelectionBasis = $"failover:{backup.Id} (原 {entry.Id} 瞬态失败, 兜底 {attemptN}/{backupChain.Count})";
                    }
                    _tokenUsage?.RecordUsage(backupResp.Model, backup.Provider, backupResp.PromptTokens, backupResp.CompletionTokens);
                    var cacheKv = PromptCacheKpi.Fields(backupResp.CacheHitTokens, backupResp.CacheMissTokens);
                    // R380: 备选 provider 路径同样只算"需要命中的部分"
                    var effKv = PromptCacheKpi.EffectiveFields(backupResp.CacheHitTokens, backupResp.PromptTokens, LastPromptTokensFor(prompt.SessionId));
                    agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                        ("model", backup.Id), ("provider", backup.Provider),
                        ("prompt_tokens", backupResp.PromptTokens), ("completion_tokens", backupResp.CompletionTokens),
                        ("total_tokens", backupResp.TokensUsed), ("success", true),
                        ("content_len", backupResp.Content?.Length ?? 0),
                        ("reasoning_len", backupResp.ReasoningContent?.Length ?? 0),
                        ("ms", backupSw.ElapsedMilliseconds), ("attempt", "failover"),
                        cacheKv[0], cacheKv[1], cacheKv[2], effKv[0], effKv[1]);
                    return backupResp;
                }
                agent.config.AgentTelemetry.Emit("fallback_verify_fail", "ModelQueueRouter",
                    ("model", backup.Id), ("success", backupResp.Success),
                    ("content_len", backupResp.Content?.Length ?? 0));
                lastFail = backupResp.Success ? null : backupResp;
                if (lastFail is null)
                    lastFail = new QueueResponse { Success = false, Error = $"备选 {backup.Id} 回复未通过兜底校验", Model = backup.Id };
            }
            catch (Exception ex3) when (ex3 is HttpRequestException
                || (ex3 is OperationCanceledException oce && !ct.IsCancellationRequested))
            {
                lastFail = new QueueResponse
                {
                    Success = false,
                    Error = $"备选 {backup.Id} 失败: {ex3.Message}",
                    Model = backup.Id,
                };
            }
        }
        if (lastFail is not null)
        {
            // 兜底链耗尽 — 如实返回最后失败 (不降级硬跑):
            return lastFail;
        }

        // v0.11.0 R23: 重试耗尽且无可用备选 — 保守计数后如实返回失败
        lock (_lock)
        {
            _consecutiveFailures++;
            LastSelectionBasis = $"primary:{entry.Id} (重试耗尽, 无可用备选: {why})";
        }
        return new QueueResponse
        {
            Success = false,
            Error = $"模型 {entry.Id} 调用失败 (请求内重试+备选均不可用): {why}",
            Model = entry.Id,
        };
    }

    /// <summary>
    /// v0.10.0 余额不足备选: 同目录排除当前模型, 按 (余额充足, 分数) 选最优。
    /// 本地通道可用 → 本地优先 (无余额概念, 天然充足)。
    /// </summary>
    private ModelCatalogEntry? SelectAlternativeByBalance(ModelCatalogEntry current, int estimatedTokens)
    {
        if (_tokenUsage is null) return null;
        var candidates = _catalog.Models
            .Where(m => !string.Equals(m.Id, current.Id, StringComparison.OrdinalIgnoreCase))
            // v0.11.0 R115 (真缺陷 46): 候选必须 key 已配置 (曾选中 claude-sonnet-4-5 而
            // ANTHROPIC_KEY 未设 → 切换后调用必败, 比不切更糟)
            .Where(m => !string.IsNullOrEmpty(Environment.GetEnvironmentVariable(m.ApiKeyEnv)))
            .Select(m => (Model: m, Est: _tokenUsage!.EstimateBalance(m.Provider, estimatedTokens)))
            .Where(t => t.Est.Sufficient)
            .OrderByDescending(t => t.Model.ReasoningScore + t.Model.CodingScore)
            .ToList();
        return candidates.Count == 0 ? null : candidates[0].Model;
    }

    /// <summary>
    /// 通道优先级选模 (R351: 本地/官方通道移除 — 纯远端目录选优)。
    /// 通道满 (AcquireChannel=null) → 不阻塞主链, 退回目录首模型由其自身失败语义兜底。
    /// </summary>
    private ModelCatalogEntry? SelectByChannelPriority(TaskKindHint kind, string intent, int estimatedTokens)
    {
        var remoteRanked = Scheduler.RankCandidates(_catalog.Models, kind, estimatedTokens);
        if (remoteRanked.Count == 0)
            return null;
        LastSelectionBasis = $"channel:remote:{remoteRanked[0].Model.Id}";
        return remoteRanked[0].Model;
    }

    /// <summary>按目录条目真实调用 OpenAI 兼容 chat completions (endpoint/keyEnv 来自目录)</summary>

    /// <summary>
    /// v0.12.0 A2: 请求序列化 — 无 parts 走 source-gen (原路); 任一消息 HasParts → 手写
    /// Utf8JsonWriter 输出 parts[] 形态 (source-gen 对 union 不友好, 手写 AOT 安全)。
    /// </summary>
    internal static string SerializeChatRequest(QueueChatRequest request)
    {
        // R456: 工具声明/回灌消息必须走手写 writer (source-gen DTO 不含这两个字段);
        // 无工具请求仍走 source-gen ⇒ 与旧版逐字节相同 (缓存前缀不受影响)。
        var manual = !string.IsNullOrEmpty(request.ToolsJson) || request.Messages.Any(m => m.HasParts || m.HasToolPayload);
        if (!manual)
            return JsonSerializer.Serialize(request, ModelQueueJsonContext.Default.QueueChatRequest);
        using var ms = new System.IO.MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartObject();
            w.WriteString("model", request.Model);
            w.WritePropertyName("messages");
            w.WriteStartArray();
            foreach (var m in request.Messages)
            {
                w.WriteStartObject();
                w.WriteString("role", m.Role);
                if (m.HasParts)
                {
                    w.WritePropertyName("content");
                    w.WriteStartArray();
                    foreach (var p in m.ContentParts!)
                    {
                        w.WriteStartObject();
                        w.WriteString("type", p.Type);
                        if (p.Type == "text")
                            w.WriteString("text", p.Text ?? string.Empty);
                        else if (p.Type == "image_url" && p.ImageUrl != null)
                        {
                            w.WritePropertyName("image_url");
                            w.WriteStartObject();
                            w.WriteString("url", p.ImageUrl.Url);
                            w.WriteEndObject();
                        }
                        w.WriteEndObject();
                    }
                    w.WriteEndArray();
                }
                else if (m.ToolCalls is { Count: > 0 })
                {
                    // assistant 请求工具: content 省略 (协议允许), 只带 tool_calls
                }
                else
                {
                    w.WriteString("content", m.Content);
                }
                if (m.ToolCalls is { Count: > 0 })
                {
                    w.WritePropertyName("tool_calls");
                    w.WriteStartArray();
                    foreach (var tc in m.ToolCalls)
                    {
                        w.WriteStartObject();
                        w.WriteString("id", tc.Id);
                        w.WriteString("type", "function");
                        w.WritePropertyName("function");
                        w.WriteStartObject();
                        w.WriteString("name", tc.Name);
                        w.WriteString("arguments", tc.ArgumentsJson);
                        w.WriteEndObject();
                        w.WriteEndObject();
                    }
                    w.WriteEndArray();
                }
                if (!string.IsNullOrEmpty(m.ToolCallId))
                    w.WriteString("tool_call_id", m.ToolCallId);
                w.WriteEndObject();
            }
            w.WriteEndArray();
            if (!string.IsNullOrEmpty(request.ToolsJson))
            {
                w.WritePropertyName("tools");
                w.WriteRawValue(request.ToolsJson, skipInputValidation: true);
            }
            if (!string.IsNullOrEmpty(request.ReasoningEffort))
            {
                w.WriteString("reasoning_effort", request.ReasoningEffort);
            }
            w.WriteEndObject();
        }
        return System.Text.Encoding.UTF8.GetString(ms.ToArray());
    }

    /// <summary>R371: 空正文恢复时的输出预算 (×4 于默认 8192; 硬上限保护, 不是"再抬天花板"而是配合抑制推理)。</summary>
    private const int MaxTokensEscalated = 32768;

    /// <summary>默认输出预算 (与 DTO 默认一致; 只作截断保护, 实际长度由输出纪律约束)。</summary>
    public const int DefaultMaxTokens = 8192;

    /// <summary>
    /// R373 **首轮预算策略** —— D1(空正文)/D7(半正文) 的**同源根因修复**。
    /// 真机铁证: `completion_tokens=8192` 被**推理内容独占** (reasoning_len 22633~28306, content_len=0),
    /// 旧行为 = 首轮 8192 全废 → 触发有界恢复(第 2 次调用 32768) → 同题 2~3 次调用/多花 8192 tok/多等 30~60s。
    /// 正解: **首轮就按任务类型给足预算** (推理 + 完整产物必须同框), 恢复链退化为兜底。
    /// 判据只取**确定性信号** (任务类型 + 意图标签), 不做用户文本关键词猜测 —— 避免把闲聊也抬到 32k。
    /// </summary>
    public static int InitialMaxTokens(TaskKindHint kind, string? intent)
    {
        if (kind != TaskKindHint.General) return DefaultMaxTokens;   // 压缩/标注类任务产物短, 保持 8k
        if (string.IsNullOrWhiteSpace(intent)) return DefaultMaxTokens;
        foreach (var marker in LargeOutputIntentMarkers)
            if (intent.Contains(marker, StringComparison.OrdinalIgnoreCase)) return MaxTokensEscalated;
        return DefaultMaxTokens;
    }

    /// <summary>大产物意图标记 (产物通常含整份文件/脚本 → 推理+正文必须同框)。</summary>
    private static readonly string[] LargeOutputIntentMarkers =
        { "code", "coding", "script", "program", "game", "implement", "refactor", "artifact" };

    /// <summary>R371: 抑制推理、强制正文的提示 (模型无关表述, 追加为 system 消息)。</summary>
    private const string NoReasoningNudge =
        "[系统] 直接输出最终答案正文本身, 不要输出思考/推理过程 (推理会占满输出预算, 导致正文为空)。";

    /// <summary>
    /// R371 空正文恢复 (真缺陷修复): 首次调用 content 为空而 reasoning 非空 (= 推理吃满输出预算)
    /// → 升级预算 + 抑制推理再试一次; 仍空则返回**可见降级文案**并把 Success 置假 (绝不静默返回空白)。
    /// 有界: 只重试 1 次, 不做循环; 失败判定与遥测绑定 (success/empty_reply/error_kind)。
    /// </summary>
    private async Task<QueueResponse> RecoverFromEmptyContentAsync(
        ModelCatalogEntry entry, QueuePrompt prompt, QueueResponse first, CancellationToken ct)
    {
        var firstReasoning = first.ReasoningContent?.Length ?? 0;
        var firstCompletion = first.CompletionTokens;
        try
        {
            var retried = await CallEntryAsync(entry, prompt, ct,
                maxTokensOverride: MaxTokensEscalated, extraSystemSuffix: NoReasoningNudge).ConfigureAwait(false);
            var recovered = !string.IsNullOrWhiteSpace(retried.Content);
            agent.config.AgentTelemetry.Emit("llm_call_recover", "ModelQueueRouter",
                ("model", entry.Id), ("reason", "empty_content"), ("max_tokens", MaxTokensEscalated),
                ("first_content_len", first.Content?.Length ?? 0), ("first_reasoning_len", firstReasoning),
                ("first_completion_tokens", firstCompletion),
                ("retry_content_len", retried.Content?.Length ?? 0),
                ("retry_reasoning_len", retried.ReasoningContent?.Length ?? 0),
                ("retry_completion_tokens", retried.CompletionTokens),
                ("recovered", recovered));
            if (recovered) return retried;

            retried.Success = false;
            retried.Error = "empty_content_after_retry";
            // R414: 本条 Content 是**面向用户**的降级文案 ⇒ 必须显式标记, 否则链侧按"不可见失败"丢弃 (= 用户看到空白)
            retried.ContentIsUserFacing = true;
            retried.Content =
                "⚠ 模型未产出正文: 推理过程占满了输出预算 (已自动放宽输出预算并重试一次仍失败)。"
                + "请重试, 或改用非推理模型 / 缩小任务范围。";
            return retried;
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            agent.config.AgentTelemetry.Emit("llm_call_recover", "ModelQueueRouter",
                ("model", entry.Id), ("reason", "empty_content"), ("recovered", false), ("error", ex.Message));
            first.Success = false;
            first.Error = $"empty_content_retry_failed: {ex.Message}";
            first.ContentIsUserFacing = true;
            // 凭据/内部信息卫生: 可见文案**不带 ex.Message** (原始异常仍完整保留在 Error 字段, 供排查/日志)
            first.Content = "⚠ 模型未产出正文, 且自动重试失败 — 请重试或切换模型。";
            return first;
        }
    }

    /// <summary>
    /// R371 D7: **截断检测** (真机 RUN3 实证: 输出预算耗尽, 正文停在半行 `start_len: int =` 却 success=true)。
    /// 判据纯语法、与模型/语言无关: 尾部是"未完结构" (= ( [ { , + - * / \ : 或未闭合三引号 / 未闭合围栏)。
    /// 为何不用 token 计数: 预算可被升级 (8192 → 32768), 只有**结构未闭合**才是与预算无关的客观截断证据。
    /// </summary>
    public static bool LooksTruncated(string? content)
    {
        if (string.IsNullOrWhiteSpace(content)) return false;
        var t = content.TrimEnd();
        if (t.Length == 0) return false;

        // 尾部运算符 / 开括号 / 分隔符 → 语句未完 (中文全角标点不算: "说明如下：" 是完整句)
        if ("=([{,+-*/\\:".IndexOf(t[^1]) >= 0) return true;

        // 未闭合的三引号 (字符串字面量中途断掉)
        var triples = 0;
        for (var i = 0; (i = t.IndexOf("\"\"\"", i, StringComparison.Ordinal)) >= 0; i += 3) triples++;
        if (triples % 2 == 1) return true;

        // 未闭合的代码围栏
        var fences = 0;
        for (var i = 0; (i = t.IndexOf("```", i, StringComparison.Ordinal)) >= 0; i += 3) fences++;
        return fences % 2 == 1;
    }

    /// <summary>续写去重: 去掉续写段开头与已输出尾部**重叠**的部分 (模型常把断点前几个字符重打一遍)。</summary>
    public static string MergeContinuation(string head, string tail)
    {
        if (tail.Length == 0) return head;
        var max = Math.Min(MaxOverlapChars, Math.Min(head.Length, tail.Length));
        for (var len = max; len >= MinOverlapChars; len--)
        {
            var overlapped = head.AsSpan(head.Length - len);
            if (!overlapped.SequenceEqual(tail.AsSpan(0, len))) continue;
            // 纯空白重叠不算证据: 缩进/换行在断点两侧本来就相同, 删掉会吃掉真实缩进
            if (!ContainsNonSpace(overlapped)) continue;
            return head + tail[len..];
        }
        return head + tail;
    }

    private const int MinOverlapChars = 6;   // 6 起: 覆盖 `print(` 这类真实断点重复
    private const int MaxOverlapChars = 200;

    private static bool ContainsNonSpace(ReadOnlySpan<char> s)
    {
        foreach (var c in s) if (!char.IsWhiteSpace(c)) return true;
        return false;
    }

    /// <summary>截断续写提示 (模型无关表述): 给出断点, 只要求补剩余部分。</summary>
    private const string TruncatedNudge =
        "[系统] 上一轮回答在输出预算处被**截断**了 (不是写完了)。请**只输出断点之后的剩余内容**, 从断点处直接续写: "
        + "不要重复断点之前的任何字符, 不要重开场白/标题, 不要解释, 不要重开代码围栏。";

    /// <summary>
    /// R371 D7 修复: 截断正文 → 升预算 + 断点提示**续写一次**, 语法去重重拼;
    /// 续写失败/仍截断则保留原文并如实上报 (success 不置假: 半份实现仍可用, 但 truncated 事实必须可见)。
    /// </summary>
    private async Task<QueueResponse> RecoverFromTruncatedAsync(
        ModelCatalogEntry entry, QueuePrompt prompt, QueueResponse first, CancellationToken ct)
    {
        var head = first.Content ?? string.Empty;
        var tailShown = head.Length <= 40 ? head : head[^40..];
        try
        {
            var retried = await CallEntryAsync(entry, prompt, ct,
                maxTokensOverride: MaxTokensEscalated, extraSystemSuffix: TruncatedNudge).ConfigureAwait(false);
            var added = (retried.Content ?? string.Empty).TrimEnd();
            var merged = added.Length == 0 ? head : MergeContinuation(head, retried.Content!);
            var stillTruncated = LooksTruncated(merged);
            agent.config.AgentTelemetry.Emit("llm_call_continue", "ModelQueueRouter",
                ("model", entry.Id), ("reason", "truncated"), ("max_tokens", MaxTokensEscalated),
                ("before_len", head.Length), ("added_len", added.Length), ("after_len", merged.Length),
                ("first_completion_tokens", first.CompletionTokens),
                ("retry_completion_tokens", retried.CompletionTokens),
                ("still_truncated", stillTruncated), ("recovered", added.Length > 0 && !stillTruncated),
                ("tail_before", tailShown));
            if (added.Length == 0) return first;
            first.Content = merged;
            return first;
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            agent.config.AgentTelemetry.Emit("llm_call_continue", "ModelQueueRouter",
                ("model", entry.Id), ("reason", "truncated"), ("recovered", false), ("error", ex.Message));
            return first;
        }
    }

    private static int _reqDumpSeq;

    /// <summary>
    /// R378 (缓存命中率归因): 把发给提供方的请求体原样落盘, 目录由 env AGENTFRAMEWORK_DUMP_REQUEST 指定。
    /// 用途: 两次调用的最长公共前缀 = 提供方实际可缓存的上界; 据此定位"第一个分歧字节"。
    /// 默认关闭 (未设 env 时零开销), 失败静默且不影响主链。
    /// </summary>
    private static void DumpRequestIfRequested(string body)
    {
        var dir = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_DUMP_REQUEST");
        if (string.IsNullOrWhiteSpace(dir)) return;
        try
        {
            if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);
            var n = System.Threading.Interlocked.Increment(ref _reqDumpSeq);
            var stamp = DateTime.UtcNow.ToString("HHmmss_fff", System.Globalization.CultureInfo.InvariantCulture);
            var path = Path.Combine(dir, "req_" + stamp + "_" + n.ToString("00", System.Globalization.CultureInfo.InvariantCulture) + ".json");
            File.WriteAllText(path, body, new System.Text.UTF8Encoding(false));
        }
        catch
        {
            // 诊断通道: 任何失败都不应影响主链
        }
    }

    private async Task<QueueResponse> CallEntryAsync(ModelCatalogEntry entry, QueuePrompt prompt, CancellationToken ct,
        int? maxTokensOverride = null, string? extraSystemSuffix = null)
    {
        // R351: 全通道 key 走环境变量 (官方内存通道已移除; 凭据铁律不变)
        var apiKey = Environment.GetEnvironmentVariable(entry.ApiKeyEnv);
        if (string.IsNullOrEmpty(apiKey))
        {
            return new QueueResponse
            {
                Success = false,
                Model = entry.Id,
                Error = $"环境变量 {entry.ApiKeyEnv} 未设置 (模型 {entry.Id} 的 API Key 来源)",
            };
        }

        var client = _httpClientFactory.CreateClient("modelqueue");
        var targetEndpoint = prompt.ImageUrls.Count > 0 ? VisionPayload.ToChatEndpoint(entry.Endpoint) : entry.Endpoint;
        var messages = BuildMessages(prompt, extraSystemSuffix);
        var request = new QueueChatRequest { Model = entry.Id, Messages = messages, ReasoningEffort = prompt.ReasoningEffort, ToolsJson = prompt.ToolsJson };
        if (maxTokensOverride is int mt && mt > 0) request.MaxTokens = mt;
        var requestBody = SerializeChatRequest(request);
        // R378 归因: 请求体按需落盘 (env AGENTFRAMEWORK_DUMP_REQUEST=目录) —— 缓存命中率前缀分歧点可测
        DumpRequestIfRequested(requestBody);
        using var http = new HttpRequestMessage(HttpMethod.Post, targetEndpoint)
        {
            Content = new StringContent(requestBody, System.Text.Encoding.UTF8, "application/json"),
        };
        http.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", apiKey);

        using var resp = await client.SendAsync(http, ct);
        var body = await resp.Content.ReadAsStringAsync(ct);
        if (!resp.IsSuccessStatusCode)
        {
            throw new HttpRequestException($"HTTP {(int)resp.StatusCode}: {Truncate(body, 200)}");
        }

        var parsed = JsonSerializer.Deserialize(body, ModelQueueJsonContext.Default.OpenAIChatResponse);
        var choice = parsed?.Choices?.FirstOrDefault();
        var content = choice?.Message?.Content ?? string.Empty;
        // v0.21.1: 推理模型思考链捕获 (DeepSeek deepseek-flash/reasoner 实测返回 reasoning_content)
        var reasoning = choice?.Message?.ReasoningContent;
        // R456 解析面: tool_calls → 链上动作请求 (无 tool_calls 时为 null, 行为与旧版一致)
        List<ActionToolCall>? toolCalls = null;
        if (choice?.Message?.ToolCalls is { Count: > 0 } raw)
        {
            toolCalls = new List<ActionToolCall>(raw.Count);
            foreach (var tc in raw)
                toolCalls.Add(new ActionToolCall
                {
                    Id = tc.Id ?? string.Empty,
                    Name = tc.Function?.Name ?? string.Empty,
                    ArgumentsJson = string.IsNullOrEmpty(tc.Function?.Arguments) ? "{}" : tc.Function!.Arguments!,
                });
        }
        return new QueueResponse
        {
            Content = content,
            Success = true,
            Model = entry.Id,
            PromptTokens = parsed?.Usage?.PromptTokens ?? 0,
            TokensUsed = parsed?.Usage?.TotalTokens ?? 0,
            CacheHitTokens = parsed?.Usage?.PromptCacheHitTokens,
            CacheMissTokens = parsed?.Usage?.PromptCacheMissTokens,
            ReasoningContent = reasoning,
            ToolCalls = toolCalls,
            FinishReason = choice?.FinishReason,
        };
    }

    /// <summary>
    /// R379: 消息列表装配 (自 CallEntryAsync 抽出, 供缓存前缀不变式机检直接消费, 无需网络)。
    /// 顺序契约: system(会话内恒定字节) → context(system, 本轮) → history(追加式全量回放) → user(本轮)
    ///   → [extraSystemSuffix]。
    /// ⚠ extraSystemSuffix 必须追加在末尾: 任何把它前置到 system 首位的改动都会切断已缓存前缀
    ///   (MultiTurnCachePrefixTests 负向控制会红)。同理 system 一旦发出, 会话内不得再变。
    /// </summary>
    internal static List<QueueChatMessage> BuildMessages(QueuePrompt prompt, string? extraSystemSuffix = null)
    {
        var messages = new List<QueueChatMessage>();
        if (!string.IsNullOrEmpty(prompt.SystemPrompt))
            messages.Add(new QueueChatMessage { Role = "system", Content = prompt.SystemPrompt });
        if (!string.IsNullOrEmpty(prompt.ContextPrompt))
            messages.Add(new QueueChatMessage
            {
                Role = "system",
                Content = $"以下是你可以参考的相关上下文信息，请结合这些信息回答用户问题：\n\n{prompt.ContextPrompt}"
            });
        foreach (var msg in prompt.History)
            messages.Add(new QueueChatMessage { Role = msg.Role, Content = msg.Content });
        // v0.12.0 A2: 带图 user 消息 → parts[] 多段 (text + image_url × N)
        if (prompt.ImageUrls.Count > 0)
        {
            var parts = new List<QueueContentPart> { new() { Type = "text", Text = prompt.UserMessage } };
            // v0.12.0 A3 (真缺陷 63): 本地路径 → base64 data URL (云端无法读本地文件, 真机 400/1210 实证)
            parts.AddRange(prompt.ImageUrls.Select(u => new QueueContentPart
            {
                Type = "image_url",
                ImageUrl = new QueueImageUrl { Url = VisionPayload.ToDataUrl(u) },
            }));
            messages.Add(new QueueChatMessage { Role = "user", Content = prompt.UserMessage, ContentParts = parts });
        }
        else
        {
            messages.Add(new QueueChatMessage { Role = "user", Content = prompt.UserMessage });
        }

        // v0.12.0 A3 (真缺陷 64): coding 端点不收图像 (HTTP 400 1210 真机实证) —
        // 带图请求改写标准 v4 chat 端点 (glm-5.3-flash 视觉走 v4, data URL 真机已验 1445tok)。
        if (!string.IsNullOrWhiteSpace(extraSystemSuffix))
            messages.Add(new QueueChatMessage { Role = "system", Content = extraSystemSuffix });
        // R456 回灌面: 动作环追加消息 (assistant(tool_calls)/tool(...)) 一律在**最尾部** ——
        // 前缀 system/context/history/user/extra 逐字节不变 ⇒ provider 缓存前缀单调增长 (R377 红线)。
        foreach (var pm in prompt.PostUser)
            messages.Add(new QueueChatMessage
            {
                Role = pm.Role,
                Content = pm.Content,
                ToolCalls = pm.ToolCalls,
                ToolCallId = pm.ToolCallId,
            });
        return messages;
    }

    private static string Truncate(string s, int max) =>
        s.Length <= max ? s : s[..max] + "…";
}

/// <summary>AOT source-gen 序列化上下文 (模型队列协议 DTO)</summary>
[JsonSerializable(typeof(QueueChatRequest))]
[JsonSerializable(typeof(OpenAIChatResponse))]
[JsonSerializable(typeof(ModelSwitchRecord))]
[JsonSourceGenerationOptions(DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull)]
public partial class ModelQueueJsonContext : JsonSerializerContext
{
}
