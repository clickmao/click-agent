using System.Text.Json.Serialization;

namespace agent.intent;



/// <summary>节点重试审计记录 (v7.15 FailRetry — /plan JSON 程序可解析)。</summary>
public class NodeRetryRecord
{
    public string NodeId { get; set; } = string.Empty;

    /// <summary>第几次重试 (1 起; 初次执行不计)</summary>
    public int Attempt { get; set; }

    /// <summary>被重试的那次失败原因</summary>
    public string? Error { get; set; }

    /// <summary>重试前退避等待毫秒</summary>
    public int WaitedMs { get; set; }

    /// <summary>记录时间 (UTC)</summary>
    public DateTime At { get; set; } = DateTime.UtcNow;
}
