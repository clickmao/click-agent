using System.Text.Json.Serialization;

namespace agent.intent;

/// <summary>
/// 任务计划运行时状态 (v7.10): 计划在循环执行中的生命周期。
/// 图结构 (TaskPlan) 是静态蓝图; TaskPlanRun 是它的运行时实例 —
/// 节点状态迁移、用户插入指令的合并、敏感任务的暂停点都在这里。
/// </summary>
public class TaskPlanRun
{

    /// <summary>重试审计 (v7.15 FailRetry): 每次重试一条, /plan JSON 输出 (程序可解析)。</summary>
    public List<NodeRetryRecord> Retries { get; set; } = new();
    public string RunId { get; set; } = Guid.NewGuid().ToString("N")[..12];

    public string PlanId { get; set; } = string.Empty;

    public TaskPlanRunState State { get; set; } = TaskPlanRunState.Running;

    /// <summary>节点运行状态 (NodeId → 状态)</summary>
    public Dictionary<string, PlanNodeState> NodeStates { get; set; } = new();

    /// <summary>用户插入的新指令 (循环执行中到达) — 待合并进计划</summary>
    public List<InjectedInstruction> InjectedInstructions { get; set; } = new();

    /// <summary>暂停原因 (State=PausedForApproval 时必填)</summary>
    public string? PauseReason { get; set; }

    /// <summary>等待审批的敏感节点 (State=PausedForApproval 时非空)</summary>
    public string? PendingSensitiveNodeId { get; set; }

    /// <summary>证据疑问超限节点 (v7.13): 低置信但疑问数已达上限, 走兜底不静默 (编排层可见)</summary>
    public List<string> DroppedForEvidenceLimit { get; set; } = new();

    /// <summary>节点执行审计 (v0.22.0 exp9 D3/D6): 每节点一条 — 位置/执行器/耗时/token/产物。
    /// 前端事件 (D5) 与 KPI 打点 (D6) 都读这里, 不各自猜。</summary>
    public List<NodeOutcome> Outcomes { get; set; } = new();

    /// <summary>计划级 KPI (v0.22.0 exp9 D6): 前端事件 / 同题对照脚本 / 遥测三处**同一份数字**,
    /// 不许各自重算 (重算 = 口径漂移的来源)。</summary>
    public PlanKpi? Kpi { get; set; }

    /// <summary>
    /// 运行时依赖等待台账 (v0.22.0 exp9 D7): NodeId → 等待记录。空 = 本轮没有节点在等别人。
    /// 这是"等待"说法的唯一事实源: 状态 (NodeStates=Waiting) 只说"在等", 这里说"等谁、为什么、等多久"。
    /// </summary>
    public Dictionary<string, NodeWaitRecord> Waits { get; set; } = new(StringComparer.Ordinal);

    public DateTime StartedAt { get; set; } = DateTime.UtcNow;
}
