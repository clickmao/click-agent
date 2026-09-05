using System.Globalization;
namespace agent.config;

/// <summary>
/// 分层配置快照 — 《全模块 YAML 配置开发规范》§3 的落地实现。
/// 覆盖优先级: L4 runtime/dynamic.yaml > L3 modules/{module}.yaml (同名模块定制)
///            > L2 env/{env}.yaml > L1 base/{module}.yaml。
/// 深合并: 字典递归合并, 标量/列表整体替换; 未定义字段继承低层 (增量覆盖)。
/// 模块消费方唯一入口: <see cref="Get"/> / <see cref="GetSection"/> — 禁止自行读 yaml 文件。
/// </summary>
public sealed class ConfigSnapshot
{
    /// <summary>生效配置 (四层深合并后的只读视图, 顶层 key = 模块名)</summary>
    private readonly Dictionary<string, object?> _merged;

    /// <summary>各模块配置的根目录 (相对/绝对, 默认 ./config)</summary>
    private readonly string _configRoot;

    public ConfigSnapshot(string? configRoot = null)
    {
        _configRoot = string.IsNullOrWhiteSpace(configRoot) ? Path.Combine(".", "config") : configRoot;
        _merged = LoadAll();
    }

    /// <summary>加载四层并合并。任何一层缺失都跳过 (默认值兜底由调用方/ConfigKeys 提供, 规范 §6.4)。</summary>
    private Dictionary<string, object?> LoadAll()
    {
        var merged = new Dictionary<string, object?>();
        // L1 base/ 下全部基础配置 (base 文件名 = 模块名)
        MergeDir(merged, Path.Combine(_configRoot, "base"));
        // L2 env/{env}.yaml (env 由 AGENTFRAMEWORK_ENV 指定, 缺省 development)
        var env = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_ENV") ?? "development";
        MergeFile(merged, Path.Combine(_configRoot, "env", env + ".yaml"));
        // L3 modules/ 下全部同名模块定制 (用户钦定核心契约: 同名 module 覆盖 base)
        MergeDir(merged, Path.Combine(_configRoot, "modules"));
        // L4 runtime/dynamic.yaml (热更新层, 仅 @dynamic 项运行时可变; 加载时整体并入)
        MergeFile(merged, Path.Combine(_configRoot, "runtime", "dynamic.yaml"));
        return merged;
    }

    private static void MergeDir(Dictionary<string, object?> target, string dir)
    {
        if (!Directory.Exists(dir)) return;
        foreach (var file in Directory.GetFiles(dir, "*.yaml").OrderBy(f => f, StringComparer.Ordinal))
            MergeFile(target, file);
    }

    private static void MergeFile(Dictionary<string, object?> target, string path)
    {
        if (!File.Exists(path)) return;
        try
        {
            var parsed = MiniYaml.Parse(File.ReadAllText(path));
            DeepMerge(target, parsed);
        }
        catch (FormatException ex)
        {
            // 规范 §6.4-2: 格式错误 → 回退 (跳过该文件), 告警不崩溃
            Console.Error.WriteLine($"[ConfigSnapshot][WARN] 配置文件解析失败, 已跳过: {path} ({ex.Message})");
        }
    }

    /// <summary>深合并: 字典递归, 标量/列表整体替换 (规范 §3.2-2 增量覆盖)。</summary>
    public static void DeepMerge(Dictionary<string, object?> target, Dictionary<string, object?> overlay)
    {
        foreach (var (key, value) in overlay)
        {
            if (value is Dictionary<string, object?> sub &&
                target.TryGetValue(key, out var existing) &&
                existing is Dictionary<string, object?> existDict)
            {
                DeepMerge(existDict, sub);
            }
            else
            {
                target[key] = value;
            }
        }
    }

    /// <summary>取模块节 (顶层 key)。缺失返回空字典 — 调用方按 ConfigKeys 默认值兜底。</summary>
    public IReadOnlyDictionary<string, object?> GetSection(string module)
    {
        if (_merged.TryGetValue(module, out var v) && v is Dictionary<string, object?> d)
            return d;
        return EmptyDict;
    }

    private static readonly IReadOnlyDictionary<string, object?> EmptyDict =
        new Dictionary<string, object?>();

    /// <summary>类型化标量读取: 缺失/类型不符 → 返回默认值 (规范 §6.4-3)。</summary>
    public T Get<T>(string module, string key, T fallback)
    {
        if (!GetSection(module).TryGetValue(key, out var raw) || raw is null)
            return fallback;
        if (raw is T typed) return typed;
        try
        {
            // 允许 int→double / long→int 等安全收窄
            var converted = Convert.ChangeType(raw, typeof(T), CultureInfo.InvariantCulture);
            if (converted is T ok) return ok;
        }
        catch (FormatException) { }
        catch (InvalidCastException) { }
        catch (OverflowException) { }
        return fallback;
    }

    /// <summary>调试/面板输出: 生效快照顶层键 (不导出值, 防泄漏敏感配置)。</summary>
    public IReadOnlyList<string> ModuleNames =>
        _merged.Keys.OrderBy(k => k, StringComparer.Ordinal).ToList();
}
