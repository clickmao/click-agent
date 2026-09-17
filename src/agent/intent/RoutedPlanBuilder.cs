using System.Text.Json.Serialization;

namespace agent.intent;


/// <summary>
/// 计划构建门面 (v0.22.0 exp9 D1+D2 对外单入口):
/// Build → 路由判定 → 追加本地验证节点 → (可选) 序列化给前端。
/// 调用方只需记住这一个入口, 防"忘了调路由"的断链再现。
/// </summary>
public static class RoutedPlanBuilder
{
    /// <summary>构建带执行位置的计划 (幂等: 重复调用不会重复追加本地节点)</summary>
    public static TaskPlan Build(string sourceText, IReadOnlyList<IntentDecomposer.SubTask> subTasks)
    {
        var plan = TaskPlanBuilder.Build(sourceText, subTasks);

        // D4: 用户要求处理"**自己的原文**"时, 该文本动作单列为无依赖本地节点 (输入在手 ⇒ 可先于远程生成跑),
        //     且生成节点不再吸收它 (Hybrid 第二段输入是生成内容, 目标不同 ⇒ 不许混算)。
        var separateLocalText = LocalVerifyNodePlanner.AsksSourceTextOp(sourceText);
        var absorbLocalTextOp = !separateLocalText;

        PlanRoutePolicy.Apply(plan, absorbLocalTextOp);
        var before = plan.Nodes.Count;
        LocalVerifyNodePlanner.AppendFor(plan);
        if (separateLocalText)
            LocalVerifyNodePlanner.AppendSourceTextProcessor(plan, sourceText);
        if (plan.Nodes.Count != before)
            TaskPlanBuilder.ComputeLevelsAndParallelGroups(plan);
        PlanRoutePolicy.Apply(plan, absorbLocalTextOp);
        return plan;
    }
}
