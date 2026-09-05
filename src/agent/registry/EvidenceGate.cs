using agent.intent;
using agent.userinteraction;
using SubTask = agent.intent.IntentDecomposer.SubTask;
using ConfidenceFlags = agent.intent.IntentDecomposer.ConfidenceFlags;

namespace agent.registry;

/// <summary>
/// 证据门槛 (v7.13): 不可置信子任务 / 数据边界不清的子任务 →
/// 向发起者 (真实用户或上游 agent) 索要证据补充; 同时执行最大疑问数量限制。
///
/// 硬规则:
///   ① 疑问上限内: 高优先级问题优先问 (MissingParameter &gt; AmbiguousReference &gt; 其余), 按 GroupId 批量打包;
///   ② 超出上限: 不再问 — 取 SuggestedValues 首个兜底 (记 Trace, 不伪造"问过了");
///   ③ 全部问询走 ClarificationBatch (一次交互收全部答案) + DataType 校验。
/// 响应速度: 置信度评估是 IntentDecomposer 内纯规则 (微秒), 门槛分类也是纯规则 — 不调 LLM。
/// </summary>
public sealed class EvidenceGate
{
    /// <summary>单个证据请求: 待补充的子任务 + 问题集</summary>
    public sealed class EvidenceRequest
    {
        public required SubTask SubTask { get; init; }
        public required List<ClarificationItem> Questions { get; init; }

        /// <summary>优先级: MissingParameter(0) &gt; AmbiguousReference(1) &gt; WeakIntent/TooVague(2) &gt; SuspiciousDependency(3)</summary>
        public int Priority => SubTask.Flags.HasFlag(ConfidenceFlags.MissingParameter) ? 0
            : SubTask.Flags.HasFlag(ConfidenceFlags.AmbiguousReference) ? 1
            : SubTask.Flags.HasFlag(ConfidenceFlags.WeakIntent | ConfidenceFlags.TooVague) ? 2
            : 3;
    }

    /// <summary>门槛裁定结果</summary>
    public sealed class GateResult
    {
        /// <summary>上限内、真正要问的问题 (已按优先级截断)</summary>
        public List<EvidenceRequest> ToAsk { get; } = new();

        /// <summary>超出上限被截断的子任务 (走 SuggestedValues 兜底, 不问)</summary>
        public List<SubTask> DroppedForLimit { get; } = new();

        /// <summary>置信度足够、不问</summary>
        public List<SubTask> Passed { get; } = new();
    }

    private readonly int _maxQuestions;
    private readonly double _confidenceThreshold;

    /// <param name="maxQuestions">最大疑问数量 (用户钦定限制; 默认 3)</param>
    /// <param name="confidenceThreshold">置信度阈值: 低于它才触发问询 (默认 0.60)</param>
    public EvidenceGate(int maxQuestions = 3, double confidenceThreshold = 0.60)
    {
        _maxQuestions = Math.Max(0, maxQuestions);
        _confidenceThreshold = confidenceThreshold;
    }

    /// <summary>
    /// 对拆解结果做门槛裁定 (纯规则): 挑出不可置信/数据边界不清的子任务并组证据请求。
    /// 数据边界不清的判定: AmbiguousReference (指代词) 或 SuspiciousDependency (疑似省略依赖)。
    /// </summary>
    public GateResult Evaluate(IReadOnlyList<SubTask> tasks)
    {
        var result = new GateResult();
        var candidates = new List<EvidenceRequest>();
        var questionBudget = _maxQuestions;

        // 按置信度升序 (最不可信的最优先), 同置信度按序号
        var suspects = tasks
            .Where(t => t.Confidence < _confidenceThreshold)
            .OrderBy(t => t.Confidence)
            .ThenBy(t => t.Order)
            .ToList();

        foreach (var task in suspects)
        {
            var questions = BuildQuestions(task);
            if (questions.Count == 0)
            {
                // 无可问的 — 直接兜底判定 (不浪费预算)
                continue;
            }

            if (questionBudget >= questions.Count)
            {
                candidates.Add(new EvidenceRequest { SubTask = task, Questions = questions });
                questionBudget -= questions.Count;
            }
            else
            {
                result.DroppedForLimit.Add(task);
            }
        }

        // 已通过预算的按优先级排 (MissingParameter 最优先问)
        result.ToAsk.AddRange(candidates.OrderBy(r => r.Priority).ThenBy(r => r.SubTask.Order));
        result.Passed.AddRange(tasks.Where(t => t.Confidence >= _confidenceThreshold));

        return result;
    }

    /// <summary>
    /// 为不可信子任务生成证据补充问题 (含 DataType 约束, 走批量问询协议)。
    /// 问题必须具体: 问什么、为什么、给出选项/类型。
    /// </summary>
    private static List<ClarificationItem> BuildQuestions(SubTask task)
    {
        var items = new List<ClarificationItem>();

        if (task.Flags.HasFlag(ConfidenceFlags.MissingParameter))
        {
            items.Add(new ClarificationItem
            {
                NodeId = $"subtask-{task.Order}",
                ParameterName = $"子任务{task.Order + 1}_缺失参数",
                Question = $"「{task.Text}」缺少执行所需的参数 (目标对象/路径/范围)。请补充。",
                DataType = PromptDataType.String,
                Authority = "MainAgentAllowed",
            });
        }

        if (task.Flags.HasFlag(ConfidenceFlags.AmbiguousReference))
        {
            items.Add(new ClarificationItem
            {
                NodeId = $"subtask-{task.Order}",
                ParameterName = $"子任务{task.Order + 1}_指代对象",
                Question = $"「{task.Text}」中的指代 (这个/它/该文件) 具体指向什么? 请给出确切的文件/数据名。",
                DataType = PromptDataType.String,
                Authority = "MainAgentAllowed",
            });
        }

        if (task.Flags.HasFlag(ConfidenceFlags.SuspiciousDependency))
        {
            items.Add(new ClarificationItem
            {
                NodeId = $"subtask-{task.Order}",
                ParameterName = $"子任务{task.Order + 1}_数据来源",
                Question = $"「{task.Text}」要基于哪个前序结果? (若是上一步输出, 可直接确认)",
                DataType = PromptDataType.Choice,
                Choices = ["上一步的输出结果", "另指定的数据", "不需要输入数据"],
                Authority = "MainAgentAllowed",
            });
        }

        if (items.Count == 0 &&
            (task.Flags.HasFlag(ConfidenceFlags.WeakIntent) ||
             task.Flags.HasFlag(ConfidenceFlags.TooVague)))
        {
            items.Add(new ClarificationItem
            {
                NodeId = $"subtask-{task.Order}",
                ParameterName = $"子任务{task.Order + 1}_意图确认",
                Question = $"「{task.Text}」意图不明确。你想让 agent 做什么? (如: 搜索/写文档/执行命令/分析数据)",
                DataType = PromptDataType.Choice,
                Choices = ["搜索资料", "写文档/总结", "执行代码/命令", "分析数据", "读文件", "其他 (请补充说明)"],
                Authority = "MainAgentAllowed",
            });
        }

        // 同一子任务的问题归一组 — 批量问询协议要求
        var groupId = $"subtask-{task.Order}";
        foreach (var it in items)
            it.GroupId = groupId;

        return items;
    }
}
