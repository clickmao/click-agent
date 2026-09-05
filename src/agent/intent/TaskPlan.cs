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
}

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

    /// <summary>参数齐备 + 依赖可满足 → 调度器可立即异步执行</summary>
    public bool IsExecutable => Clarifications.Count == 0;

    /// <summary>并行组号 (同 level 且互不依赖共享组号; UI 可按组着色)</summary>
    public int ParallelGroup { get; set; }

    /// <summary>对应设计/开发文档路径 (相对仓库根, 如 docs/plan_model_queue.md)。
    /// 开发计划型任务节点标注其模块文档; 日常用户任务无文档时为 null。AOT 纯数据字段。</summary>
    public string? DocRef { get; set; }

    /// <summary>拆解置信度 (v7.13): EvidenceGate 裁定依据 (Builder 从 SubTask 透传)</summary>
    public double Confidence { get; set; } = 1.0;

    /// <summary>置信度扣分信号 (v7.13): 指代不清/弱意图/缺参数等 (Builder 从 SubTask 透传)</summary>
    public IntentDecomposer.ConfidenceFlags ConfidenceFlags { get; set; }
        = IntentDecomposer.ConfidenceFlags.None;
}

/// <summary>子任务参数槽 — 问询协议的拆解侧载体 (复用 AnswerAuthority 语义)</summary>
public class TaskParameter
{
    public string Name { get; set; } = string.Empty;

    /// <summary>给用户看的参数名 (如 "目标分支")</summary>
    public string DisplayName { get; set; } = string.Empty;

    /// <summary>已填充值 (null = 待澄清)</summary>
    public string? Value { get; set; }

    public bool IsRequired { get; set; } = true;

    /// <summary>敏感参数 (如 API Key) — 只走真实用户, 永不代答</summary>
    public bool IsSensitive { get; set; }

    /// <summary>推荐值 (UI 可显示为快捷选项)</summary>
    public List<string> SuggestedValues { get; set; } = new();
}

/// <summary>待澄清条目 — 问询请求的图内表达</summary>
public class ClarificationItem
{
    /// <summary>问询类型 flag (程序底层路由用; 与 CredentialRequestKind 语义对齐并扩展)</summary>
    public string Kind { get; set; } = ClarificationKinds.MissingParameter;

    /// <summary>哪个节点的哪个参数</summary>
    public string NodeId { get; set; } = string.Empty;

    public string ParameterName { get; set; } = string.Empty;

    /// <summary>给用户看的问题 (必须具体: 问什么、为什么需要、不填会怎样)</summary>
    public string Question { get; set; } = string.Empty;

    /// <summary>谁有权回答 (复用 agent.userinteraction 语义: RealUserOnly/MainAgentAllowed)</summary>
    public string Authority { get; set; } = "MainAgentAllowed";

    public List<string> SuggestedValues { get; set; } = new();

    /// <summary>答案数据类型约束 (v7.13): 回答必须通过 PromptDataValidator 校验</summary>
    public agent.userinteraction.PromptDataType DataType { get; set; } =
        agent.userinteraction.PromptDataType.String;

    /// <summary>Choice/MultiChoice 的完整选项列表 (选单选择必须给全所有选项)</summary>
    public List<string> Choices { get; set; } = new();

    /// <summary>批量分组键 (v7.13): 同组问询一次性打包给出, 不一条一条问</summary>
    public string GroupId { get; set; } = string.Empty;
}

/// <summary>澄清类型 flag 常量 (序列化友好; 凭据类沿用 CredentialRequestKind 语义字符串)</summary>
public static class ClarificationKinds
{
    public const string MissingParameter = "missing_parameter";
    public const string ApiKey = "api_key";
    public const string Endpoint = "endpoint";
    public const string ExternalToolPath = "external_tool_path";
    public const string AmbiguousIntent = "ambiguous_intent";
}
