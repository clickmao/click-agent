using System.Text.Json.Serialization;

namespace agent.search;


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
