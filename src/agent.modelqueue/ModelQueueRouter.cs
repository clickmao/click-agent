using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.modelqueue;

/// <summary>
/// 模型队列路由器 (v7.15 C.3.3): ILLMCaller 实现 — 内部按策略从模型目录选模型,
/// 主模型连续失败 N 次自动切备 (取消永不触发切换), 手动 /model 指定最高优先。
/// 序列化全走 source-gen fast-path (AOT 铁律)。
/// </summary>
public sealed partial class ModelQueueRouter : IModelQueueCaller
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
}
