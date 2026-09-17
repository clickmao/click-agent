using System;
using System.Threading;
using System.Threading.Tasks;

namespace agent.skills;


/// <summary>v0.17.2-c: 条件定时结果 (宿主/上层直接 Render 渲染)。</summary>
public sealed class ConditionalRunVerdict
{
    public ConditionalRunVerdictType Verdict { get; set; }
    public ScriptPluginRunResult? Run { get; set; }
    public string? Reason { get; set; }

    public string Render()
    {
        switch (Verdict)
        {
            case ConditionalRunVerdictType.Executed:
                return Run?.Render() ?? "✅ 已执行。";
            case ConditionalRunVerdictType.Failed:
                return Run?.Render() ?? $"❌ 执行失败: {Reason}";
            case ConditionalRunVerdictType.RefusedBusy:
                return $"⏸ 到期时仍有其他 agent 忙, 未执行 (条件: 无其他任务): {Reason}";
            case ConditionalRunVerdictType.RejectedInvalid:
                return $"⛔ 脚本验证拒绝, 未执行: {Reason}";
            default:
                return "已取消。";
        }
    }
}
