namespace agent.llamacpp;

/// <summary>
/// R411: <b>长驻</b>本地生成端口 —— 一个进程内**只起一个** llama-server，跨调用复用同一 KV 前缀缓存。
///
/// 为什么必须有这一层（R410 实测的缺口）: K2b 达标三条件 = **长驻进程 + 稳定长前缀 + cache 开**。
/// R410 已证明「同 server 两请求复用 99.88%」，但宿主侧每次调用都新起 server（`cached=0`/`misses=1`）
/// ⇒ 缺「长驻」这一条，另两条全白搭。本类就是补这一条的端口：懒启动 + 单飞 + 跨调用保活。
///
/// 端口化纪律（与 <see cref="LlamaCppTextEmbedder"/> 同构）:
///   • <see cref="IsAvailable"/> = 纯配置判定（模型文件 ∧ 二进制可解析），零 I/O、零进程、零副作用；
///   • 失败**抛** <see cref="LlamaCppException"/>（带 code），不静默兜底；
///   • 被使用计数: <see cref="ProcessStarts"/>/<see cref="TurnsGenerated"/>/<see cref="PromptTokensTotal"/>/
///     <see cref="CachedTokensTotal"/>/<see cref="CacheMissTurns"/>；
///   • 生成必经 <see cref="ILocalPromptRenderer"/>（R409 闸门: 只吃结构化轮次，物理上无法手拼 prompt）。
/// </summary>
public sealed class LlamaCppTextGenerator : IAsyncDisposable
{
    private readonly LlamaCppGeneratorOptions _o;
    private readonly SemaphoreSlim _gate = new(1, 1);
    /// <summary>R412: 会话级账本（多会话交替/并发下保各自的可复用上限）。</summary>
    private readonly LocalSessionTracker _sessions = new();
    private LlamaCppProvider? _provider;
    private long _starts;
    private long _turns;
    private long _promptTokens;
    private long _cachedTokens;
    private long _cacheMissTurns;

    public LlamaCppTextGenerator(LlamaCppGeneratorOptions options) => _o = options;

    /// <summary>纯配置判定（无副作用）。</summary>
    public bool IsAvailable => File.Exists(_o.ModelPath) && ResolveBinary() is not null;

    public string? BinaryPath => ResolveBinary();

    /// <summary>进程启动次数（**必须为 1** 才是长驻；>1 说明发生重启 ⇒ 前序 KV 缓存已丢）。</summary>
    public long ProcessStarts => Interlocked.Read(ref _starts);

    public long TurnsGenerated => Interlocked.Read(ref _turns);
    public long PromptTokensTotal => Interlocked.Read(ref _promptTokens);
    public long CachedTokensTotal => Interlocked.Read(ref _cachedTokens);

    /// <summary>会话口径下**非首轮**「前缀没被复用」的轮次数（cached=0 且总长 ≥128；首轮冷启动不计）。</summary>
    public long CacheMissTurns => Interlocked.Read(ref _cacheMissTurns);

    /// <summary>最近一轮读数（诊断/断言用；-1 = 尚未生成）。<see cref="LastPromptTokens"/> = **总长** = <c>tokens_evaluated</c>。</summary>
    public int LastPromptTokens { get; private set; } = -1;
    /// <summary>
    /// 最近一轮的**重算** token 数 = 总长 − 命中（= <c>timings.prompt_n</c>）。
    /// R411 实测: 冷启 497/0 ⇒ 重算 497；热轮 530/512 ⇒ 重算 18。
    /// </summary>
    public int LastPromptTokensRecomputed { get; private set; } = -1;
    public int LastCachedTokens { get; private set; } = -1;

    /// <summary>R430: 最近一次生成的 prompt 指纹 (SHA-256 前 16 hex) — 判定输入可复现性的机械锚点。</summary>
    public string LastPromptSha16 { get; private set; } = string.Empty;

    /// <summary>R430: 最近一次生成的**请求体**指纹 (覆盖 n_predict/samplers/cache_prompt/seed 等全部字段)。</summary>
    public string LastRequestSha16 { get; private set; } = string.Empty;

    /// <summary>R430: 最近一次请求的关键字段摘要 (指纹不同 ⇒ 直接指出哪个字段变了)。</summary>
    public string LastRequestFields { get; private set; } = string.Empty;
    /// <summary>最近一轮生成 token 数（下一轮的可复用上限 = 本轮总长 + 本轮生成）。</summary>
    public int LastGeneratedTokens { get; private set; } = -1;

    /// <summary>
    /// R412: 会话级账本 —— 按 <c>sessionKey</c> 分开记「上一轮总长/生成」。
    /// 实例级 <see cref="LastPromptTokens"/> 在多会话下会互相覆盖；本属性同时暴露
    /// <c>TrackedSessions</c>/<c>ConcurrentTurns</c>/<c>MaxConcurrentTurns</c>/<c>UnkeyedTurns</c> 计数。
    /// </summary>
    public LocalSessionTracker Sessions => _sessions;

    /// <summary>
    /// 口径换算（R411 独立实现钉死，**别再改回去**）:
    /// llama.cpp `/completion` 顶层的 <c>tokens_evaluated</c> = **本轮 prompt 总长**（含 BOS），
    /// <c>timings.prompt_n</c> = 本轮**新评估**数，<c>timings.cache_n</c> = 命中复用数。
    /// 实测（同一渲染串，独立实现 /tokenize 对账）: 冷 497/497/0；热 530/18/512 ⇒ 总长 = prompt_n + cache_n ✓。
    /// 教训: **不能按字段名的字面猜语义**（"evaluated" 看着像新算数，实际是总长）；命名相近的
    /// <c>tokens_evaluated</c> 与 <c>timings.prompt_n</c> 一个是总长一个是新算数。
    /// </summary>
    public static int RecomputedTokens(int promptTotalTokens, int cachedTokens)
        => Math.Max(0, promptTotalTokens - Math.Max(0, cachedTokens));

    /// <summary>服务端逐轮复用计数（透传 provider；-1 = 未启动）。</summary>
    public long ProviderSessionReuseCalls => _provider?.SessionReuseCalls ?? 0;
    public long ProviderSessionCacheMisses => _provider?.SessionCacheMisses ?? 0;
    public string? BaseUrl => _provider?.BaseUrl;

    /// <summary>
    /// 每轮生成完成回调: (sessionKey, turnIndex, promptTokens 总长, cachedTokens, carryOverCeiling)。
    /// <paramref name="carryOverCeiling"/> = 本轮开始时的「可复用上限」= 上一轮总长 + 上一轮生成；
    /// 首轮传 0（无上一轮）。
    /// 用途 = 产品侧接 K2b 台账（<c>LocalSessionCacheLedger.Observe</c>）而**不把 modelqueue 依赖塞进本程序集**
    /// （保持 agent.llamacpp → agent.contextgradient 单向分层）。cachedTokens = -1 表示未上报。
    /// </summary>
    public Action<string?, int, int, int, int>? OnTurnCompleted { get; set; }

    /// <summary>
    /// 生成一轮（长驻: 复用同一 server / 同一前缀缓存）。默认 <see cref="CompletionReuse.Session"/>（生产口径）。
    /// </summary>
    public async Task<CompletionResult> GenerateTurnAsync(
        IReadOnlyList<ChatTurn> turns,
        string? sessionKey = null,
        int turnIndex = 1,
        int? maxTokens = null,
        CompletionReuse reuse = CompletionReuse.Session,
        CancellationToken ct = default)
    {
        // R412: 上限必须取**本会话自己**的上一轮。实例级 LastPromptTokens/LastGeneratedTokens 是全局唯一的，
        //        多会话交替/并发时会被别的会话覆盖 ⇒ 台账分母污染（判红/判绿都可能失真，且外部看不出来）。
        //        无 sessionKey 时退回实例级 ⇒ 无会话形态行为不变（零回归）。
        using var lease = _sessions.EnterTurn(sessionKey);
        var carryOverCeiling = _sessions.CeilingFor(sessionKey, LastPromptTokens, LastGeneratedTokens);

        var provider = await EnsureProviderAsync(ct).ConfigureAwait(false);
        var result = await provider
            .GenerateAsync(turns, maxTokens ?? _o.MaxTokens, greedy: true, reuse, ct)
            .ConfigureAwait(false);

        // 总长 = tokens_evaluated 本身（**不再做任何加法**；见 RecomputedTokens 的实测依据）。
        var total = result.PromptTokens;
        var recomputed = RecomputedTokens(total, result.CachedTokens);
        LastPromptTokensRecomputed = recomputed;
        LastPromptTokens = total;
        LastCachedTokens = result.CachedTokens;
        // R430: 指纹只观测, 不改生成路径 (判定输入可复现性必须先能区分「输入变了」与「引擎漂了」)。
        LastPromptSha16 = result.PromptSha16;
        LastRequestSha16 = result.RequestSha16;
        LastRequestFields = result.RequestFields;
        LastGeneratedTokens = result.Tokens.Length;
        _sessions.Record(sessionKey, total, result.Tokens.Length);   // R412: 按会话记账（下一轮的 ceiling 来源）
        Interlocked.Increment(ref _turns);
        Interlocked.Add(ref _promptTokens, total);
        Interlocked.Add(ref _cachedTokens, Math.Max(0, result.CachedTokens));
        if (reuse == CompletionReuse.Session && result.CachedTokens == 0 && total >= 128 && turnIndex > 1)
            Interlocked.Increment(ref _cacheMissTurns);

        OnTurnCompleted?.Invoke(sessionKey, turnIndex, total, result.CachedTokens, carryOverCeiling);
        return result;
    }

    /// <summary>懒启动 + 单飞：并发调用只会起一个进程（长驻语义的机械保证）。</summary>
    public async Task<LlamaCppProvider> EnsureProviderAsync(CancellationToken ct = default)
    {
        if (!IsAvailable)
            throw new LlamaCppException(LlamaCppException.ProviderUnavailable,
                $"本地生成不可用: 模型不存在或二进制不可解析 (model={_o.ModelPath})");

        var existing = _provider;
        if (existing is { IsRunning: true }) return existing;

        await _gate.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            if (_provider is { IsRunning: true }) return _provider;
            if (_provider is not null && !_o.AllowRestart)
                throw new LlamaCppException(LlamaCppException.ProviderUnavailable, "生成服务已停止且 AllowRestart=false");
            if (_provider is not null) await _provider.DisposeAsync().ConfigureAwait(false);

            var provider = await LlamaCppProvider.StartAsync(new LlamaServerOptions
            {
                ModelPath = _o.ModelPath,
                BinaryPath = _o.BinaryPath,
                BinaryEnvVar = _o.BinaryEnvVar,
                ContextSize = _o.ContextSize,
                Threads = _o.Threads,
                Parallel = _o.Parallel,
                StartTimeoutMs = _o.StartTimeoutMs,
                EmbeddingMode = false,   // 与嵌入互斥 ⇒ 各起一个进程
            }, ct).ConfigureAwait(false);

            _provider = provider;
            Interlocked.Increment(ref _starts);
            return provider;
        }
        finally
        {
            _gate.Release();
        }
    }

    private string? ResolveBinary()
    {
        try
        {
            var opts = new LlamaServerOptions { ModelPath = _o.ModelPath, BinaryPath = _o.BinaryPath, BinaryEnvVar = _o.BinaryEnvVar };
            return LlamaServerHost.TryResolveBinary(opts, out var path, out _) ? path : null;
        }
        catch { return null; }
    }

    public async ValueTask DisposeAsync()
    {
        if (_provider is not null)
        {
            await _provider.DisposeAsync().ConfigureAwait(false);
            _provider = null;
        }
        _gate.Dispose();
    }
}
