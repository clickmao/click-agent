// R480: 独立文本召回模块 —— 任务级 memory / 当前状态 (用户令: 「每个任务应该有个memory或当前状态? 不应该仅靠上下文」)。
// 设计闭环 (双向优化):
//   产出物 → 自带地址 (RecallHit.Links / Artifacts) → 落入任务状态 → SyncToIndex 回流成可召回文档 → 下次探索召回命中。
// 本文件不依赖任何模型上下文: 状态在磁盘, 进程重启后按 taskId 读回即可。
using System.Text;
using System.Text.Json;

namespace agent.recall;


/// <summary>任务状态物化视图: 由事件流按序折叠而来 (不含模型上下文)。</summary>
public sealed class TaskState
{
    public required string TaskId { get; init; }
    public string LastText { get; set; } = "";
    public long LastTs { get; set; }
    public int EventCount { get; set; }
    public List<string> Artifacts { get; } = new();
    public List<string> Links { get; } = new();

    /// <summary>状态文档自身的地址 (产出物自带地址的一员)。</summary>
    public string Address => "task://" + TaskId;

    public string ToStateText()
    {
        var sb = new StringBuilder(256);
        sb.Append("任务 ").Append(TaskId).Append(" 当前状态: ").Append(LastText);
        if (Artifacts.Count > 0)
        {
            sb.Append(" | 产出物: ").Append(string.Join(" ", Artifacts));
        }
        if (Links.Count > 0)
        {
            sb.Append(" | 关联地址: ").Append(string.Join(" ", Links));
        }
        return sb.ToString();
    }
}
