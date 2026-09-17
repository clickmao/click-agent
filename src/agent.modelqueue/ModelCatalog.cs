using agent.config;

namespace agent.modelqueue;

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
                    Priority = (int)AsDouble(d, "priority"),
                    CodingScore = (int)AsDouble(d, "coding_score"),
                    ContextWindow = (int)AsDouble(d, "context_window"),
                    SuitedFor = d.TryGetValue("suited_for", out var sf) && sf is List<object?> sl
                        ? sl.Where(x => x is string).Select(x => (string)x!).ToList()
                        : new List<string>(),
                    Capabilities = ModelCapabilitiesParser.Parse(d),
                });
            }
        }
        if (section.TryGetValue("local", out var lc) && lc is Dictionary<string, object?> ld)
        {
            catalog.LocalChannel = new LocalChannelConfig
            {
                Declared = true,
                ModelPath = AsString(ld, "model_path"),
                ContextSize = (int)AsDouble(ld, "context_size"),
                GpuLayers = (int)AsDouble(ld, "gpu_layers"),
                // R413: 缺省键 = 默认值 (向后兼容旧 models.yaml, 不带 local 段时通道关闭)
                MaxTokens = ld.ContainsKey("max_tokens") ? (int)AsDouble(ld, "max_tokens") : 256,
                Parallel = ld.ContainsKey("parallel") ? Math.Max(1, (int)AsDouble(ld, "parallel")) : 1,
                MaxPromptTokens = ld.ContainsKey("max_prompt_tokens") ? (int)AsDouble(ld, "max_prompt_tokens") : 2048,
                AllowedKinds = ld.TryGetValue("allowed_kinds", out var ak) && ak is List<object?> akl
                    ? akl.Where(x => x is string).Select(x => (string)x!).ToList()
                    : new List<string>(),
                AllowGeneral = ld.TryGetValue("allow_general", out var ag) && ag is bool agb && agb,
                TurnGate = ld.TryGetValue("turn_gate", out var tg) && tg is bool tgb && tgb,
                RelationJudge = ld.TryGetValue("relation_judge", out var rj) && rj is bool rjb && rjb,
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
                    Endpoint = OrStr(sd, "request_address", "endpoint"),
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
