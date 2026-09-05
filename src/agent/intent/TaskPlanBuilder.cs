using System.Text.Json;
using System.Text.Json.Serialization;
using agent.userinteraction;

namespace agent.intent;

/// <summary>
/// TaskPlan 构建器 (v7.10): 拆解结果 → 参数化图 (问询节点 + 依赖层级 + 并行组)。
/// </summary>
public static class TaskPlanBuilder
{
    /// <summary>
    /// 意图 → 参数槽模板。Value=null 且 IsRequired=true 的槽触发问询。
    /// 模板裁剪原则: 只声明真正影响执行的参数, 不做形式化凑数。
    /// </summary>
    private static readonly Dictionary<string, List<TaskParameter>> ParameterTemplates = new(StringComparer.Ordinal)
    {
        [IntentRecognizer.Intents.GitOperation] =
        [
            new TaskParameter
            {
                Name = "branch", DisplayName = "目标分支", IsRequired = false,
                SuggestedValues = ["main", "当前分支"]
            },
        ],
        [IntentRecognizer.Intents.FileOperation] =
        [
            new TaskParameter
            {
                Name = "path", DisplayName = "目标路径", IsRequired = true,
            },
        ],
        [IntentRecognizer.Intents.CodeGeneration] =
        [
            new TaskParameter
            {
                Name = "language", DisplayName = "目标语言", IsRequired = false,
                SuggestedValues = ["csharp", "python", "typescript"],
            },
        ],
    };

    /// <summary>构建计划图: 拆解 → 参数槽 → 澄清节点 → 层级/并行组计算</summary>
    public static TaskPlan Build(string sourceText, IReadOnlyList<IntentDecomposer.SubTask> subTasks)
    {
        var plan = new TaskPlan { SourceText = sourceText };
        var idByOrder = new List<string>();

        foreach (var st in subTasks)
        {
            var node = new PlanNode
            {
                Text = st.Text,
                Intent = st.Intent,
                Confidence = st.Confidence,             // v7.13: 证据门槛裁定依据
                ConfidenceFlags = st.Flags,
            };

            // 依赖接线 (v7.12 关系分级):
            //   DependsOnOutput (基于/根据) → 数据依赖紧邻前序
            //   Sequential (然后/接着)     → 依赖紧邻前序 (保执行序)
            //   Parallel (同时/以及)       → 不接线 (同层并行组)
            if ((st.Relation == IntentDecomposer.TaskRelation.DependsOnOutput ||
                 st.Relation == IntentDecomposer.TaskRelation.Sequential) &&
                idByOrder.Count > 0)
            {
                node.DependsOn.Add(idByOrder[^1]);
            }

            // 参数槽填充
            if (ParameterTemplates.TryGetValue(st.Intent, out var template))
            {
                foreach (var t in template)
                    node.Parameters.Add(CloneParameter(t));
            }

            CollectClarifications(node);
            plan.Nodes.Add(node);
            idByOrder.Add(node.Id);
        }

        ComputeLevelsAndParallelGroups(plan);
        return plan;
    }

    /// <summary>用户答复澄清后调用: 填参 → 重算可执行性 (不改层级, 依赖不变)</summary>
    public static void ApplyClarificationAnswer(TaskPlan plan, string nodeId, string parameterName, string value)
    {
        var node = plan.Nodes.FirstOrDefault(n => n.Id == nodeId);
        if (node == null)
            return;

        var p = node.Parameters.FirstOrDefault(x => x.Name == parameterName);
        if (p == null)
            return;

        p.Value = value;
        node.Clarifications.RemoveAll(c => c.ParameterName == parameterName);
    }

    /// <summary>运行中新指令合并: 拆解插入文本 → 新节点追加进图 (依赖当前执行到的前序)</summary>
    public static PlanNode MergeInstruction(TaskPlan plan, string instructionText, string? afterNodeId)
    {
        var subTasks = IntentDecomposer.Decompose(instructionText);
        PlanNode? last = null;
        foreach (var st in subTasks)
        {
            var node = new PlanNode
            {
                Text = st.Text,
                Intent = st.Intent,
                Confidence = st.Confidence,
                ConfidenceFlags = st.Flags,
            };
            if (st.DependsOnPrevious && last != null)
                node.DependsOn.Add(last.Id);
            else if (afterNodeId != null)
                node.DependsOn.Add(afterNodeId);

            if (ParameterTemplates.TryGetValue(st.Intent, out var template))
            {
                foreach (var t in template)
                    node.Parameters.Add(CloneParameter(t));
            }

            CollectClarifications(node);
            plan.Nodes.Add(node);
            last = node;
        }

        ComputeLevelsAndParallelGroups(plan);
        return last ?? throw new InvalidOperationException("合并指令未产生节点");
    }

    /// <summary>拓扑层级 + 并行组: 同层无依赖 → 同组可异步并行</summary>
    public static void ComputeLevelsAndParallelGroups(TaskPlan plan)
    {
        var byId = plan.Nodes.ToDictionary(n => n.Id, StringComparer.Ordinal);
        var levelCache = new Dictionary<string, int>(StringComparer.Ordinal);

        int LevelOf(PlanNode n)
        {
            if (levelCache.TryGetValue(n.Id, out var cached))
                return cached;
            var level = 0;
            foreach (var depId in n.DependsOn)
            {
                if (byId.TryGetValue(depId, out var dep))
                    level = Math.Max(level, LevelOf(dep) + 1);
            }
            levelCache[n.Id] = level; // 拆解链是线性的, 无环; 防御性缓存同时避免重复计算
            return level;
        }

        foreach (var n in plan.Nodes)
            n.Level = LevelOf(n);

        // 并行组: 同层内每个节点独立成组号 (层号即组基线; 同层节点天然互不依赖)
        foreach (var n in plan.Nodes)
            n.ParallelGroup = n.Level;
    }

    /// <summary>公开重算入口: 运行时手工增删参数槽后刷新澄清状态</summary>
    public static void RecalculateClarifications(PlanNode node) => CollectClarifications(node);

    /// <summary>参数槽 → 澄清条目 (必填且无值 → 问询)</summary>
    private static void CollectClarifications(PlanNode node)
    {
        node.Clarifications.Clear();
        foreach (var p in node.Parameters)
        {
            if (!p.IsRequired || p.Value != null)
                continue;

            node.Clarifications.Add(new ClarificationItem
            {
                Kind = p.IsSensitive ? ClarificationKinds.ApiKey : ClarificationKinds.MissingParameter,
                NodeId = node.Id,
                ParameterName = p.Name,
                Question = BuildQuestion(node, p),
                Authority = p.IsSensitive ? "RealUserOnly" : "MainAgentAllowed",
                SuggestedValues = p.SuggestedValues,
            });
        }
    }

    private static string BuildQuestion(PlanNode node, TaskParameter p) =>
        $"子任务「{node.Text}」({node.Intent}) 需要知道 {p.DisplayName}; " +
        "不提供该参数则此子任务将保持等待, 其余子任务不受影响。";

    private static TaskParameter CloneParameter(TaskParameter t) => new()
    {
        Name = t.Name,
        DisplayName = t.DisplayName,
        IsRequired = t.IsRequired,
        IsSensitive = t.IsSensitive,
        SuggestedValues = new List<string>(t.SuggestedValues),
    };
}

/// <summary>
/// TaskPlan → JSON (外部 UI 绘制契约)。
/// AOT: source-gen JsonContext, 禁反射序列化 (v7.3 教训: 裸泛型 Serialize 触发 IL3050)。
/// </summary>
[JsonSerializable(typeof(TaskPlan))]
[JsonSerializable(typeof(PlanNode))]
[JsonSerializable(typeof(TaskParameter))]
[JsonSerializable(typeof(ClarificationItem))]
[JsonSerializable(typeof(TaskPlanRun))]
[JsonSerializable(typeof(InjectedInstruction))]
[JsonSerializable(typeof(NodeRetryRecord))]
[JsonSourceGenerationOptions(WriteIndented = true, DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull)]
public partial class TaskPlanJsonContext : JsonSerializerContext
{
    /// <summary>UI 绘制契约: 结构化 JSON (节点+依赖+层级+并行组+问询)</summary>
    public static string ToJson(TaskPlan plan) =>
        JsonSerializer.Serialize(plan, typeof(TaskPlan), Default);

    /// <summary>运行时状态 JSON (节点状态/插入指令/暂停原因 — UI 轮询刷新用)</summary>
    public static string ToJson(TaskPlanRun run) =>
        JsonSerializer.Serialize(run, typeof(TaskPlanRun), Default);
}
