using System.Text.Json.Serialization;

namespace agent.search;


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
