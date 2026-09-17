using System.Text.Json.Serialization;

namespace agent;

/// <summary>模型队列指令 JSON 载荷 (v7.15: /model 与 /balance 输出 — source-gen AOT fast-path 铁律)</summary>
public sealed class ModelCommandPayload
{
    public string Command { get; set; } = string.Empty;
    public bool Ok { get; set; }
    public string? Active { get; set; }
    public string? Provider { get; set; }
    public int ReasoningScore { get; set; }
    public int CodingScore { get; set; }
    public string? LastSelection { get; set; }
    public int Switches { get; set; }
    public string? Target { get; set; }
    public int HttpStatusCode { get; set; }
    public string? Verdict { get; set; }
    public double? TotalGranted { get; set; }
    public double? TotalUsed { get; set; }
    public double? TotalRemaining { get; set; }
    public string? Error { get; set; }
    public string? Note { get; set; }

    /// <summary>需求1: 官方通道 key 是否已注入 (true/false — 不回显 key 本身)</summary>
    public bool? OfficialKeyPresent { get; set; }

    /// <summary>/model list: 可用模型条目 (序号 1-N, 序号可直接用于 /model &lt;序号&gt; 指定)</summary>
    public List<ModelListItem>? Models { get; set; }

    /// <summary>当前执行模式: auto (智能选模, 默认) / manual (用户指定模型)</summary>
    public string? Mode { get; set; }
}
