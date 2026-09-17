namespace agent.modelqueue;


/// <summary>
/// R510: 动作环「步进」观察面 —— 一次工具执行的事实 (步号/工具/成败/耗时)。
/// 只带事实字段, 不带任何展示文案 (文案面由出站方决定, 避免第二处实现)。
/// </summary>
public readonly record struct ActionStepProgress(int StepIndex, string Tool, bool Ok, long ElapsedMs);
