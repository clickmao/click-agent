using System.Text.Json.Serialization;

namespace agent.search;

/// <summary>
/// 搜索源插件契约 —— 每个具体搜索引擎实现为一个插件。
/// 工业实践参考 Tavily/Serper 的 provider 抽象与 Polly 的弹性策略:
/// 编排层(SearchFailoverService)按"主槽→备槽"顺序调用, 单源连续失败触发熔断,
/// 备源自动提升为主源, 槽位变更持久化到磁盘, 下次启动复用。
/// 全部实现必须 Native AOT 兼容 (HttpClient + System.Text.Json, 禁反射式序列化)。
/// </summary>
public interface ISearchProvider
{
    /// <summary>插件唯一标识 (bocha / searxng / bingcn / baidu)</summary>
    string Name { get; }

    /// <summary>插件是否已配置可用 (有 Key / 有实例地址 / 免配置)</summary>
    bool IsConfigured { get; }

    /// <summary>插件优先级数值, 越小越优先 (仅作为初始槽位分配依据)</summary>
    int DefaultPriority { get; }

    /// <summary>
    /// 执行搜索。实现必须:
    /// 1. 尊重 ct 取消; 2. 失败抛异常(不吞异常返回伪成功); 3. 结果按相关性降序。
    /// </summary>
    Task<List<SearchResult>> SearchAsync(string query, SearchOptions options, CancellationToken ct);
}

/// <summary>
/// 搜索源健康状态 (熔断器状态机: Closed → Open → HalfOpen)
/// </summary>
public class ProviderHealth
{
    /// <summary>连续失败次数</summary>
    public int ConsecutiveFailures { get; set; }

    /// <summary>累计成功次数</summary>
    public long TotalSuccess { get; set; }

    /// <summary>累计失败次数</summary>
    public long TotalFailures { get; set; }

    /// <summary>最近一次成功时间 (UTC)</summary>
    public DateTime? LastSuccessAt { get; set; }

    /// <summary>最近一次失败时间 (UTC)</summary>
    public DateTime? LastFailureAt { get; set; }

    /// <summary>熔断打开时间 (UTC)。非空且未过冷却期 = Open 状态</summary>
    public DateTime? OpenedAt { get; set; }

    /// <summary>是否处于熔断打开状态 (含冷却期判断)</summary>
    [JsonIgnore]
    public bool IsCircuitOpen => OpenedAt.HasValue &&
        DateTime.UtcNow - OpenedAt.Value < CircuitCooldown;

    /// <summary>熔断冷却期, 过后半开试通, 成功则闭合</summary>
    [JsonIgnore]
    public static TimeSpan CircuitCooldown => TimeSpan.FromMinutes(2);

    /// <summary>记录一次成功 (闭合熔断)</summary>
    public void RecordSuccess()
    {
        ConsecutiveFailures = 0;
        TotalSuccess++;
        LastSuccessAt = DateTime.UtcNow;
        OpenedAt = null;
    }

    /// <summary>记录一次失败 (达到阈值则打开熔断)</summary>
    public void RecordFailure(int openThreshold)
    {
        ConsecutiveFailures++;
        TotalFailures++;
        LastFailureAt = DateTime.UtcNow;
        if (ConsecutiveFailures >= openThreshold)
            OpenedAt ??= DateTime.UtcNow;
    }
}

/// <summary>
/// 槽位状态持久化模型 —— 记录主备次序, 下次启动复用
/// </summary>
public class ProviderSlotState
{
    /// <summary>槽位顺序 (index 0 = 主槽)</summary>
    public List<string> SlotOrder { get; set; } = new();

    /// <summary>各插件健康状态</summary>
    public Dictionary<string, ProviderHealthSnapshot> Health { get; set; }
        = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>状态保存时间 (UTC)</summary>
    public DateTime SavedAtUtc { get; set; } = DateTime.UtcNow;

    /// <summary>状态文件格式版本 (向前兼容)</summary>
    public int Version { get; set; } = 1;
}

/// <summary>
/// 健康状态的持久化快照 (运行时 ProviderHealth 的磁盘形态)
/// </summary>
public class ProviderHealthSnapshot
{
    public long TotalSuccess { get; set; }
    public long TotalFailures { get; set; }
    public DateTime? LastSuccessAt { get; set; }
    public DateTime? LastFailureAt { get; set; }

    public static ProviderHealthSnapshot From(ProviderHealth h) => new()
    {
        TotalSuccess = h.TotalSuccess,
        TotalFailures = h.TotalFailures,
        LastSuccessAt = h.LastSuccessAt,
        LastFailureAt = h.LastFailureAt,
    };
}

/// <summary>
/// 搜索插件配置 (来自 config/ 分层 YAML / 环境变量)
/// </summary>
public class SearchProvidersOptions
{
    /// <summary>连续失败多少次触发熔断</summary>
    public int FailureThreshold { get; set; } = 3;

    /// <summary>搜索插件配置列表 (顺序即初始主备次序)</summary>
    public List<SearchProviderConfig> Providers { get; set; } = new();

    /// <summary>槽位状态文件路径 (相对 DataStoragePath)</summary>
    public string SlotStatePath { get; set; } = "search_slots.json";

    /// <summary>单源搜索超时(秒)</summary>
    public int ProviderTimeoutSeconds { get; set; } = 10;

    /// <summary>webreaper CLI 可执行文件路径 (可选; 缺省走 PATH 探测)</summary>
    public string? WebReaperCliPath { get; set; }

    /// <summary>托管级别 (full/standard/strict): 决定敏感操作是否问询真实用户</summary>
    public string Supervision { get; set; } = "standard";
}

/// <summary>
/// 单个搜索插件配置
/// </summary>
public class SearchProviderConfig
{
    /// <summary>插件名: bocha / searxng / bingcn / baidu</summary>
    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    /// <summary>是否启用</summary>
    [JsonPropertyName("enabled")]
    public bool Enabled { get; set; } = true;

    /// <summary>API Key (博查等)</summary>
    [JsonPropertyName("apiKey")]
    public string? ApiKey { get; set; }

    /// <summary>实例地址 (SearXNG 等)</summary>
    [JsonPropertyName("endpoint")]
    public string? Endpoint { get; set; }

    /// <summary>优先级数值, 越小越优先</summary>
    [JsonPropertyName("priority")]
    public int Priority { get; set; } = 100;
}
