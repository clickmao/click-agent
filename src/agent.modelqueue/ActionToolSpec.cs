using System.Text;

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

    /// <summary>声明面全集 (名称白名单与执行面同源: <see cref="ActionToolDecl.Names"/>)。</summary>
    public static readonly ActionToolSpec[] All =
    {
        new(ActionToolDecl.ListDir, "列出工作区目录条目(相对路径/大小/类型)",
            "{\"type\":\"object\",\"properties\":{\"path\":{\"type\":\"string\",\"description\":\"相对工作区根的目录路径, 省略=根\"}},\"required\":[]}"),
        new(ActionToolDecl.ReadFile, "读取工作区文本文件",
            "{\"type\":\"object\",\"properties\":{\"path\":{\"type\":\"string\",\"description\":\"相对工作区根的文件路径\"},\"max_bytes\":{\"type\":\"integer\",\"description\":\"最大字节数(默认8192)\"}},\"required\":[\"path\"]}"),
        new(ActionToolDecl.WriteFile, "写入/覆盖工作区文本文件",
            "{\"type\":\"object\",\"properties\":{\"path\":{\"type\":\"string\",\"description\":\"相对工作区根的文件路径\"},\"content\":{\"type\":\"string\",\"description\":\"文件内容\"}},\"required\":[\"path\",\"content\"]}"),
        new(ActionToolDecl.RunCommand, "在工作区根执行一条命令并返回 stdout/stderr/退出码",
            "{\"type\":\"object\",\"properties\":{\"command\":{\"type\":\"string\",\"description\":\"命令原文\"},\"timeout_ms\":{\"type\":\"integer\",\"description\":\"超时毫秒(默认120000, 上限600000)\"}},\"required\":[\"command\"]}"),
        new(ActionToolDecl.DeleteFile, "删除工作区内的文件或目录(需人工审批; 未接入审批通道时一律拒绝)",
            "{\"type\":\"object\",\"properties\":{\"path\":{\"type\":\"string\",\"description\":\"相对工作区根的文件/目录路径\"}},\"required\":[\"path\"]}"),
    };

    /// <summary>Chat Completions 线格式 (与 R456 常量逐字节相同)。</summary>
    public static readonly string ChatToolsJson = Compose(flatten: false);

    /// <summary>Responses 线格式 (平铺; tools[i] 直接带 name/description/parameters)。</summary>
    public static readonly string ResponsesToolsJson = Compose(flatten: true);

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
