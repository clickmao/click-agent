// R480: 独立文本召回模块 —— 任务级 memory / 当前状态 (用户令: 「每个任务应该有个memory或当前状态? 不应该仅靠上下文」)。
// 设计闭环 (双向优化):
//   产出物 → 自带地址 (RecallHit.Links / Artifacts) → 落入任务状态 → SyncToIndex 回流成可召回文档 → 下次探索召回命中。
// 本文件不依赖任何模型上下文: 状态在磁盘, 进程重启后按 taskId 读回即可。
using System.Text;
using System.Text.Json;

namespace agent.recall;


public sealed class TaskStateEvent
{
    public required long Ts { get; init; }
    public required string Kind { get; init; }
    public required string Text { get; init; }
    public IReadOnlyList<string> Artifacts { get; init; } = Array.Empty<string>();
    public IReadOnlyList<string> Links { get; init; } = Array.Empty<string>();
}
