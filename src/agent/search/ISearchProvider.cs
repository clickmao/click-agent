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
