using System.Text.Json.Serialization;

namespace agent.intent;


/// <summary>
/// 用户插入指令 (循环执行中到达的新输入)。
/// 语义分级决定处置方式 — 不是所有插入都"加入循环":
/// Cancel/停止类立即生效; 修改类合并进图; 澄清类直接答复等待中的问询。
/// </summary>
public class InjectedInstruction
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N")[..8];

    public string Text { get; set; } = string.Empty;

    public InjectedInstructionKind Kind { get; set; }

    /// <summary>插入时正在运行的节点 (Cancel 时即被中断者)</summary>
    public string? TargetNodeId { get; set; }

    public DateTime InjectedAt { get; set; } = DateTime.UtcNow;
}
