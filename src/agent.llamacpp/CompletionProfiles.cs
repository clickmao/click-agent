namespace agent.llamacpp;

/// <summary>
/// 生成口径 → 请求参数的**唯一映射点**（可单测，避免口径判断散落在多处）。
/// 依据（R410 实测）: 前缀复用只发生在 cache_prompt=true 且前缀稳定时;
/// 而 cache_prompt=true 会破坏不同 batch 的 logits 逐位一致 ⇒ 对账口径必须与生产口径分离。
/// </summary>
public static class CompletionProfiles
{
    /// <summary>按口径构造请求参数。greedy = 仅 temperature 采样器 + temp 0（与 R407 对账口径同构）。</summary>
    public static CompletionOptions Build(string prompt, int maxTokens, bool greedy, CompletionReuse reuse) => new()
    {
        Prompt = prompt,
        MaxTokens = maxTokens,
        Temperature = greedy ? 0f : 0.8f,
        Samplers = greedy ? ["temperature"] : ["top_k", "top_p", "min_p", "temperature"],
        CachePrompt = reuse == CompletionReuse.Session,
    };
}
