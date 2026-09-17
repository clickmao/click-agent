using System.Text.Json;
using System.Text.Json.Serialization;
using agent.session;

namespace agent.registry;


/// <summary>会话恢复面板 (需求3: 检查点 → 恢复计划)</summary>
public sealed class RecoveryPanel
{
    public bool Resumable { get; set; }
    public string PlanId { get; set; } = string.Empty;
    public string ResumeFromNodeId { get; set; } = string.Empty;
    public int CompletedNodes { get; set; }
    public string Summary { get; set; } = string.Empty;
}
