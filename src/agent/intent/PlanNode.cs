namespace agent.intent;


/// <summary>计划节点 = 一个子任务</summary>
public class PlanNode
{

    /// <summary>本节点最大重试次数 (v7.15 FailRetry; null = 用 TaskPlan.DefaultMaxRetries)。</summary>
    public int? MaxRetries { get; set; }
    public string Id { get; set; } = "n" + Guid.NewGuid().ToString("N")[..8];

    /// <summary>子任务原文片段</summary>
    public string Text { get; set; } = string.Empty;

    /// <summary>识别意图 (IntentRecognizer.Intents 常量)</summary>
    public string Intent { get; set; } = IntentRecognizer.Intents.General;

    /// <summary>依赖的前序节点 Id (空 = 无依赖, 可最先执行)</summary>
    public List<string> DependsOn { get; set; } = new();

    /// <summary>拓扑层级 (root=0); 同层节点之间无依赖 → 可并行</summary>
    public int Level { get; set; }

    /// <summary>子任务参数槽 (缺失且必填 → NeedsClarification)</summary>
    public List<TaskParameter> Parameters { get; set; } = new();

    /// <summary>待澄清条目 (非空 → 该节点暂不可执行)</summary>
    public List<ClarificationItem> Clarifications { get; set; } = new();

    /// <summary>
    /// 澄清已结清 (v0.22.0 exp9 D7b 续跑专用): 用户已答复过本节点的澄清 → 证据门槛**不得**再问一遍。
    /// 续跑时 Clarifications 被清空 (答案写回参数槽), 若不记这个标记, 门槛会按同一低置信度重新提问
    /// ⇒ 用户被反复问同一句。false = 老行为 (未结清)。
    /// </summary>
    public bool ClarificationsSettled { get; set; }

    /// <summary>参数齐备 + 依赖可满足 → 调度器可立即异步执行</summary>
    public bool IsExecutable => Clarifications.Count == 0;

    /// <summary>并行组号 (同 level 且互不依赖共享组号; UI 可按组着色)</summary>
    public int ParallelGroup { get; set; }

    /// <summary>对应设计/开发文档路径 (相对仓库根, 如 docs/archive/plan_model_queue.md)。
    /// 开发计划型任务节点标注其模块文档; 日常用户任务无文档时为 null。AOT 纯数据字段。</summary>
    public string? DocRef { get; set; }

    /// <summary>
    /// 形式化断言契约 (v0.23.0 exp12 S2): 本节点的可判定片段文本 —— 逐行 `premise &lt;expr&gt;` / `goal &lt;expr&gt;`,
    /// 或显式弃权 `no_formal: &lt;理由&gt;`。语法与 agent.rover `check` 同构, 判定在**本机内核**完成(零 token)。
    /// 缺省 null = 未声明 ⇒ 闸门按「无形式化义务」放行, **绝不为此追问 LLM**。
    /// </summary>
    public string? Formal { get; set; }

    /// <summary>拆解置信度 (v7.13): EvidenceGate 裁定依据 (Builder 从 SubTask 透传)</summary>
    public double Confidence { get; set; } = 1.0;

    /// <summary>置信度扣分信号 (v7.13): 指代不清/弱意图/缺参数等 (Builder 从 SubTask 透传)</summary>
    public IntentDecomposer.ConfidenceFlags ConfidenceFlags { get; set; }
        = IntentDecomposer.ConfidenceFlags.None;

    /// <summary>执行位置 (v0.22.0 exp9 D1): 由 PlanRoutePolicy 确定性判定写回, 不由 LLM 决定。
    /// 默认 Remote 是**保守**缺省 (未判定 = 不许乐观当本地可跑)。</summary>
    public NodeExecutionLocation Location { get; set; } = NodeExecutionLocation.Remote;

    /// <summary>本地执行器登记 Id (Location != Remote 时非空; 取 LocalExecutorRegistry 已接线项)</summary>
    public string? LocalExecutorId { get; set; }

    /// <summary>判定依据短句 (前端展示"为什么这步能本地跑"; 规则给出的事实, 非模型自述)</summary>
    public string? LocalHint { get; set; }

    /// <summary>位置文本 (UI/事件契约用; 枚举数值不进前端契约)</summary>
    public string LocationText => Location switch
    {
        NodeExecutionLocation.Local => "local",
        NodeExecutionLocation.Hybrid => "hybrid",
        _ => "remote",
    };

    /// <summary>是否可零 token 本地执行 (调度器据此决定是否先行/并发)</summary>
    public bool RunsLocally =>
        Location != NodeExecutionLocation.Remote && !string.IsNullOrEmpty(LocalExecutorId);

    /// <summary>
    /// 运行时依赖 (v0.22.0 exp9 D7): 执行中才发现"需要另一节点的产出"。由调度器在等待解决后写入,
    /// 输入解析优先取这些节点 (晚绑定)。与 <see cref="DependsOn"/> 的区别: 后者是**建计划时**声明的,
    /// 前者是**执行时**发现的 —— 两者语义相同: 必须等它产出, 不许伪造/静默兜底。
    /// </summary>
    public List<string> RuntimeDeps { get; set; } = [];

    /// <summary>
    /// 本节点是否为「用户原文级本地子请求」(v0.22.0 exp9 D4b)。
    /// 语义: **整段子请求**就是"在用户自己的原文上做文本处理" —— 框架确定性可算, 无需模型参与。
    /// 因此该子请求必须 ① 走 Local 执行 ② 从**模型出站文本扣减** (RequestAblation)
    /// ③ 由框架把本地结论自渲染进回复 (PlanLocalAnswer)。
    /// 不给扣减 = 模型会把同一步再算一遍 (真机实测: 模型算 118 / 框架算 117) ⇒ 零 token 收益被吃掉。
    /// 与 Location/Hint 同源: 由 PlanRoutePolicy 写回, 不许上游手填。
    /// </summary>
    public bool IsLocalizedRequest { get; set; }
}
