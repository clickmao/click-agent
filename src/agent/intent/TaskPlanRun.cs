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

/// <summary>
/// 单次运行时依赖等待 (v0.22.0 exp9 D7)。
/// Reason 语义 (确定性取值, 前端直接显示):
/// - `running`: 生产节点在本轮已启动, 尚未产出;
/// - `queued`: 生产节点尚未启动 (层级在后 / 并发额度未轮到);
/// - `user`: 生产节点在等用户澄清/审批 —— 它的产出依赖用户回复 (跨轮场景, 见 §12 D7b 边界)。
/// </summary>
public sealed record NodeWaitRecord(
    string NodeId,
    string ProducerId,
    string Reason,
    long StartedUs)
{
    /// <summary>唤醒时刻 (未唤醒为 null)</summary>
    public long? EndedUs { get; set; }

    /// <summary>等待时长 (微秒; 未唤醒为 null)</summary>
    public long? WaitUs => EndedUs is null ? null : EndedUs - StartedUs;
}

/// <summary>
/// 计划级 KPI (v0.22.0 exp9 D6)。单位: ms / 个 / token。
/// 语义:
/// - LocalFirstNodes/LocalFirstMs: **无依赖本地节点**的个数与其自身墙钟耗时 (远程产物未就绪前就跑完的部分);
/// - OverlapMs: 本地先行与"远程等待期"的**真重叠**时长 (0 = 假并行, 只是先后排列);
/// - RemoteWaitMs: 远程等待期总长 (计划构建 → 产物就绪);
/// - LocalTokens: 本地节点消耗的模型 token (恒 0 —— 这是"省 token"的原始证据, 不是估计值)。
/// </summary>
public sealed record PlanKpi(
    int Nodes,
    int LocalNodes,
    int RemoteNodes,
    int HybridNodes,
    int LocalFirstNodes,
    int LocalFirstMs,
    int OverlapMs,
    int RemoteWaitMs,
    long LocalFirstUs,
    long OverlapUs,
    long RemoteWaitUs,
    long LocalTokens,
    int WaitNodes,
    long WaitUs,
    int ElapsedMs);

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

/// <summary>计划运行状态</summary>
public enum TaskPlanRunState
{
    /// <summary>执行中 (可被注入指令合并、被敏感节点暂停)</summary>
    Running,

    /// <summary>敏感节点等待用户审批 — 全计划暂停 (不可跳过继续)</summary>
    PausedForApproval,

    /// <summary>全部节点终态 (Completed/Failed/Skipped)</summary>
    Finished,

    /// <summary>
    /// 存在节点在等另一节点的产出, 而该生产节点在等用户 (澄清/审批) (v0.22.0 exp9 D7)。
    /// 本轮到此为止: 不许伪造数据硬跑 —— 用户回复后重跑 (跨轮唤醒 D7b 见计划 §12 边界)。
    /// </summary>
    PausedForDependency,

    /// <summary>用户或策略取消 (未完成节点标记 Skipped)</summary>
    Cancelled,
}

/// <summary>节点运行状态</summary>
public enum PlanNodeState
{
    Pending,

    /// <summary>
    /// 等待其它节点产出 (v0.22.0 exp9 D7 运行时依赖): A 跑到中途发现要用 B 的产出, 而 B 尚未产出
    /// (在跑 / 在等用户澄清) ⇒ A 进本状态, **不消费输入、不伪造数据、不静默降级**。
    /// 生产节点落终态后由调度器唤醒 (详情见 TaskPlanRun.Waits)。
    /// </summary>
    Waiting,

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
