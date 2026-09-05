namespace agent.modelqueue;

/// <summary>
/// "官方"模型 (用户需求1 钦定): 硬编码模型集合 — **不进 yaml 配置** (与 config/base/models.yaml
/// 的远端目录区分)。其 api-key 不落任何配置文件, 仅由 CLI 启动参数 `--official-key` 或
/// `/official-key` 指令传递 (⚠ 指令名代拟, 用户原文 "xxx 是我还没想好指令名") — 运行时存
/// OfficialKeyStore (内存), 会话结束即弃。
/// </summary>
public static class OfficialModels
{
    /// <summary>官方通道端点 (OpenAI 兼容; 官方=框架发布方签名的默认模型通道)</summary>
    public const string OfficialEndpoint = "https://api.openai.com/v1/chat/completions";

    /// <summary>官方硬编码模型 (id/推理分/编码分/价格/上下文 — 与目录同构但不走 yaml)</summary>
    public static readonly IReadOnlyList<ModelCatalogEntry> Models = new List<ModelCatalogEntry>
    {
        new()
        {
            Id = "official-gpt-4o", Provider = "official",
            Endpoint = OfficialEndpoint, ApiKeyEnv = "__OFFICIAL_KEY_MEMORY__",
            PriceInPerM = 2.50, PriceOutPerM = 10.00,
            ReasoningScore = 8, CodingScore = 8, ContextWindow = 128000,
            SuitedFor = new List<string> { "general", "coding", "reasoning", "planning" },
        },
        new()
        {
            Id = "official-gpt-4o-mini", Provider = "official",
            Endpoint = OfficialEndpoint, ApiKeyEnv = "__OFFICIAL_KEY_MEMORY__",
            PriceInPerM = 0.15, PriceOutPerM = 0.60,
            ReasoningScore = 6, CodingScore = 6, ContextWindow = 128000,
            SuitedFor = new List<string> { "general", "chat", "summary", "classify" },
        },
    };

    public static ModelCatalogEntry? Find(string? id) =>
        id is null ? null : Models.FirstOrDefault(m => m.Id.Equals(id, StringComparison.OrdinalIgnoreCase));
}

/// <summary>
/// 官方 key 内存仓库 (凭据铁律: 永不落配置/磁盘; CLI 启动参数或 /official-key 指令注入)。
/// 线程安全。进程退出即销毁。
/// </summary>
public sealed class OfficialKeyStore
{
    private readonly object _lock = new();
    private string? _key;

    /// <summary>注入 (CLI --official-key / /official-key); 空串视为清除</summary>
    public void Set(string? key)
    {
        lock (_lock)
            _key = string.IsNullOrWhiteSpace(key) ? null : key;
    }

    /// <summary>当前 key (null = 未注入)</summary>
    public string? Get()
    {
        lock (_lock)
            return _key;
    }

    /// <summary>官方通道可用? (key 已注入)</summary>
    public bool IsAvailable()
    {
        lock (_lock)
            return _key is not null;
    }
}
