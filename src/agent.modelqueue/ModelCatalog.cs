using agent.config;

namespace agent.modelqueue;

/// <summary>模型目录条目 (C.6.2) — 除 API-KEY 外全部参数; key 只存环境变量名。</summary>
public sealed class ModelCatalogEntry
{
    public string Id { get; set; } = string.Empty;

    /// <summary>人读描述 (v0.11.0: 一句话能力/定位 — /model list 展示)</summary>
    public string Description { get; set; } = string.Empty;

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
/// <summary>本地推理通道配置 (models.yaml local 段 — gguf 路径/上下文/GPU 层数)</summary>
public sealed class LocalChannelConfig
{
    /// <summary>gguf 对话模型路径 (空/文件缺失 → 本地通道不可用)</summary>
    public string ModelPath { get; set; } = string.Empty;

    /// <summary>上下文窗口大小</summary>
    public int ContextSize { get; set; } = 4096;

    /// <summary>vulkan offload 层数 (0 = 纯 CPU)</summary>
    public int GpuLayers { get; set; }

    /// <summary>配置路径非空且文件存在 = 通道就绪</summary>
    public bool IsReady => !string.IsNullOrEmpty(ModelPath) && File.Exists(ModelPath);
}

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
    /// <summary>本地通道配置 (models.yaml local 段; 缺省 = 本地通道关闭)</summary>
    public LocalChannelConfig LocalChannel { get; set; } = new();

    public Dictionary<string, BalanceScheme> BalanceSchemes { get; set; } =
        new(StringComparer.OrdinalIgnoreCase);

    /// <summary>从分层配置解析 models.yaml (顶层节 models/balance_schemes)</summary>
    public static ModelCatalog Load(ConfigSnapshot snapshot)
    {
        var catalog = new ModelCatalog();
        // v0.10.0 修复: models.yaml 顶层 models 是列表键 — GetSection 只服务 dict 节,
        // 用 TryGetTopLevel 取原始值 (真实 bug: 运行时目录一直为空, 测试全用内联目录未暴露)
        // v0.11.0: 顶层键重构 models: → modules: (用户钦定); 旧键兼容读取
        object? modelsRoot = snapshot.TryGetTopLevel("modules", out var mvNew) ? mvNew
            : snapshot.TryGetTopLevel("models", out var mvOld) ? mvOld : null;
        if (modelsRoot is Dictionary<string, object?> dictRoot)
        {
            // 容错: models:/modules: 下再嵌同名列表 (历史格式)
            if (dictRoot.TryGetValue("models", out var nested) && nested is List<object?> nestedList)
                modelsRoot = nestedList;
            else if (dictRoot.TryGetValue("modules", out var nested2) && nested2 is List<object?> nestedList2)
                modelsRoot = nestedList2;
        }
        var section = modelsRoot is List<object?> ml
            ? WrapAsSection(ml, snapshot)
            : snapshot.GetSection("models");
        if (!section.TryGetValue("modules", out var raw) || raw is not List<object?>)
            section.TryGetValue("models", out raw);
        if (raw is List<object?> list)
        {
            foreach (var item in list)
            {
                if (item is not Dictionary<string, object?> d)
                    continue;
                catalog.Models.Add(new ModelCatalogEntry
                {
                    Id = OrStr(d, "name", "id"),
                    Description = AsString(d, "description"),
                    Provider = AsString(d, "provider"),
                    Endpoint = OrStr(d, "request_address", "endpoint"),
                    ApiKeyEnv = OrStr(d, "api_key", "api_key_env"),
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
        if (section.TryGetValue("local", out var lc) && lc is Dictionary<string, object?> ld)
        {
            catalog.LocalChannel = new LocalChannelConfig
            {
                ModelPath = AsString(ld, "model_path"),
                ContextSize = (int)AsDouble(ld, "context_size"),
                GpuLayers = (int)AsDouble(ld, "gpu_layers"),
            };
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

    /// <summary>顶层列表包装为节 dict (models 键 → 列表) — Load 内部形态适配</summary>
    private static Dictionary<string, object?> WrapAsSection(List<object?> models, ConfigSnapshot snapshot)
    {
        var d = new Dictionary<string, object?>();
        d["modules"] = models;
        d["models"] = models; // 双键兼容 (旧解析路径)
        // local/balance_schemes 仍是顶层 dict 键 — 从 snapshot 原始顶层取出
        if (snapshot.TryGetTopLevel("local", out var lc) && lc is Dictionary<string, object?> lcd)
            d["local"] = lcd;
        if (snapshot.TryGetTopLevel("balance_schemes", out var bs) && bs is Dictionary<string, object?> bsd)
            d["balance_schemes"] = bsd;
        return d;
    }

    public ModelCatalogEntry? Find(string? id) =>
        id is null ? null : Models.FirstOrDefault(m =>
            string.Equals(m.Id, id, StringComparison.OrdinalIgnoreCase));

    private static string AsString(Dictionary<string, object?> d, string k) =>
        d.TryGetValue(k, out var v) && v is string s ? s : string.Empty;

    /// <summary>双键读取: 新键优先, 缺失回落旧键 (v0.11.0 格式重构兼容)</summary>
    private static string OrStr(Dictionary<string, object?> d, string newKey, string oldKey)
        => OrStrImpl(d, newKey, oldKey);

    private static string OrStrImpl(Dictionary<string, object?> d, string newKey, string oldKey)
    {
        var v = AsString(d, newKey);
        return v.Length > 0 ? v : AsString(d, oldKey);
    }

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
