using System.Collections.Concurrent;
using System.Globalization;

namespace agent.modelqueue;

/// <summary>单次调用用量记录</summary>
public sealed record UsageRecord(string ModelId, string Provider, int PromptTokens, int CompletionTokens, DateTime At);

/// <summary>模型余额快照 (真实 API 查询结果或本地推算)</summary>
public sealed record BalanceSnapshot(
    string Provider, double? TotalRemaining, DateTime At, bool FromApi,
    string Currency = "USD"); // v0.11.0 R15: 原始币种 (默认 USD 兼容旧调用)

/// <summary>
/// v0.10.0 Token 使用统计服务 — 用户钦定契约:
///   ① 初始化: 每个有余额 API 的 provider 真实同步一次 (BalanceQueryService 真实 HTTP)
///   ② 每次调用: 本地累计 (PromptTokens+CompletionTokens, 按模型/维度聚合)
///   ③ 阈值再同步: 累计消耗超 _resyncThresholdTokens 后, 下次调用前再真实同步一次
///   ④ 余额预估: remaining = lastApiRemaining - (本地累计消耗 × 单价)
///   ⑤ 余额不足判定: remaining &lt; 任务预估成本阈值 → 前端提示 model:xxx flags:余额不足 + 切换模型
/// 线程安全: ConcurrentDictionary + 单锁快照 (读写均衡, 热路径只读字典)。
/// </summary>
public sealed class TokenUsageService
{
    private readonly BalanceQueryService _balance;
    private readonly ModelCatalog _catalog;
    private readonly int _resyncThresholdTokens;
    private readonly double _minBalanceUsd;          // 余额不足判定线 (USD)
    private readonly object _sync = new();

    private readonly ConcurrentDictionary<string, long> _tokensByModel = new();
    private readonly ConcurrentDictionary<string, long> _tokensByProvider = new();
    private readonly Dictionary<string, BalanceSnapshot> _balances = new();   // provider → 快照
    private readonly Dictionary<string, long> _tokensSinceSync = new();       // provider → 上次同步后累计
    private long _totalTokens;

    public TokenUsageService(BalanceQueryService balance, ModelCatalog catalog,
        int resyncThresholdTokens = 100_000, double minBalanceUsd = 0.50)
    {
        _balance = balance;
        _catalog = catalog;
        _resyncThresholdTokens = Math.Max(1_000, resyncThresholdTokens);
        // v0.11.0 R15: 判定线支持 env 覆写 (阈值切模实战注入用)
        var envMin = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_MIN_BALANCE_USD");
        if (double.TryParse(envMin, System.Globalization.CultureInfo.InvariantCulture, out var parsedMin) && parsedMin >= 0)
            minBalanceUsd = parsedMin;
        _minBalanceUsd = minBalanceUsd;
    }

    /// <summary>初始化同步: 对每个有余额 API 的 provider 真实同步一次 (启动时调用)</summary>
    public async Task InitializeAsync(CancellationToken ct = default)
    {
        var providers = _catalog.Models
            .Where(m => _catalog.BalanceSchemes.ContainsKey(m.Provider))
            .Select(m => m.Provider)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
        foreach (var p in providers)
        {
            try
            {
                var r = await _balance.QueryAsync(p, ct).ConfigureAwait(false);
                if (r is { Ok: true, TotalRemaining: not null })
                {
                    lock (_sync)
                    {
                        _balances[p] = new BalanceSnapshot(p, r.TotalRemaining.Value, DateTime.UtcNow, FromApi: true, r.Currency);
                        _tokensSinceSync[p] = 0;
                    }
                }
            }
            catch
            {
                // 初始化同步失败不阻断启动 — 该 provider 走纯本地累计 (余额未知)
            }
        }
    }

    /// <summary>记录一次调用用量 (本地累计 — 每次 LLM 调用后)</summary>
    public void RecordUsage(string modelId, string provider, int promptTokens, int completionTokens)
    {
        var total = promptTokens + completionTokens;
        if (total <= 0) return;
        _tokensByModel.AddOrUpdate(modelId, total, (_, v) => v + total);
        _tokensByProvider.AddOrUpdate(provider, total, (_, v) => v + total);
        lock (_sync)
        {
            _totalTokens += total;
            _tokensSinceSync[provider] = _tokensSinceSync.TryGetValue(provider, out var s) ? s + total : total;
        }
    }

    /// <summary>
    /// 预估余额检查: remaining = api余额 - 本地累计消耗×单价。
    /// 返回 (预估余额, 是否充足)。余额未知 (无 API) → (null, true) 不阻断。
    /// </summary>
    public (double? Remaining, bool Sufficient) EstimateBalance(string provider, int estimatedTokens)
    {
        lock (_sync)
        {
            if (!_balances.TryGetValue(provider, out var snap) || snap.TotalRemaining is null)
                return (null, true); // 未知不阻断 (诚实: 无余额 API 的 provider 只统计不判定)
            var priceOut = _catalog.Models
                .Where(m => string.Equals(m.Provider, provider, StringComparison.OrdinalIgnoreCase))
                .Select(m => m.PriceOutPerM).DefaultIfEmpty(0).Min();
            // v0.11.0 R15: 余额币种 ≠ 记价币种 (USD) 时先换算再比较 (原实现 CNY 余额直接当 USD 比价, 差 ~7.2 倍)
            var rate = CurrencyToUsdRate(snap.Currency);
            var balanceUsd = snap.TotalRemaining.Value * rate;
            var spentSinceSync = (_tokensSinceSync.TryGetValue(provider, out var s) ? s : 0) * priceOut / 1_000_000.0;
            var remaining = balanceUsd - spentSinceSync;
            var estCost = estimatedTokens * priceOut / 1_000_000.0;
            return (remaining, remaining - estCost >= _minBalanceUsd);
            // remaining - estCost >= minBalanceUsd: 预估完成本次调用后仍高于判定线
        }
    }

    /// <summary>
    /// v0.11.0 R15: 原始币种→USD 汇率。AGENTFRAMEWORK_FX_RATE_CNY_USD 环境变量可覆写 (默认 7.2);
    /// 未知币种返回 1.0 并由调用方语义保持 (记账侧只统计不判定)。
    /// </summary>
    public static double CurrencyToUsdRate(string currency)
    {
        if (string.IsNullOrWhiteSpace(currency) || string.Equals(currency, "USD", StringComparison.OrdinalIgnoreCase))
            return 1.0;
        if (string.Equals(currency, "CNY", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(currency, "RMB", StringComparison.OrdinalIgnoreCase))
        {
            var env = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_FX_RATE_CNY_USD");
            return double.TryParse(env, System.Globalization.CultureInfo.InvariantCulture, out var r) && r > 0 ? r : 7.2;
        }
        return 1.0; // 未知币种: 诚实按 1:1 (不编造汇率), Note 标注
    }

    /// <summary>是否需要再同步 (阈值触发: provider 累计超阈值)</summary>
    public bool NeedsResync(string provider)
    {
        lock (_sync)
            return _tokensSinceSync.TryGetValue(provider, out var s) && s >= _resyncThresholdTokens;
    }

    /// <summary>阈值触发再同步 (真实 API)</summary>
    public async Task<bool> TryResyncAsync(string provider, CancellationToken ct = default)
    {
        try
        {
            var r = await _balance.QueryAsync(provider, ct).ConfigureAwait(false);
            if (r is not { Ok: true, TotalRemaining: not null }) return false;
            lock (_sync)
            {
                _balances[provider] = new BalanceSnapshot(provider, r.TotalRemaining.Value, DateTime.UtcNow, true, r.Currency);
                _tokensSinceSync[provider] = 0;
            }
            return true;
        }
        catch
        {
            return false;
        }
    }

    /// <summary>统计快照 (供 /token stats 指令与面板)</summary>
    public UsageStatsSnapshot GetStats()
    {
        lock (_sync)
        {
            return new UsageStatsSnapshot(
                TotalTokens: _totalTokens,
                TokensByModel: new Dictionary<string, long>(_tokensByModel),
                TokensByProvider: new Dictionary<string, long>(_tokensByProvider),
                Balances: _balances.ToDictionary(kv => kv.Key, kv => kv.Value),
                EstimatedCostUsd: _catalog.Models.Count == 0 ? 0 :
                    _tokensByModel.Sum(kv =>
                    {
                        var m = _catalog.Find(kv.Key);
                        return m is null ? 0 : kv.Value * (m.PriceInPerM + m.PriceOutPerM) / 2 / 1_000_000.0;
                    }));
        }
    }

    /// <summary>所有有余额快照的 provider (初始化同步过的)</summary>
    public IReadOnlyList<string> SyncedProviders
    {
        get { lock (_sync) return _balances.Keys.ToList(); }
    }
}

/// <summary>用量统计快照</summary>
public sealed record UsageStatsSnapshot(
    long TotalTokens,
    Dictionary<string, long> TokensByModel,
    Dictionary<string, long> TokensByProvider,
    Dictionary<string, BalanceSnapshot> Balances,
    double EstimatedCostUsd);
