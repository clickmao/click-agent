namespace agent.r1;

/// <summary>
/// R1 管道 · 调用账（token 口径：PromptTokens/CompletionTokens 取 provider 实报；
/// 缓存命中「未上报」= null，禁写 0 冒充）。
/// </summary>
public sealed record R1CallStats(
    int Calls,
    int PromptTokens,
    int CompletionTokens,
    int? CacheHitTokens,
    int? CacheMissTokens,
    int RepairRounds,
    int ExecRepairs = 0)
{
    public static R1CallStats Empty => new(0, 0, 0, null, null, 0, 0);

    public int Total => PromptTokens + CompletionTokens;
}
