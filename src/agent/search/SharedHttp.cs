namespace agent.search;

/// <summary>
/// 搜索插件共享 HttpClient —— IHttpClientFactory 无法在此处直接使用的静态场景
/// (插件构造函数) 下提供统一配置的实例; 超时/UA 与编排器一致。
/// </summary>
public static class SharedHttp
{
    private static readonly Lazy<HttpClient> _instance = new(Create);

    /// <summary>单例 HttpClient (进程生命周期内复用, 避免 socket 耗尽)</summary>
    public static HttpClient ForProviders() => _instance.Value;

    private static HttpClient Create()
    {
        var client = new HttpClient();
        client.Timeout = TimeSpan.FromSeconds(15);
        client.DefaultRequestHeaders.TryAddWithoutValidation("User-Agent",
            "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0 AgentFramework/1.0");
        client.DefaultRequestHeaders.TryAddWithoutValidation("Accept",
            "text/html,application/json;q=0.9,*/*;q=0.8");
        client.DefaultRequestHeaders.TryAddWithoutValidation("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.5");
        return client;
    }
}
