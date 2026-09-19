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
        // R577 (用户令「用 r1 / 删 3b」): 默认权重 = DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M。
        //   同源校验: 1,117,320,800 B / sha256 1741e5b2…(= HF LFS oid, 与 r463.deletion-ledger 同值);
        //   R462-W 同语料同器具复算与旧档逐指标相同 (acc 0.5 / 假跳 14/14 / gen 4418 tok)
        //   ⇒ 口径 = F2 回退, 不是升级 (eval/rover/r577/arm-r1-requal.json, registry r577.local-gate-model-revert)。
        //   3B 权重已按令删除, 故此处不再指向它。仍可用 AGENTFRAMEWORK_LLM_MODEL 覆盖。
        var modelPath = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLM_MODEL")
            ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                            ".agentframework", "models", "r1-distill-qwen-1.5b-q4km.gguf");
        var bin = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLAMA_BIN");
        return new LlamaCppGeneratorOptions
        {
            ModelPath = modelPath,
            BinaryPath = string.IsNullOrWhiteSpace(bin) ? null : bin,
        };
    }
}
