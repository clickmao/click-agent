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

    public DateTime StartedAt { get; set; } = DateTime.UtcNow;
}

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
}

/// <summary>计划运行状态</summary>
public enum TaskPlanRunState
{
    /// <summary>执行中 (可被注入指令合并、被敏感节点暂停)</summary>
    Running,

    /// <summary>敏感节点等待用户审批 — 全计划暂停 (不可跳过继续)</summary>
    PausedForApproval,

    /// <summary>全部节点终态 (Completed/Failed/Skipped)</summary>
    Finished,

    /// <summary>用户或策略取消 (未完成节点标记 Skipped)</summary>
    Cancelled,
}

/// <summary>节点运行状态</summary>
public enum PlanNodeState
{
    Pending,
    AwaitingClarification,
    AwaitingApproval,
    Running,
    Completed,
    Failed,
    Skipped,
}

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

/// <summary>插入指令语义分级</summary>
public enum InjectedInstructionKind
{
    /// <summary>停止/取消: 立即中断当前节点与计划 (敏感词判定 + 显式指令)</summary>
    Cancel,

    /// <summary>敏感暂停请求: 用户要求在危险步骤前停下确认</summary>
    RequestApproval,

    /// <summary>新子任务: 拆解后合并进运行中的图 (新节点 + 依赖接线)</summary>
    NewTask,

    /// <summary>参数补充: 直接答复等待中的问询节点</summary>
    ClarificationAnswer,

    /// <summary>约束修改: 改变未开始节点的执行方式 (如 "别用 npm 用 pnpm")</summary>
    ConstraintUpdate,
}

/// <summary>
/// 插入指令分类器: 文本 → 语义分级。
/// 显式停止指令与敏感词在这里判定 (工业规则: 停止指令永远生效, 不需要问询)。
/// </summary>
public static class InjectedInstructionClassifier
{
    private static readonly string[] CancelMarkers =
    [
        "停止", "取消", "停下", "别做了", "终止", "中止", "撤销",
        "stop", "cancel", "abort", "halt"
    ];

    private static readonly string[] ApprovalMarkers =
    [
        "先停下确认", "问过我", "先问我", "暂停确认", "需要我确认",
        "ask me first", "confirm with me", "pause before"
    ];

    /// <summary>敏感意图集合: 这些意图的节点默认需要审批 (非全托管模式)</summary>
    private static readonly HashSet<string> SensitiveIntents = new(StringComparer.Ordinal)
    {
        IntentRecognizer.Intents.FileOperation,   // 删除/移动文件不可逆
        IntentRecognizer.Intents.GitOperation,    // push/reset 影响远端
    };

    public static bool IsCancel(string text)
    {
        foreach (var m in CancelMarkers)
        {
            if (text.Contains(m, StringComparison.OrdinalIgnoreCase))
                return true;
        }
        return false;
    }

    public static bool IsApprovalRequest(string text)
    {
        foreach (var m in ApprovalMarkers)
        {
            if (text.Contains(m, StringComparison.OrdinalIgnoreCase))
                return true;
        }
        return false;
    }

    public static bool IsSensitiveIntent(string intent) => SensitiveIntents.Contains(intent);

    /// <summary>分类入口 (顺序: 取消 > 审批请求 > 其余按内容拆解定性)</summary>
    public static InjectedInstructionKind Classify(string text)
    {
        if (IsCancel(text))
            return InjectedInstructionKind.Cancel;
        if (IsApprovalRequest(text))
            return InjectedInstructionKind.RequestApproval;
        return InjectedInstructionKind.NewTask;
    }
}


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
