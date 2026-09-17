using System.Text;
using System.Text.Json;

namespace agent.modelqueue;

/// <summary>
/// R479: 工具声明面**单一事实源** —— 一份规格派生两种线格式。
/// 形态差异是**协议事实**, 不是风格问题:
///   · Chat Completions: {"type":"function","function":{"name":…,"description":…,"parameters":{…}}}
///   · Responses:        {"type":"function","name":…,"description":…,"parameters":{…}}  (平铺一层)
/// 派生文本必须逐字节稳定 (缓存前缀铁律): <see cref="ChatToolsJson"/> 与既有
/// <see cref="ActionToolDecl.ToolsJson"/> **逐字节相等**, 由单测锁死; 任何漂移即红。
/// </summary>
public sealed class ActionToolSpec
{
    public ActionToolSpec(string name, string description, string parametersJson)
    {
        Name = name;
        Description = description;
        ParametersJson = parametersJson;
    }

    public string Name { get; }

    public string Description { get; }

    /// <summary>JSON Schema 原文 (手写常量; 无反射、无生成)。</summary>
    public string ParametersJson { get; }

    /// <summary>声明面全集 (名称白名单与执行面同源: <see cref="ActionToolDecl.Names"/>)。
    /// 顺序 = 字母序; 描述自带**调用协议** (准入/排除/互斥指路) —— claude-fable-5.1 动因5/6。</summary>
    public static readonly ActionToolSpec[] All =
    {
        new(ActionToolDecl.DeleteFile,
            "删除工作区内的文件或目录。需人工审批: 未接入审批通道时一律拒绝。"
            + "不要用于清理临时文件或重建文件 (改用 write_file 覆盖); 删除不可撤销。",
            "{\"type\":\"object\",\"properties\":{\"path\":{\"type\":\"string\",\"description\":\"相对工作区根的文件/目录路径\"}},\"required\":[\"path\"]}"),
        new(ActionToolDecl.ListDir, "列出工作区目录条目 (相对路径/大小/类型)。"
            + "不要用于读取文件内容 (改用 read_file), 也不要用于按内容查找 (改用 run_command)。",
            "{\"type\":\"object\",\"properties\":{\"path\":{\"type\":\"string\",\"description\":\"相对工作区根的目录路径, 省略=根\"}},\"required\":[]}"),
        new(ActionToolDecl.ReadFile, "读取工作区文本文件。"
            + "不要用于列目录 (改用 list_dir); 超过 max_bytes 的内容会被截断。",
            "{\"type\":\"object\",\"properties\":{\"path\":{\"type\":\"string\",\"description\":\"相对工作区根的文件路径\"},\"max_bytes\":{\"type\":\"integer\",\"description\":\"最大字节数(默认8192)\"}},\"required\":[\"path\"]}"),
        new(ActionToolDecl.RunCommand, "在工作区根执行一条命令并返回 stdout/stderr/退出码。"
            + "不要用于联网、安装依赖、长驻进程或多命令串联 (串成一次调用); 一次只发一条命令。",
            "{\"type\":\"object\",\"properties\":{\"command\":{\"type\":\"string\",\"description\":\"命令原文\"},\"timeout_ms\":{\"type\":\"integer\",\"description\":\"超时毫秒(默认120000, 上限600000)\"}},\"required\":[\"command\"]}"),
        new(ActionToolDecl.WriteFile, "写入/覆盖工作区文本文件, content 为完整文件内容。"
            + "不要用于追加或局部替换 (先 read_file 读全量, 再整体覆盖); 路径必须在工作区内。",
            "{\"type\":\"object\",\"properties\":{\"path\":{\"type\":\"string\",\"description\":\"相对工作区根的文件路径\"},\"content\":{\"type\":\"string\",\"description\":\"文件内容(全量)\"}},\"required\":[\"path\",\"content\"]}"),
    };

    /// <summary>Chat Completions 线格式 (与 R456 常量逐字节相同)。</summary>
    public static readonly string ChatToolsJson = Compose(flatten: false);

    /// <summary>Responses 线格式 (平铺; tools[i] 直接带 name/description/parameters)。</summary>
    public static readonly string ResponsesToolsJson = Compose(flatten: true);

    /// <summary>
    /// R538: 前端条目标题的「主参数键」= 该工具 schema 的 required[0] (声明面本身即事实源 ⇒ 不另维护映射表;
    /// 缺 required 时退到 properties 的第一个键, 仍无 ⇒ 空串 = 标题只留工具名, 不伪造)。
    /// </summary>
    public static string PrimaryArgKey(string? tool)
    {
        foreach (var s in All)
            if (s.Name == tool) return s.PrimaryArgKeyOf();
        return string.Empty;
    }

    private string PrimaryArgKeyOf()
    {
        try
        {
            using var d = JsonDocument.Parse(ParametersJson);
            if (d.RootElement.TryGetProperty("required", out var req)
                && req.ValueKind == JsonValueKind.Array && req.GetArrayLength() > 0)
                return req[0].GetString() ?? string.Empty;
            if (d.RootElement.TryGetProperty("properties", out var props) && props.ValueKind == JsonValueKind.Object)
                foreach (var p in props.EnumerateObject()) return p.Name;
        }
        catch (JsonException) { }
        return string.Empty;
    }

    private static string Compose(bool flatten)
    {
        var sb = new StringBuilder(2048);
        sb.Append('[');
        for (var i = 0; i < All.Length; i++)
        {
            if (i > 0) sb.Append(",\n");
            var t = All[i];
            if (flatten)
            {
                sb.Append("{\"type\":\"function\",\"name\":\"").Append(t.Name)
                  .Append("\",\"description\":\"").Append(t.Description)
                  .Append("\",\"parameters\":").Append(t.ParametersJson).Append('}');
            }
            else
            {
                sb.Append("{\"type\":\"function\",\"function\":{\"name\":\"").Append(t.Name)
                  .Append("\",\"description\":\"").Append(t.Description)
                  .Append("\",\"parameters\":").Append(t.ParametersJson).Append("}}");
            }
        }
        sb.Append(']');
        return sb.ToString();
    }
}
