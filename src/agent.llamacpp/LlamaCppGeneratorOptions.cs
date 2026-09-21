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
        // R609 (用户令「用8b和速度快的fork(x1.80那个)」): 两半分开落地 ——
        //   ① **fork 运行时（已落地）**：默认二进制 = PrismML 厂商 fork `prism-b10709-9a9394a`
        //      (llama-server sha256 e5c4211999de5b789b980626…) 若在盘上则优先；同件同夹具实测
        //      1.80× 提速 (LFM2.5-VL-3B: 482.6 s vs 主线 869.4 s / 28 例)，能力逐位相同
        //      (acc 1.0000 / 假跳 0/14 / 漏跳 0/14，eval/rover/r462 同窗四臂)。
        //   ② **8B 权重（未落地·被闸拦住）**：Ternary-Bonsai-8B-PQ2_0 (Qwen3-8B 三值 PQ2_0 /
        //      2,182,184,672 B / sha256 1376f942aa90e60f7b570c1d…) 判别位达标 (acc 1.0000 /
        //      假跳 0/14 / 漏跳 0/14) 但**产品 chat 通路被 R409 模板闸拒绝**：
        //      `--verify-template` ⇒ RenderedBosCount=0 (Qwen3 模板无 BOS) ⇒ `gated_bos_count_0`
        //      ⇒ exit 6 (LlamaCppCommand.cs:327 硬编码 `RenderedBosCount == 1`)。
        //      另: 该包 BOS 元数据 = ","(id 11) 而非 Qwen3 惯用 151643 ⇒ 模板族判定不可信。
        //      落地前须裁定「改闸适配无 BOS 模板」或「给 8B 注入单 BOS 覆盖模板」。
        //      产品档装载实测: ctx 4608 / f32-KV / -t 2 / -np 1 ⇒ 峰值 RSS 3,139 MB (余量 ~169 MB)。
        //   ③ 历史选型 (R578「那就用lfm2.5」) 仍为**默认权重**：LFM2.5-VL-3B 可用 env 覆盖。
        var modelPath = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLM_MODEL")
            ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                            ".agentframework", "models", "lfm25vl3b", "LFM2.5-VL-3B-Q4_K_M.gguf");
        var bin = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLAMA_BIN");
        if (string.IsNullOrWhiteSpace(bin))
        {
            var fork = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                                    ".agentframework", "bin", "llama-prism-b10709-9a9394a", "llama-server");
            bin = File.Exists(fork) ? fork : null;
        }
        return new LlamaCppGeneratorOptions
        {
            ModelPath = modelPath,
            BinaryPath = string.IsNullOrWhiteSpace(bin) ? null : bin,
        };
    }
}
