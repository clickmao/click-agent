using System.Text.Json.Serialization;

namespace agent.intent;


/// <summary>
/// 单节点执行审计 (v0.22.0 exp9 D3)。"零 token 本地节点占了几个、省了多少" 的可测事实。
/// </summary>
public class NodeOutcome
{
    public string NodeId { get; set; } = string.Empty;

    /// <summary>位置文本 (local/hybrid/remote; 与 PlanNode.LocationText 同源)</summary>
    public string Location { get; set; } = "remote";

    /// <summary>本地执行器登记 Id (远程节点为 null)</summary>
    public string? ExecutorId { get; set; }

    public PlanNodeState State { get; set; }

    /// <summary>本节点消耗的模型 token (本地节点恒 0 — 这是"省 token"的原始证据)</summary>
    public long Tokens { get; set; }

    public long ElapsedMs { get; set; }

    /// <summary>节点产物路径 (本地真跑产物/远程落盘产物; 无则 null)</summary>
    public string? ArtifactPath { get; set; }

    /// <summary>结论摘要 (成功=简述; 失败=真实原因, 不静默)</summary>
    public string? Detail { get; set; }

    /// <summary>运行时依赖等待: 在等哪个节点的产出 (v0.22.0 exp9 D7; 非等待节点为 null)</summary>
    public string? WaitFor { get; set; }

    /// <summary>等待原因 (running/queued/user; 非等待节点为 null)</summary>
    public string? WaitReason { get; set; }
}
