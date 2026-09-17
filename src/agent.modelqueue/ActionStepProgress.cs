namespace agent.modelqueue;


/// <summary>
/// R510: 动作环「步进」观察面 —— 一次工具执行的事实 (步号/工具/成败/耗时)。
/// 只带事实字段, 不带任何展示文案 (文案面由出站方决定, 避免第二处实现)。
/// R538: 增 <see cref="Item"/> —— 同一时刻的「条目」面 (标题/正文/输出尾, 对标 codex `• Ran … ⎿`),
/// 走同一通道上报 ⇒ 步进事实与条目事实同源; 未填 (null) = 老口径, 调用方行为逐字节不变。
/// </summary>
public readonly record struct ActionStepProgress(int StepIndex, string Tool, bool Ok, long ElapsedMs)
{
    /// <summary>条目面 (null = 无; 填了才发 item.* 事件)。</summary>
    public ActionItemProgress? Item { get; init; }
}
