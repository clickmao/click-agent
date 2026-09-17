using System.Collections.Generic;

namespace agent.r1;

/// <summary>R1 管道 · 计划执行结果（rc 与 PipelineOutcome 同域：0 全过 / 4 计划非法 / 5 未达期望）。</summary>
public sealed record PlanExecutorResult(int Rc, string Stage, string Reason, IReadOnlyList<StepOutcome> Steps);
