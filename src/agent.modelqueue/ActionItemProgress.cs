namespace agent.modelqueue;

/// <summary>
/// R538 (对标 codex 展示面, R508 分析稿 §4.3): 动作环「条目」面的一次上报 ——
/// 一个工具调用条目 (步内) 的标题 / 正文 / 输出尾 / 退出码。
///
/// Phase 语义 (单调: 同一 ItemId 先 started 后 completed):
///   started   — 执行**前**发出 (前端可立刻显示 "正在运行 X", 对标 codex `• Working (Ns)`);
///   completed — 执行**后**发出 (带 output_tail / lines_total / truncated / exit_code / elapsed_ms)。
///
/// 与 <see cref="ActionStepProgress"/> 走**同一**观察通道 (ActionProgressObserver) —— 不新开第二处发射面,
/// 保证「条目事实」与「步进事实」同源 (同一 tc/res, 同一时刻)。
/// 只说事实, 不带展示文案 (文案由出站方决定)。
/// </summary>
public readonly record struct ActionItemProgress(
    string ItemId,
    string Phase,
    string Kind,
    string Title,
    string Detail,
    string OutputTail,
    int LinesTotal,
    bool Truncated,
    int ExitCode);
