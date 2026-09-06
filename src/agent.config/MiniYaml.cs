using System.Globalization;
using System.Text;

namespace agent.config;

/// <summary>
/// YAML 解析门面 (零反射, NativeAOT 安全) — 全框架配置读取的地基。
/// v0.10.0 新需求1: 内部实现由自研子集解析器替换为 Yamlify 1.8.0 (SwissLife-OSS, MIT)。
///   - Yamlify: SourceGenerator 级库, 运行时零反射, NativeAOT 实测零 IL 警告
///   - YAML 1.2 全规范 (原子集: 锚点/流式/多行块标量等均不支持, 现全支持)
///   - 输出契约不变: Dictionary&lt;string, object?&gt; / List&lt;object?&gt; / 标量
///     (标量按原 MiniYaml 契约解析: bool/int/long/double/null, 其余为 string)
/// 5 个消费者 (ConfigSnapshot/SkillRegistry/ConfigWriter/测试) API 零改动。
/// </summary>
public static class MiniYaml
{
    /// <summary>解析 YAML 文本 → 弱类型树。FormatException 语义与原实现一致 (调用方捕获回退)。</summary>
    public static Dictionary<string, object?> Parse(string yamlText)
    {
        try
        {
            var docs = Yamlify.Nodes.YamlStream.Load(yamlText);
            if (docs.Count == 0)
                throw new FormatException("MiniYaml: 文档为空");
            if (docs[0].RootNode is not Yamlify.Nodes.YamlMappingNode root)
                throw new FormatException($"MiniYaml: 根节点须为映射 (实际: {docs[0].RootNode?.NodeType})");
            var result = new Dictionary<string, object?>();
            foreach (var (keyNode, valueNode) in IterateMapping(root))
                result[KeyToString(keyNode)] = ToTree(valueNode);
            return result;
        }
        catch (FormatException)
        {
            throw; // 本层语义错误直接抛
        }
        catch (Exception ex)
        {
            throw new FormatException($"MiniYaml: YAML 解析失败 ({ex.Message})", ex);
        }
    }

    private static System.Collections.Generic.IEnumerable<(Yamlify.Nodes.YamlNode Key, Yamlify.Nodes.YamlNode Value)> IterateMapping(Yamlify.Nodes.YamlMappingNode map)
    {
        var keys = map.Keys.ToList();
        var values = map.Values.ToList();
        for (var i = 0; i < keys.Count; i++)
            yield return (keys[i], values[i]);
    }

    private static string KeyToString(Yamlify.Nodes.YamlNode key)
        => key switch
        {
            Yamlify.Nodes.YamlScalarNode s => s.Value ?? string.Empty,
            _ => throw new FormatException("MiniYaml: 映射 key 须为标量"),
        };

    /// <summary>DOM 节点 → 弱类型树 (嵌套 dict/list/标量)</summary>
    private static object? ToTree(Yamlify.Nodes.YamlNode node)
    {
        switch (node)
        {
            case Yamlify.Nodes.YamlMappingNode map:
                var d = new Dictionary<string, object?>();
                foreach (var (k, v) in IterateMapping(map))
                    d[KeyToString(k)] = ToTree(v);
                return d;
            case Yamlify.Nodes.YamlSequenceNode seq:
                var l = new List<object?>();
                foreach (var item in seq)
                    l.Add(ToTree(item));
                return l;
            case Yamlify.Nodes.YamlScalarNode sc:
                return ParseScalar(sc.Value, sc.Style);
            default:
                return null;
        }
    }

    /// <summary>标量解析 (契约兼容原 MiniYaml): bool/int/long/double/null/其余 string</summary>
    private static object? ParseScalar(string? value, Yamlify.ScalarStyle style)
    {
        if (value is null) return null;
        // 引号标量: 原样保留字符串 (不剥引号 — Yamlify DOM 已剥)
        
        return ParseScalarText(value, style);
    }

    private static object? ParseScalarText(string value, Yamlify.ScalarStyle style)
    {
        // 显式引号强制 string (即使内容像数字)
        if (style == Yamlify.ScalarStyle.SingleQuoted || style == Yamlify.ScalarStyle.DoubleQuoted)
            return value;
        // 隐式标量类型推断 (与原 MiniYaml 契约一致)
        if (value == "null" || value == "~" || value.Length == 0) return null;
        if (value == "true") return true;
        if (value == "false") return false;
        if (long.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out var l)) return l;
        if (double.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out var d)) return d;
        return value;
    }
}
