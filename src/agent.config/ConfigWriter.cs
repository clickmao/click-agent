using System.Globalization;
using System.Text;

namespace agent.config;

/// <summary>
/// 配置写入器 (v7.15 需求4): 公开给外部 C# 项目的人性化配置读写接口 —
/// 与 <see cref="ConfigSnapshot"/> (只读快照) 配对。
///
/// 职责边界 (规范 §3/§6):
///   读: ConfigSnapshot (四层合并视图, Get/GetSection)
///   写: ConfigWriter — 只落 **runtime/dynamic.yaml (L4)** 或 **modules/{module}.yaml (L3 同名覆盖)**,
///       永不直接改 L1 base (基础配置 = 代码发布物的一部分)。
///
/// 人性化点:
///   - dot-path 快速定位: Get("model_queue", "router.max_failures") / Set(...)
///   - SetModule(module, dict) 整节覆盖
///   - 自动建目录; MiniYaml 序列化 (注释保留尽力而为 — 语义化写入)
///   - 快照刷新: 写后调用方重新 new ConfigSnapshot 或 Reload() (无缓存穿透)
/// </summary>
public sealed class ConfigWriter
{
    private readonly string _configRoot;

    public ConfigWriter(string? configRoot = null)
    {
        _configRoot = string.IsNullOrWhiteSpace(configRoot)
            ? Path.Combine(".", "config")
            : configRoot;
    }

    // ─────────────────────────── 读 (dot-path) ───────────────────────────

    /// <summary>
    /// 快速读取某模块某个键 (dot-path 支持 "router.max_failures" 二级路径)。
    /// snapshot 传当前生效快照 (四层合并后), 不在 Writer 内重新加载 — 读写分离, 读零副作用。
    /// </summary>
    public static T GetValue<T>(ConfigSnapshot snapshot, string module, string path, T fallback)
    {
        var section = snapshot.GetSection(module);
        object? current = section;
        foreach (var segment in path.Split('.'))
        {
            if (current is not IReadOnlyDictionary<string, object?> dict ||
                !dict.TryGetValue(segment, out current))
                return fallback;
        }
        if (current is T typed)
            return typed;
        try
        {
            var converted = Convert.ChangeType(current, typeof(T), CultureInfo.InvariantCulture);
            return converted is T ok ? ok : fallback;
        }
        catch (FormatException) { }
        catch (InvalidCastException) { }
        catch (OverflowException) { }
        return fallback;
    }

    // ─────────────────────────── 写 (L4 runtime / L3 modules) ───────────────────────────

    /// <summary>
    /// 写运行时动态项 (L4 runtime/dynamic.yaml): 仅 @dynamic 语义的键 (规范 §5),
    /// 点路径自动展开为嵌套字典。同键覆盖。
    /// </summary>
    public void SetRuntime(string module, string path, object? value)
    {
        var runtimePath = Path.Combine(_configRoot, "runtime", "dynamic.yaml");
        var doc = LoadYaml(runtimePath);
        var moduleDict = EnsureModule(doc, module);
        ApplyDotPath(moduleDict, path, value);
        SaveYaml(runtimePath, doc);
    }

    /// <summary>
    /// 写模块同名覆盖 (L3 modules/{module}.yaml): 整模块节覆盖/合并 (深合并语义 — 已有键保留,
    /// 新键追加, 显式 null 删除该键)。这是"快速得到某个 module 的配置并改它"的主入口。
    /// </summary>
    public void UpdateModule(string module, IReadOnlyDictionary<string, object?> overrides)
    {
        var modulePath = Path.Combine(_configRoot, "modules", module + ".yaml");
        // 规范: 文件内容顶层 key = 模块名 (MergeDir 按内容合并, 不按文件名归节)
        var doc = LoadYaml(modulePath);
        var moduleDict = EnsureModule(doc, module);
        foreach (var (key, value) in overrides)
        {
            if (value is null)
                moduleDict.Remove(key); // null = 删除覆盖项 (回落 L1)
            else if (value is Dictionary<string, object?> sub)
            {
                // 深合并语义: 已有嵌套节保留未提及键
                if (moduleDict.TryGetValue(key, out var existing) &&
                    existing is Dictionary<string, object?> existDict)
                    ConfigSnapshot.DeepMerge(existDict, sub);
                else
                    moduleDict[key] = sub;
            }
            else
                moduleDict[key] = value;
        }
        SaveYaml(modulePath, doc);
    }

    /// <summary>清空某模块的 L3 同名覆盖 (回落 L1 base)。</summary>
    public void ResetModule(string module)
    {
        var modulePath = Path.Combine(_configRoot, "modules", module + ".yaml");
        if (File.Exists(modulePath))
            File.Delete(modulePath);
    }

    // ─────────────────────────── 内部 ───────────────────────────

    private Dictionary<string, object?> LoadYaml(string path)
    {
        if (!File.Exists(path))
            return new Dictionary<string, object?>();
        try
        {
            return new Dictionary<string, object?>(MiniYaml.Parse(File.ReadAllText(path)));
        }
        catch (FormatException)
        {
            // 坏文件 → 从空开始 (写入即修复), 不阻断
            return new Dictionary<string, object?>();
        }
    }

    private static Dictionary<string, object?> EnsureModule(
        Dictionary<string, object?> doc, string module)
    {
        if (doc.TryGetValue(module, out var v) && v is Dictionary<string, object?> d)
            return d;
        var fresh = new Dictionary<string, object?>();
        doc[module] = fresh;
        return fresh;
    }

    /// <summary>点路径展开: "a.b" → {"a": {"b": value}} (中间节点自动建)。</summary>
    private static void ApplyDotPath(
        Dictionary<string, object?> target, string path, object? value)
    {
        var segments = path.Split('.');
        var current = target;
        for (var i = 0; i < segments.Length - 1; i++)
        {
            if (!current.TryGetValue(segments[i], out var next) ||
                next is not Dictionary<string, object?> nextDict)
            {
                nextDict = new Dictionary<string, object?>();
                current[segments[i]] = nextDict;
            }
            current = nextDict;
        }
        current[segments[^1]] = value;
    }

    /// <summary>MiniYaml 序列化落盘 (目录自动建; UTF-8 无 BOM)。</summary>
    private void SaveYaml(string path, Dictionary<string, object?> doc)
    {
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir))
            Directory.CreateDirectory(dir);
        File.WriteAllText(path, MiniYamlSerialize(doc), new UTF8Encoding(false));
    }

    /// <summary>
    /// MiniYaml 反向序列化 (递归嵌套, 与 MiniYaml.Parse 缩进递归对齐):
    /// 字典 → key: + 深一层缩进子节; 标量 → 单行。
    /// </summary>
    internal static string MiniYamlSerialize(Dictionary<string, object?> doc) =>
        SerializeDict(doc, indent: 0);

    private static string SerializeDict(Dictionary<string, object?> doc, int indent)
    {
        var pad = new string(' ', indent * 2);
        var sb = new StringBuilder();
        foreach (var (key, value) in doc)
        {
            if (value is Dictionary<string, object?> sub)
            {
                sb.AppendLine($"{pad}{key}:");
                sb.Append(SerializeDict(sub, indent + 1));
            }
            else
            {
                sb.AppendLine($"{pad}{key}: {FormatScalar(value)}");
            }
        }
        return sb.ToString();
    }

    private static string FormatScalar(object? value) => value switch
    {
        null => "",
        string s => s,
        bool b => b ? "true" : "false",
        IFormattable f => f.ToString(null, CultureInfo.InvariantCulture),
        _ => value.ToString() ?? "",
    };
}
