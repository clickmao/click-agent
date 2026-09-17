using agent.intent;
using agent.core;

namespace agent.registry;

public class NodeExecutionResult
{
    public string NodeId { get; init; } = string.Empty;

    public PlanNodeState FinalState { get; init; }

    /// <summary>节点产物 (当前版本 = LLM 响应文本; 后续接真实 handler)</summary>
    public string? Output { get; init; }

    public string? Error { get; init; }

    /// <summary>失败种类 (v7.15): 默认 Transient — nodeRunner 实现方负责细分, Unknown 按可重试处理</summary>
    public NodeFailureKind FailureKind { get; init; } = NodeFailureKind.Transient;

    /// <summary>
    /// 执行**中途**发现的运行时依赖 (v0.22.0 exp9 D7): 本节点需要该节点的产出才能继续。
    /// 配 FinalState=Waiting 返回 ⇒ 调度器记账等待, 生产节点就绪后**重跑本节点**(此时依赖已注入)。
    /// 不允许用它来"要一个不存在的节点": 未知 id 按 Pending 处理 → 收尾轮如实失败。
    /// </summary>
    public string? NeedNodeId { get; init; }
}
