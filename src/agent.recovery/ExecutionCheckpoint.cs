using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.recovery;

/// <summary>
/// 任务步骤检查点 (v7.15 需求3: 工业级会话中断恢复):
/// 记录会话内最近一次计划执行到哪一步 — 意外中断/进程关闭后下次启动直接恢复进度。
/// 落盘 data/sessions/&lt;sessionId&gt;/checkpoint.json (原子写: tmp → File.Move)。
/// 序列化 source-gen (AOT 铁律: 无反射)。
/// </summary>
public sealed class ExecutionCheckpoint
{
    public string SessionId { get; set; } = string.Empty;

    /// <summary>计划 id (TaskPlan.PlanId)</summary>
    public string PlanId { get; set; } = string.Empty;

    /// <summary>RunId (TaskPlanRun.RunId)</summary>
    public string RunId { get; set; } = string.Empty;

    /// <summary>节点状态快照 (NodeId → 状态名)</summary>
    public Dictionary<string, string> NodeStates { get; set; } = new(StringComparer.Ordinal);

    /// <summary>最后完成的节点 id (恢复起点 = 其后第一个 Pending 节点)</summary>
    public string? LastCompletedNodeId { get; set; }

    /// <summary>检查点写入时刻 (UTC)</summary>
    public DateTime SavedAtUtc { get; set; } = DateTime.UtcNow;

    /// <summary>暂停原因 (中断时计划处于 PausedForApproval 则记录)</summary>
    public string? PauseReason { get; set; }

    /// <summary>
    /// 计划蓝图快照 JSON (v0.22.0 exp9 D7b — 缺了它就无法"重建 run": 光有节点状态名,
    /// 恢复后没有节点文本/依赖/执行位置, 只能重拆一遍 = 不是续跑)。
    /// 由 agent.intent 侧用 source-gen 上下文序列化; 本层(agent.recovery)不认识计划类型, 只当字符串存。
    /// null = 老检查点/无计划上下文 ⇒ 续跑必须**如实拒绝**, 不许猜测重建。
    /// </summary>
    public string? PlanJson { get; set; }

    /// <summary>运行实例快照 JSON (节点状态/等待台账/暂停原因; 同上, 字符串透传)</summary>
    public string? RunJson { get; set; }

    /// <summary>
    /// 已完成节点的**真实产出** (NodeId → 输出文本)。
    /// 续跑的关键: 唤醒等待节点要喂给它生产者的真产出 —— 没有这份快照就只能重跑生产者 (有副作用!)
    /// 或伪造数据。两者都不可接受 ⇒ 缺快照时续跑拒绝。
    /// </summary>
    public Dictionary<string, string> NodeOutputs { get; set; } = new(StringComparer.Ordinal);

    /// <summary>本轮用户原始请求 (续跑时无依赖节点的输入来源)</summary>
    public string? SourceText { get; set; }

    /// <summary>
    /// 卡在等用户回复的那个节点 (State=AwaitingClarification/Approval)。
    /// 非空 ⇒ 下一轮用户消息语义 = **答复它**, 不是新任务 (D7b 跨轮唤醒的入口判据)。
    /// </summary>
    public string? AwaitingNodeId { get; set; }

    /// <summary>等用户回复时给用户看的问题 (前端/CLI 提示用; 与节点 Clarifications 同源)</summary>
    public string? PendingQuestion { get; set; }
}

/// <summary>检查点 JSON 载荷序列化上下文 (AOT fast-path)</summary>
[JsonSerializable(typeof(ExecutionCheckpoint))]
[JsonSourceGenerationOptions(DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull)]
public partial class RecoveryJsonContext : JsonSerializerContext
{
}

/// <summary>
/// 检查点仓库: 写 (执行器每节点边界回调) + 读 (启动/恢复时) + 恢复裁定。
/// 线程安全 (单文件锁)。
/// </summary>
public sealed class CheckpointStore
{
    private readonly string _sessionsDir;
    private readonly object _lock = new();

    public CheckpointStore(string dataStoragePath = "data")
    {
        _sessionsDir = Path.Combine(dataStoragePath, "sessions");
        Directory.CreateDirectory(_sessionsDir);
    }

    private string PathOf(string sessionId) =>
        Path.Combine(_sessionsDir, sessionId, "checkpoint.json");

    /// <summary>保存检查点 (原子写: 同目录 tmp → move 覆盖 — 崩溃不产生半截文件)。</summary>
    public void Save(ExecutionCheckpoint checkpoint)
    {
        lock (_lock)
        {
            var finalPath = PathOf(checkpoint.SessionId);
            Directory.CreateDirectory(Path.GetDirectoryName(finalPath)!);
            var tmpPath = finalPath + ".tmp";
            File.WriteAllText(tmpPath,
                JsonSerializer.Serialize(checkpoint, RecoveryJsonContext.Default.ExecutionCheckpoint));
            File.Move(tmpPath, finalPath, overwrite: true);
        }
    }

    /// <summary>读取最近检查点 (无 → null)。</summary>
    public ExecutionCheckpoint? Load(string sessionId)
    {
        lock (_lock)
        {
            var path = PathOf(sessionId);
            if (!File.Exists(path))
                return null;
            try
            {
                return JsonSerializer.Deserialize(
                    File.ReadAllText(path), RecoveryJsonContext.Default.ExecutionCheckpoint);
            }
            catch (System.Text.Json.JsonException)
            {
                // 半截/损坏文件 (理论上原子写避免, 但历史文件可能) → 按无检查点处理, 不阻断启动
                return null;
            }
        }
    }

    /// <summary>清除检查点 (计划成功跑完/用户显式 /reset 时调用)。</summary>
    public void Clear(string sessionId)
    {
        lock (_lock)
        {
            var path = PathOf(sessionId);
            if (File.Exists(path))
                File.Delete(path);
        }
    }
}

/// <summary>
/// 恢复裁定结果: 中断的会话该从哪继续。
/// </summary>
public sealed class RecoveryPlan
{
    /// <summary>有可恢复的未完成计划?</summary>
    public bool Resumable { get; set; }

    public string PlanId { get; set; } = string.Empty;

    /// <summary>恢复起点节点 id (首个 Pending 节点; 全部完成 → 空串)</summary>
    public string ResumeFromNodeId { get; set; } = string.Empty;

    /// <summary>恢复起点前的已完成节点 (直接标记完成, 不重跑)</summary>
    public List<string> CompletedNodeIds { get; set; } = new();

    /// <summary>人类可读恢复说明 (/status JSON 可读)</summary>
    public string Summary { get; set; } = string.Empty;
}

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
