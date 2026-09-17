using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.logging;

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
