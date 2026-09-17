using System.Text.Json.Serialization;

namespace agent.intent;


/// <summary>
/// 本地验证节点规划器 (v0.22.0 exp9 D2) —— 为"远程生成产物"的节点追加**确定性**本地节点。
///
/// 为什么不是"为编排而编排": 这些节点对应的正是过去由人工/探针在环外做的事
/// (落盘后跑 --selftest、汇总证据), 现在变成计划内、零 token、可观测的一等节点。
/// 硬约束: 只追加 LocalExecutorRegistry 中 **Wired=true** 的执行器节点 —— 未接线的能力不会被写进计划。
/// </summary>
public static class LocalVerifyNodePlanner
{
    /// <summary>需要产后本地验证的生成类意图 (产物型)</summary>
    private static readonly HashSet<string> ArtifactProducingIntents = new(StringComparer.Ordinal)
    {
        IntentRecognizer.Intents.CodeGeneration,
        IntentRecognizer.Intents.CodeModification,
        IntentRecognizer.Intents.TestGeneration,
    };

    /// <summary>
    /// 代码/脚本类任务标记 (确定性, 非 LLM 判定)。
    /// 依据 = 静态前缀契约本身: 产物型任务必须落盘可执行脚本且带 `--selftest` 无头入口
    /// (`SessionBaseline.cs:53`), 因此"这步产后必然有一个可本地跑的产物"是**框架已知事实**, 不是猜测。
    /// </summary>
    private static readonly string[] CodeTaskMarkers =
    [
        "python", "py脚本", "脚本", "程序", "代码", "函数", "算法", "游戏", "game", "script",
        "贪吃蛇", "扫雷", "俄罗斯方块", "命令行", "cli",
    ];

    internal static bool LooksLikeCodeTask(string? text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return false;
        var t = text.ToLowerInvariant();
        return CodeTaskMarkers.Any(m => t.Contains(m, StringComparison.Ordinal));
    }

    /// <summary>
    /// 为计划追加本地节点 (幂等)。
    /// 触发 = 产物型意图 **或** 文本是代码/脚本类任务; 追加内容 = **只追加有消费方的节点**: 本地跑 --selftest
    /// 取退出码 (消费方 = 计划审计/前端/验收判据)。
    /// 刻意不追加"证据文本汇总"这类无消费方节点 —— 无消费方 = 为编排而编排 (见计划 §4 约束 1/5)。
    /// </summary>
    public static IReadOnlyList<PlanNode> AppendFor(TaskPlan plan)
    {
        var added = new List<PlanNode>();
        if (!LocalExecutorRegistry.IsWired(LocalExecutorRegistry.PythonSelfTest))
            return added;

        // 快照遍历: 追加过程中会改 Nodes
        foreach (var gen in plan.Nodes.ToArray())
        {
            // 只给"需要模型产内容"的节点追加验证节点:
            //   · 框架自产的本地节点 (verify_local/text_processing) 不再被追加 (防"验证的验证"递归)
            //   · 已判 Local/Hybrid 的节点其本地半段已由其自身承担
            if (gen.Intent is PlanNodeIntents.VerifyLocal or PlanNodeIntents.TextProcessing)
                continue;
            if (gen.Location != NodeExecutionLocation.Remote)
                continue;
            if (!ArtifactProducingIntents.Contains(gen.Intent) && !LooksLikeCodeTask(gen.Text))
                continue;

            // 幂等: 已有依赖它的同执行器验证节点 → 跳过
            if (HasNode(plan, gen.Id, LocalExecutorRegistry.PythonSelfTest))
                continue;

            var verify = new PlanNode
            {
                Text = $"本地跑「{gen.Text}」产物的无头自测 (--selftest) 取退出码",
                Intent = PlanNodeIntents.VerifyLocal,
                DependsOn = [gen.Id],
            };
            plan.Nodes.Add(verify);
            added.Add(verify);
        }

        if (added.Count > 0)
            TaskPlanBuilder.ComputeLevelsAndParallelGroups(plan);

        return added;
    }

    /// <summary>
    /// 用户是否要求对**自己的原文/需求**做本地可算的文本处理 (v0.22.0 exp9 D4)。
    /// 判定 = 动作词 ∧ 对象词 双命中 (确定性, 非 LLM 判定)。
    /// 为什么单列: 这类任务的输入 (用户原文) 在模型还没生成前就已在手 ⇒ 属**无依赖本地节点**,
    /// 可与远程生成**真并行先行**; 而"统计生成出来的代码行数"依赖远程产物, 是另一类 (Hybrid/验证节点)。
    /// </summary>
    private static readonly string[] SourceTextOpMarkers =
        ["统计", "计数", "字数", "行数", "词频", "摘要", "格式化", "汇总", "字符数", "词数"];

    private static readonly string[] SourceTextTargetMarkers =
        ["需求", "原文", "这段话", "我写", "我说的", "描述", "提示词", "输入文本", "问题描述", "本文"];

    internal static bool AsksSourceTextOp(string? sourceText)
    {
        if (string.IsNullOrWhiteSpace(sourceText))
            return false;
        return SourceTextOpMarkers.Any(m => sourceText.Contains(m, StringComparison.OrdinalIgnoreCase))
            && SourceTextTargetMarkers.Any(m => sourceText.Contains(m, StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>纯原文级文本处理子请求的最大字数 (超过则说明该片段还裹着别的诉求 ⇒ 不许整体扣减)</summary>
    internal const int PureSourceOpMaxChars = 60;

    /// <summary>
    /// 该节点是否为「纯原文级文本处理子请求」(v0.22.0 exp9 D4b, 纯函数):
    ///   ① 无依赖 (输入=本轮原文, 不需要任何前序产物)
    ///   ② 动作词 ∧ 原文对象词双命中 (AsksSourceTextOp —— 复用 D4 同一判据, 不另立口径)
    ///   ③ 非产物型 (无 python/脚本/游戏… 标记 ⇒ 不是"写一个统计字数的程序")
    ///   ④ 短句 (≤ PureSourceOpMaxChars ⇒ 整段就是这一步, 不是"写贪吃蛇并统计字数"这种混合诉求)
    /// 四条全中 ⇒ 框架可**独立完成**这一步: 走 Local 且从模型出站文本扣减。
    /// </summary>
    internal static bool IsPureSourceTextOp(string? text, int dependsOnCount)
    {
        if (dependsOnCount != 0 || !AsksSourceTextOp(text) || LooksLikeCodeTask(text))
            return false;
        return (text ?? string.Empty).Trim().Length <= PureSourceOpMaxChars;
    }

    /// <summary>
    /// 追加"无依赖本地文本处理"节点 (D4 本地先行的真实载体): 输入 = 本轮用户原文。
    /// 消费方 = 计划审计 / 前端事件 (D5) / KPI (D6) 与用户要的那个统计结果本身 —— 不是为编排而编排。
    /// 幂等: 已有同执行器的无依赖节点则不重复追加。
    /// </summary>
    public static IReadOnlyList<PlanNode> AppendSourceTextProcessor(TaskPlan plan, string sourceText)
    {
        var added = new List<PlanNode>();
        if (!LocalExecutorRegistry.IsWired(LocalExecutorRegistry.TextProcess))
            return added;
        if (!AsksSourceTextOp(sourceText))
            return added;
        if (plan.Nodes.Any(n => n.LocalExecutorId == LocalExecutorRegistry.TextProcess && n.DependsOn.Count == 0))
            return added;

        var preview = sourceText.Length <= 40 ? sourceText : sourceText[..40] + "…";
        var node = new PlanNode
        {
            Text = $"本地处理用户原文 (输入=本轮原文, 统计/汇总): {preview}",
            Intent = PlanNodeIntents.TextProcessing,
            DependsOn = [],
        };
        plan.Nodes.Add(node);
        added.Add(node);
        return added;
    }

    private static bool HasNode(TaskPlan plan, string dependsOnId, string executorId) =>
        plan.Nodes.Any(n => n.LocalExecutorId == executorId && n.DependsOn.Contains(dependsOnId));
}
