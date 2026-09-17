using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.recovery;


/// <summary>
/// 会话恢复器 (需求3 核心): 会话开始前读检查点 — 上次正在执行的任务步骤直接复原。
/// 恢复语义:
///   Pending/Running/Retrying 节点 → 重新执行 (无副作用假设, 与计划级重试一致);
///   Succeeded 节点 → 跳过 (不重跑);
///   Failed/Cancelled/Skipped → 重新执行 (上次非正常终态)。
/// </summary>
public static class CheckpointRecovery
{
    public static RecoveryPlan BuildRecoveryPlan(ExecutionCheckpoint checkpoint)
    {
        var plan = new RecoveryPlan
        {
            PlanId = checkpoint.PlanId,
            CompletedNodeIds = checkpoint.NodeStates
                .Where(kv => kv.Value.Equals("Completed", StringComparison.OrdinalIgnoreCase))
                .Select(kv => kv.Key)
                .ToList(),
        };

        var resumeFrom = checkpoint.NodeStates
            .FirstOrDefault(kv => kv.Value.Equals("Pending", StringComparison.OrdinalIgnoreCase)
                                  || kv.Value.Equals("Running", StringComparison.OrdinalIgnoreCase)
                                  || kv.Value.Equals("Retrying", StringComparison.OrdinalIgnoreCase))
            .Key;

        plan.ResumeFromNodeId = resumeFrom ?? string.Empty;
        plan.Resumable = checkpoint.NodeStates.Count > 0
                         && checkpoint.NodeStates.Values.Any(v =>
                             !v.Equals("Completed", StringComparison.OrdinalIgnoreCase));
        plan.Summary = plan.Resumable
            ? $"会话 {checkpoint.SessionId} 检查点恢复: 计划 {checkpoint.PlanId} 从节点 {plan.ResumeFromNodeId} 继续 " +
              $"({plan.CompletedNodeIds.Count}/{checkpoint.NodeStates.Count} 已完成节点跳过; 检查点 {checkpoint.SavedAtUtc:u})"
            : $"计划 {checkpoint.PlanId} 上次已全部完成, 无需恢复";
        return plan;
    }
}
