using System.Globalization;

namespace agent.llamacpp;

/// <summary>
/// v0.30.0 R408: llama.cpp 进程化后端配置。
///
/// 形态铁律: 与 llama.cpp 的边界只能是「进程 + HTTP」——零 P/Invoke、零 native 链接。
/// 依据: ① 跨平台(每 RID 一份官方二进制, 不在托管程序集里绑死任何 ABI);
///       ② NativeAOT 可用 —— 对照实测: LLamaSharp 进程内 interop 在 AOT 下 SIGSEGV
///          (见 src/agent.contextgradient/ITextEmbedder.cs 注释, R90 实测)。
/// </summary>
public sealed class LlamaServerOptions
{
    /// <summary>GGUF 模型绝对路径。</summary>
    public required string ModelPath { get; init; }

    /// <summary>llama-server 可执行文件路径; null ⇒ 依次尝试环境变量、PATH。</summary>
    public string? BinaryPath { get; init; }

    /// <summary>可执行文件的路径环境变量名。</summary>
    public string BinaryEnvVar { get; init; } = "AGENTFRAMEWORK_LLAMA_BIN";

    public string Host { get; init; } = "127.0.0.1";

    /// <summary>监听端口; 0 ⇒ 由本机空闲端口探测决定 (跨平台, 不依赖 unix socket)。</summary>
    public int Port { get; init; }

    public int ContextSize { get; init; } = 4096;

    /// <summary>生成线程数; 0 ⇒ 不传 -t, 交 llama.cpp 自适应。</summary>
    public int Threads { get; init; }

    /// <summary>
    /// R430: 服务端**总槽位** (-np)。默认 1 = 真串行。
    /// 依据: 本仓库使用的 llama.cpp 构建 `-np` 默认 = **4** (实测 n_slots=4) ⇒ 并发在途请求进同一批
    /// ⇒ 每序列批形状随调用序列变化 ⇒ 浮点归约顺序变 ⇒ 同一 prompt/请求体仍产出不同文本。
    /// 决策路径要逐位可复现 ⇒ 总槽位必须 = 1, 且**显式声明** (绝不依赖构建默认)。
    /// </summary>
    public int Parallel { get; init; } = 1;

    /// <summary>KV cache 数值档; 对账须 f32 (llama.cpp 默认 f16 会导致近并列翻档, R407 铁律)。</summary>
    public string CacheTypeK { get; init; } = "f32";

    /// <summary>KV cache 数值档 (V)。</summary>
    public string CacheTypeV { get; init; } = "f32";

    /// <summary>Flash attention; 对账须 off (与 f32 KV 组合才可逐位对齐)。</summary>
    public bool FlashAttention { get; init; }

    /// <summary>启动就绪等待上限 (ms)。</summary>
    public int StartTimeoutMs { get; init; } = 300_000;

    /// <summary>额外命令行参数 (追加在末尾)。</summary>
    public IReadOnlyList<string> ExtraArgs { get; init; } = [];

    /// <summary>
    /// 嵌入服务形态: llama-server 的 /v1/embeddings 需启动时加 --embeddings,
    /// 且该开关与文本生成互斥 (llama.cpp 限制) ⇒ 生成/嵌入必须起两个进程 (各自专用模型)。
    /// </summary>
    public bool EmbeddingMode { get; init; }

    /// <summary>构造 P/Invoke 之外的第三个形态参数: 一律走 ArgumentList (零 shell 铁律)。</summary>
    public string Describe() => string.Create(CultureInfo.InvariantCulture,
        $"model={ModelPath} ctx={ContextSize} threads={(Threads > 0 ? Threads.ToString(CultureInfo.InvariantCulture) : "auto")} np={Math.Max(1, Parallel)} kv={CacheTypeK}/{CacheTypeV} fa={(FlashAttention ? "on" : "off")}");
}
