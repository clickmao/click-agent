using System.Text.Json;
using System.Text.Json.Nodes;

namespace agent.config;

/// <summary>
/// R306b — 强类型配置绑定器 (用户需求: "要 Model 的实例, 不要手写 yaml")。
/// dict (MiniYaml/合并视图) ↔ POCO 双向桥: 经 System.Text.Json 中转 (JsonNode),
/// 泛型 API 形态对 AOT 友好 (调用方 AOT 时为其 POCO 自带 source-gen 即可, 库侧零反射假设)。
///
/// 用法 (外部 C# 项目):
///   var snapshot = new ConfigSnapshot("./config");
///   var model = ConfigModelBinder.Get<ModelQueueConfig>(snapshot, "model_queue");
///   model.MaxFailures = 5;
///   new ConfigWriter("./config").Save("model_queue", model);   // 写 L3 覆盖, yaml 自动生成
///   // 校验: 重新加载
///   var reloaded = ConfigModelBinder.Get<ModelQueueConfig>(new ConfigSnapshot("./config"), "model_queue");
/// </summary>
public static class ConfigModelBinder
{
    private static readonly JsonSerializerOptions _jsonOpts = new()
    {
        PropertyNameCaseInsensitive = true,
        IncludeFields = true,
        WriteIndented = false,
    };

    /// <summary>R306b 诊断: 模块节的原始 JSON 视图 (绑定调试用)。</summary>
    public static string GetRawJson(ConfigSnapshot snapshot, string module)
    {
        return ToJsonNode(snapshot.GetSection(module))?.ToJsonString() ?? "null";
    }

    /// <summary>读某模块节 → 强类型 Model 实例 (缺失键 = POCO 默认值, 不抛)。</summary>
    public static TModel Get<TModel>(ConfigSnapshot snapshot, string module) where TModel : new()
    {
        var section = snapshot.GetSection(module);
        var node = ToJsonNode(section);
        if (node is JsonObject obj)
        {
            // GetSection 返回的节可能包着模块名 (顶层 key=module) — 若首键==module 则下钻一层
            if (obj.Count == 1 && obj.First().Key.Equals(module, StringComparison.OrdinalIgnoreCase)
                && obj.First().Value is JsonObject inner)
                node = inner;
            // R306b 修正: STJ 反序列化键匹配只做大小写不敏感, **不做下划线映射**
            // (SnakeCaseLower/SnakeCaseNamingPolicy 只影响序列化写键)。yaml 键是 snake_case
            // (max_failures), POCO 属性是 PascalCase (MaxFailures) → 预归一化 node 键再反序列化。
            node = NormalizeKeys(node);
            var model = node.Deserialize<TModel>(_jsonOpts);
            if (model is not null) return model;
        }
        return new TModel();
    }

    /// <summary>递归把 snake_case / kebab-case 键归一为 PascalCase (匹配 C# 属性名, 配合大小写不敏感)。</summary>
    internal static JsonNode? NormalizeKeys(JsonNode? node)
    {
        if (node is JsonObject obj)
        {
            var copy = new JsonObject();
            foreach (var (k, v) in obj)
            {
                // R306b: 值节点若已挂父 (来自 GetSection 的树), 需克隆后重挂 — "already has a parent" 防护
                var normalized = NormalizeKeys(v);
                if (normalized is not null && normalized.Parent is not null)
                    normalized = JsonNode.Parse(normalized.ToJsonString());
                copy[ToPascal(k)] = normalized;
            }
            return copy;
        }
        if (node is JsonArray arr)
        {
            var copyArr = new JsonArray();
            foreach (var item in arr)
            {
                var normalized = NormalizeKeys(item);
                if (normalized is not null && normalized.Parent is not null)
                    normalized = JsonNode.Parse(normalized.ToJsonString());
                copyArr.Add(normalized);
            }
            return copyArr;
        }
        return node;
    }

    private static string ToPascal(string key)
    {
        var parts = key.Split(new[] { '_', '-' }, StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length == 0) return key;
        return string.Concat(parts.Select(p => char.ToUpperInvariant(p[0]) + p[1..]));
    }

    /// <summary>强类型 Model → 写 L3 覆盖 (modules/{module}.yaml), 返回写入路径。</summary>
    public static string Save<TModel>(ConfigWriter writer, string module, TModel model)
    {
        var node = JsonSerializer.SerializeToNode(model, _jsonOpts)
            ?? throw new InvalidOperationException($"序列化 {typeof(TModel).Name} 失败");
        var dict = ToDict(node);
        writer.UpdateModule(module, dict);
        return Path.Combine("config", "modules", module + ".yaml");
    }

    /// <summary>读 + 改 + 存 一体 (最常用: 拿实例 → 改字段 → 落盘)。</summary>
    public static TModel Update<TModel>(ConfigSnapshot snapshot, ConfigWriter writer, string module,
        Action<TModel> mutate) where TModel : new()
    {
        var model = Get<TModel>(snapshot, module);
        mutate(model);
        Save(writer, module, model);
        return model;
    }

    // ── dict ↔ JsonNode 桥 (MiniYaml dict 值域: string/bool/long/double/dict/list) ──

    internal static JsonNode? ToJsonNode(object? value)
    {
        switch (value)
        {
            case null: return null;
            case bool b: return b;
            case int i: return i;
            case long l: return l;
            case double d: return d;
            case float f: return f;
            case string str: return str;
            case IReadOnlyDictionary<string, object?> dict:
                var obj = new JsonObject();
                foreach (var (k, v) in dict) obj[k] = ToJsonNode(v);
                return obj;
            case IDictionary<string, object?> dict2:
                var obj2 = new JsonObject();
                foreach (var (k, v) in dict2) obj2[k] = ToJsonNode(v);
                return obj2;
            case IEnumerable<object?> list:
                var arr = new JsonArray();
                foreach (var item in list) arr.Add(ToJsonNode(item));
                return arr;
            default:
                return JsonValue.Create(value.ToString());
        }
    }

    internal static Dictionary<string, object?> ToDict(JsonNode? node)
    {
        var result = new Dictionary<string, object?>();
        if (node is JsonObject obj)
        {
            foreach (var (k, v) in obj)
                result[k] = ToPlain(v);
        }
        return result;
    }

    private static object? ToPlain(JsonNode? node)
    {
        if (node is null) return null;
        if (node is JsonValue val)
        {
            if (val.TryGetValue<bool>(out var b)) return b;
            if (val.TryGetValue<long>(out var l)) return l;
            if (val.TryGetValue<double>(out var d)) return d;
            if (val.TryGetValue<string>(out var s)) return s;
            return val.ToJsonString();
        }
        if (node is JsonObject obj)
        {
            var dict = new Dictionary<string, object?>();
            foreach (var (k, v) in obj) dict[k] = ToPlain(v);
            return dict;
        }
        if (node is JsonArray arr)
        {
            var list = new List<object?>();
            foreach (var item in arr) list.Add(ToPlain(item));
            return list;
        }
        return node.ToJsonString();
    }
}
