namespace agent.r1;

/// <summary>
/// R618（RF0004.2 · M3 第二刀）—— 被机械裁选**采纳**的动作候选（声明面 ⇒ 执行面的载体）。
///
/// 动因: 第一刀（R610）只把「声明/采纳/拒绝」三个**计数**落台账 ⇒ `accepted` **无消费者**
///   （R617 实测声明到岸 9/9 而执行面仍读 `plan`）⇒ 本记录随
///   <see cref="ActionCandidates.Selection"/> 一并产出，由 <see cref="ActionExecPlan"/>
///   映射为执行面节点（**只搬运字节, 不做语义判断**；工具白名单与准入仍由裁选器负责）。
///
/// 字段来源 = 远端回复里的候选条目原文（`args` 存**原始 JSON 文本**，避免二次序列化漂移）。
/// </summary>
public sealed record AcceptedAction(
    string Id,
    string Tool,
    string ArgsJson,
    string Why);
