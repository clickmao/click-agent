using agent.contextgradient;

namespace agent.llamacpp;


/// <summary>嵌入端口接线配置 (产品 DI 用)。</summary>
public sealed class LlamaCppEmbedderOptions
{
    /// <summary>嵌入模型 (GGUF) 绝对路径。</summary>
    public required string ModelPath { get; init; }

    /// <summary>llama-server 路径; null ⇒ 走 BinaryEnvVar / PATH。</summary>
    public string? BinaryPath { get; init; }

    /// <summary>二进制环境变量名覆盖。</summary>
    public string BinaryEnvVar { get; init; } = "AGENTFRAMEWORK_LLAMA_BIN";

    /// <summary>上下文长度 (bge 类 512)。</summary>
    public int ContextSize { get; init; } = 512;

    public int Threads { get; init; } = 1;

    /// <summary>R430: 服务端总槽位 (显式; 嵌入向量同样要求可复现)。</summary>
    public int Parallel { get; init; } = 1;

    public int StartTimeoutMs { get; init; } = 300_000;

    /// <summary>是否允许在服务进程已死时自动重启一次。</summary>
    public bool AllowRestart { get; init; } = true;

    public static LlamaCppEmbedderOptions FromEnvironment()
    {
        // 默认路径 = 链上真身(bge-small-zh-v1.5 的 Q8_0 GGUF, 25.2MB)。此前默认指向 110MB 的
        // bge-base-zh-v1.5-q8.gguf, 而该文件已按用户令(2026-09-14)从本机删除 ⇒ 若 env 未设,
        // 旧默认会让 IsAvailable=false 静默降级到 NullTextEmbedder(空心向量)。默认值必须与部署一致。
        var modelPath = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_BGE_MODEL")
            ?? DefaultModelPath;
        var bin = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLAMA_BIN");
        return new LlamaCppEmbedderOptions
        {
            ModelPath = modelPath,
            BinaryPath = string.IsNullOrWhiteSpace(bin) ? null : bin,
        };
    }

    /// <summary>
    /// R465: 内置默认权重路径 (**单一来源**) —— 接线侧的三态判定与 <see cref="FromEnvironment"/> 必须同源,
    /// 否则两处各写一份默认路径 ⇒ 改一处就悄悄漂移 (与 R463 端点错配同类失效)。
    /// </summary>
    public static string DefaultModelPath => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
        ".agentframework", "models", "bge-q8.gguf");
}
