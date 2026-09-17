using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.recovery;


/// <summary>
/// 恢复裁定结果: 中断的会话该从哪继续。
/// </summary>
public sealed class RecoveryPlan
{
    /// <summary>有可恢复的未完成计划?</summary>
    public bool Resumable { get; set; }

    public string PlanId { get; set; } = string.Empty;

    /// <summary>恢复起点节点 id (首个 Pending 节点; 全部完成 → 空串)</summary>
    public string ResumeFromNodeId { get; set; } = string.Empty;

    /// <summary>恢复起点前的已完成节点 (直接标记完成, 不重跑)</summary>
    public List<string> CompletedNodeIds { get; set; } = new();

    /// <summary>人类可读恢复说明 (/status JSON 可读)</summary>
    public string Summary { get; set; } = string.Empty;
}
