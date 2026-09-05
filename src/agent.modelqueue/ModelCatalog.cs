using agent.config;

namespace agent.modelqueue;

/// <summary>模型目录条目 (C.6.2) — 除 API-KEY 外全部参数; key 只存环境变量名。</summary>
public sealed class ModelCatalogEntry
{
    public string Id { get; set; } = string.Empty;
    public string Provider { get; set; } = string.Empty;

    /// <summary>chat completions 完整 URL</summary>
    public string Endpoint { get; set; } = string.Empty;

    /// <summary>API Key 的环境变量名 (永不存 key 本体)</summary>
    public string ApiKeyEnv { get; set; } = string.Empty;

    /// <summary>输入价格 USD / 每百万 token</summary>
    public double PriceInPerM { get; set; }

    /// <summary>输出价格 USD / 每百万 token</summary>
    public double PriceOutPerM { get; set; }

    /// <summary>推理能力 1-10 (C.6.1 标准值, 依据公开评测归一化)</summary>
    public int ReasoningScore { get; set; }

    /// <summary>编码能力 1-10</summary>
    public int CodingScore { get; set; }

    /// <summary>上下文窗口 (token)</summary>
    public int ContextWindow { get; set; }

    /// <summary>适合用途 (意图匹配: general/coding/reasoning/planning/chat/summary/classify/debug)</summary>
    public List<string> SuitedFor { get; set; } = new();
}

/// <summary>余额查询方案 (C.6.4 — provider 差异大, scheme 枚举分派)</summary>
public sealed class BalanceScheme
{
    public string Endpoint { get; set; } = string.Empty;

    /// <summary>调研备注 (接口现状/字段说明)</summary>
    public string Note { get; set; } = string.Empty;
}

/// <summary>
/// 模型目录 (v7.15 C.6): 从 config/base/models.yaml 加载 (ConfigSnapshot 分层契约),
/// "自动"选模候选池 + /model 手动指定 + /balance 方案查询。
/// </summary>
public sealed class ModelCatalog
{
    public List<ModelCatalogEntry> Models { get; set; } = new();
    public Dictionary<string, BalanceScheme> BalanceSchemes { get; set; } =
        new(StringComparer.OrdinalIgnoreCase);

    /// <summary>从分层配置解析 models.yaml (顶层节 models/balance_schemes)</summary>
    public static ModelCatalog Load(ConfigSnapshot snapshot)
    {
        var catalog = new ModelCatalog();
        var section = snapshot.GetSection("models");
        if (section.TryGetValue("models", out var raw) && raw is List<object?> list)
        {
            foreach (var item in list)
            {
                if (item is not Dictionary<string, object?> d)
                    continue;
                catalog.Models.Add(new ModelCatalogEntry
                {
                    Id = AsString(d, "id"),
                    Provider = AsString(d, "provider"),
                    Endpoint = AsString(d, "endpoint"),
                    ApiKeyEnv = AsString(d, "api_key_env"),
                    PriceInPerM = AsDouble(d, "price_in_per_m"),
                    PriceOutPerM = AsDouble(d, "price_out_per_m"),
                    ReasoningScore = (int)AsDouble(d, "reasoning_score"),
                    CodingScore = (int)AsDouble(d, "coding_score"),
                    ContextWindow = (int)AsDouble(d, "context_window"),
                    SuitedFor = d.TryGetValue("suited_for", out var sf) && sf is List<object?> sl
                        ? sl.Where(x => x is string).Select(x => (string)x!).ToList()
                        : new List<string>(),
                });
            }
        }
        if (section.TryGetValue("balance_schemes", out var bs) && bs is Dictionary<string, object?> schemes)
        {
            foreach (var (k, v) in schemes)
            {
                if (v is not Dictionary<string, object?> sd)
                    continue;
                catalog.BalanceSchemes[k] = new BalanceScheme
                {
                    Endpoint = AsString(sd, "endpoint"),
                    Note = AsString(sd, "note"),
                };
            }
        }
        return catalog;
    }

    public ModelCatalogEntry? Find(string? id) =>
        id is null ? null : Models.FirstOrDefault(m =>
            string.Equals(m.Id, id, StringComparison.OrdinalIgnoreCase));

    private static string AsString(Dictionary<string, object?> d, string k) =>
        d.TryGetValue(k, out var v) && v is string s ? s : string.Empty;

    private static double AsDouble(Dictionary<string, object?> d, string k) =>
        d.TryGetValue(k, out var v) ? Convert.ToDouble(v, System.Globalization.CultureInfo.InvariantCulture) : 0d;
}

/// <summary>DI 载体: 目录 + 加载来源快照 (避免重复解析; Router/Balance/Verify 共享同一实例)</summary>
public sealed class ModelCatalogLoadResult
{
    public ModelCatalog Catalog { get; }

    private ModelCatalogLoadResult(ModelCatalog catalog) => Catalog = catalog;

    public static ModelCatalogLoadResult Wrap(ModelCatalog catalog, ConfigSnapshot snapshot) =>
        new(catalog);
}
