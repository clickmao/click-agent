using System.Text.Json;
using System.Text.Json.Serialization;
using agent.core;

namespace agent.intent;


/// <summary>
/// TaskPlan → JSON (外部 UI 绘制契约)。
/// AOT: source-gen JsonContext, 禁反射序列化 (v7.3 教训: 裸泛型 Serialize 触发 IL3050)。
/// </summary>
[JsonSerializable(typeof(TaskPlan))]
[JsonSerializable(typeof(PlanNode))]
[JsonSerializable(typeof(TaskParameter))]
[JsonSerializable(typeof(ClarificationItem))]
[JsonSerializable(typeof(TaskPlanRun))]
[JsonSerializable(typeof(PlanKpi))]
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

    /// <summary>计划级 KPI JSON (D6: 本地先行/真重叠/远程等待/本地 token — 前端与对照脚本共用)</summary>
    public static string ToJson(PlanKpi kpi) =>
        JsonSerializer.Serialize(kpi, typeof(PlanKpi), Default);
}
