namespace agent.intent;

/// <summary>
/// 任务计划模型 (v7.10): 拆解结果的图结构化表达。
/// 双消费者: ①调度器 (依赖图 → 可并行子任务判定) ②外部 UI (JSON 绘制)。
/// 序列化必须走 TaskPlanJsonContext (AOT source-gen, 禁反射)。
/// </summary>
public class TaskPlan
{

    /// <summary>同层最大并发节点数 (v7.15 执行器并发化; 1 = 完全串行等价旧行为)。</summary>
    public int MaxParallelism { get; set; } = 4;

    /// <summary>节点级默认重试次数 (v7.15 FailRetry; PlanNode.MaxRetries 未显式设置时用此值)。</summary>
    public int DefaultMaxRetries { get; set; } = 0;
    public string PlanId { get; set; } = Guid.NewGuid().ToString("N")[..12];

    /// <summary>原始用户输入</summary>
    public string SourceText { get; set; } = string.Empty;

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public List<PlanNode> Nodes { get; set; } = new();

    /// <summary>整计划是否还有待用户澄清的参数 (true → 调度器不得直接执行)</summary>
    public bool HasPendingClarifications => Nodes.Any(n => n.Clarifications.Count > 0);

    /// <summary>当前可立即执行 (参数齐备且依赖已就绪) 的节点 Id — 调度器异步并行入口</summary>
    public List<string> ExecutableNodeIds =>
        Nodes.Where(n => n.IsExecutable).Select(n => n.Id).ToList();

    /// <summary>拓扑层级 (0 = 无依赖根层) — UI 分层布局用; 同层节点可并行</summary>
    public int MaxLevel => Nodes.Count > 0 ? Nodes.Max(n => n.Level) : 0;

    /// <summary>可零 token 本地执行的节点 Id (v0.22.0 exp9 D1): 调度器"本地先行"的候选集</summary>
    public List<string> LocalExecutableNodeIds =>
        Nodes.Where(n => n.RunsLocally).Select(n => n.Id).ToList();

    /// <summary>需远程生成的节点 Id (v0.22.0 exp9 D1): 本地无法产出, 必须走模型</summary>
    public List<string> RemoteNodeIds =>
        Nodes.Where(n => n.Location == NodeExecutionLocation.Remote).Select(n => n.Id).ToList();

    /// <summary>用户原文级本地子请求 (v0.22.0 exp9 D4b): 这些子请求的原文片段**必须从模型出站文本扣减**</summary>
    public List<PlanNode> LocalizedRequestNodes =>
        Nodes.Where(n => n.IsLocalizedRequest).ToList();
}
