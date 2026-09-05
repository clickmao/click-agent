using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.logging;

/// <summary>日志四位 flags (L.2.1 — 每条日志按 flags 一条路径路由, 不允许分叉实现)</summary>
public struct LogFlags
{
    /// <summary>显示到控制台</summary>
    public bool Console { get; set; }

    /// <summary>显示到 chatbox 思考页</summary>
    public bool ChatboxThinking { get; set; }

    /// <summary>显示到 chatbox 输出页</summary>
    public bool ChatboxOutput { get; set; }

    /// <summary>记录到日志 (缓存+存档文件)</summary>
    public bool File { get; set; }

    public static LogFlags All => new()
    {
        Console = true, ChatboxThinking = true, ChatboxOutput = true, File = true,
    };
}

/// <summary>日志通道 (thinking=思考流 / output=结果输出 / system=框架系统)</summary>
public enum LogChannel
{
    Thinking,
    Output,
    System,
}

/// <summary>
/// 日志条目内部底层格式 (v7.13 铁律: 一切返回内容都需要内部底层格式; L.3: 不含 Prompt 全文, 只有长度与摘要哈希)。
/// </summary>
public sealed class LogEntry
{
    /// <summary>ISO8601 时间戳</summary>
    public string Ts { get; set; } = string.Empty;

    /// <summary>trace/log level (info/warn/error/debug)</summary>
    public string Level { get; set; } = "info";

    /// <summary>通道</summary>
    public string Channel { get; set; } = "system";

    /// <summary>来源模块 (IndustrialAgentV2/TaskPlanExecutor/...)</summary>
    public string Module { get; set; } = string.Empty;

    /// <summary>消息本体</summary>
    public string Msg { get; set; } = string.Empty;

    /// <summary>会话 id (可空)</summary>
    public string? SessionId { get; set; }

    /// <summary>思考分片序号 (仅 thinking 通道; 供前端窗口化)</summary>
    public int Seq { get; set; }

    /// <summary>关联内容长度 (Prompt 全文不落日志, 只记长度)</summary>
    public int ContentLength { get; set; }

    /// <summary>关联内容摘要哈希 (FNV-1a 32bit hex)</summary>
    public string ContentHash { get; set; } = string.Empty;
}

/// <summary>前端协议指令 (L.2.2 — JSON 推送, 与 /status 同构)</summary>
public sealed class FrontendDirective
{
    /// <summary>thinking_page_switch / thinking_end</summary>
    public string Type { get; set; } = string.Empty;

    public string? SessionId { get; set; }

    /// <summary>thinking_page_switch: 当前分片 seq; thinking_end: 思考内容总长</summary>
    public int Seq { get; set; }

    /// <summary>thinking_end: 思考摘要长度 (前端折叠展示用)</summary>
    public int SummaryLength { get; set; }
}

[System.Text.Json.Serialization.JsonSerializable(typeof(LogEntry))]
[System.Text.Json.Serialization.JsonSerializable(typeof(FrontendDirective))]
[System.Text.Json.Serialization.JsonSourceGenerationOptions(
    DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull)]
public partial class LogJsonContext : System.Text.Json.Serialization.JsonSerializerContext
{
}
