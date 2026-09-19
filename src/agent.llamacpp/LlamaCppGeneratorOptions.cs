namespace agent.llamacpp;


/// <summary>本地生成端口接线配置（产品 DI 用；与嵌入侧同构）。</summary>
public sealed class LlamaCppGeneratorOptions
{
    /// <summary>生成模型 (GGUF) 绝对路径。</summary>
    public required string ModelPath { get; init; }

    /// <summary>llama-server 路径; null ⇒ 走 <see cref="BinaryEnvVar"/> / PATH。</summary>
    public string? BinaryPath { get; init; }

    public string BinaryEnvVar { get; init; } = "AGENTFRAMEWORK_LLAMA_BIN";

    /// <summary>上下文长度。K2b 需可复用前缀 ≥4224 token ⇒ 会话形态必须留足（默认 6144）。</summary>
    public int ContextSize { get; init; } = 6144;

    public int Threads { get; init; } = 1;

    /// <summary>R430: 服务端总槽位 (显式; 1 = 真串行, 决策路径逐位可复现的前提)。</summary>
    public int Parallel { get; init; } = 1;

    public int StartTimeoutMs { get; init; } = 300_000;

    /// <summary>服务进程已死时是否允许自动重启一次（长驻语义: 重启即丢 KV 缓存 ⇒ 计数可见）。</summary>
    public bool AllowRestart { get; init; } = true;

    /// <summary>单轮生成上限（调用方可逐轮覆盖）。</summary>
    public int MaxTokens { get; init; } = 64;

    public static LlamaCppGeneratorOptions FromEnvironment()
    {
        // R578 (用户令「那就用lfm2.5」): 默认权重 = LFM2.5-VL-3B-Q4_K_M (arch lfm2, 此处只用文本塔)。
        //   同源校验: 1,674,455,072 B / sha256 2436cf4b…8884 (= 目录内官方 SHA256SUMS;
        //   HF LFS x-linked-etag / x-linked-size 同值) ⇒ 已核, 非同名换装。
        //   选型依据 (同器具 8a8b895d27dd / 同 28 条产品实发 prompt): acc 1.000 / 假跳 0/14 /
        //   漏跳 0/14 / gen 2 token·次; 同窗对照 1.5B-instruct 13/14 假跳、r1 14/14 假跳
        //   (eval/rover/r577/arm-lfm3b-requal.json, registry r578.local-gate-model-lfm25)。
        //   R577 装回的 r1 权重仍在盘上未删 (用户本轮未令删除), 可用 AGENTFRAMEWORK_LLM_MODEL 覆盖。
        var modelPath = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLM_MODEL")
            ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                            ".agentframework", "models", "lfm25vl3b", "LFM2.5-VL-3B-Q4_K_M.gguf");
        var bin = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLAMA_BIN");
        return new LlamaCppGeneratorOptions
        {
            ModelPath = modelPath,
            BinaryPath = string.IsNullOrWhiteSpace(bin) ? null : bin,
        };
    }
}
