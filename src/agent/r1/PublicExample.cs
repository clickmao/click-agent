namespace agent.r1;

/// <summary>
/// R1 管道 · 题面**公开用例**（结构量）。
///
/// 来源 = 题面正文的逐字机械抽取（见 <see cref="PublicExampleExtractor"/>）：
/// 输入/期望两侧都来自题面，**不是**模型自撰的 <c>expect_stdout</c>，也**不经**模型裁判。
/// 抽不出 ⇒ 探针不启用（零行为变化），绝不猜。
/// </summary>
public sealed record PublicExample(string GameId, string Input, string Expected);
