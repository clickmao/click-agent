namespace agent.rover.infer;

/// <summary>
/// RoPE 配对约定 —— 由 <b>模型架构</b> 决定, 不是实现细节。
///
/// 权威源: llama.cpp <c>llama_model_rope_type()</c>
/// (取自 llama-cpp-python 0.3.35 sdist 内 llama.cpp/src/llama-model.cpp:2584;
///  机械提取结果存档 <c>eval/rover/oracle/rope-types.json</c>, 由 RoverRopeTests 机检)。
///
///   · <see cref="NormConsecutive"/> = 第 2j 与第 2j+1 维配对 (相邻)      —— llama / deepseek2 / granite / mistral3 …
///   · <see cref="NeoxHalf"/>        = 第 j 与第 j+n_rot/2 维配对 (半偏移) —— qwen2 / qwen3 / gemma / phi3 / gptneox …
///
/// 两种约定的频次表完全相同 (inv_freq[j] = base^(-2j/n_rot)), 只有取数下标不同 ⇒
/// <b>用错配对不抛错, 只静默产出错误的位置信息</b> (表现为输出退化: 重复/乱码)。
/// 因此配对必须按 arch 选, 且必须有"另一配对必须给出不同结果"的负控。
/// </summary>
public enum RopePairing
{
    /// <summary>相邻配对: (2j, 2j+1) —— llama.cpp <c>LLAMA_ROPE_TYPE_NORM</c></summary>
    NormConsecutive = 0,

    /// <summary>半偏移配对: (j, j+n_rot/2) —— llama.cpp <c>LLAMA_ROPE_TYPE_NEOX</c></summary>
    NeoxHalf = 1,
}

public static class RopePairings
{
    /// <summary>
    /// llama.cpp <c>rope_type = NORM</c> 的 GGUF arch 名 (机取自 llama-arch.cpp LLM_ARCH_NAMES, 41 项)。
    /// 未收录者按 llama.cpp 的 default 分支 ⇒ NEOX。
    /// </summary>
    public static readonly IReadOnlySet<string> NormArchs = new HashSet<string>(StringComparer.Ordinal)
    {
        "arcee", "arctic", "baichuan", "bailingmoe", "chameleon", "chatglm", "cohere2", "cohere2moe", "command-r", "deci",
        "deepseek", "deepseek2", "deepseek2-ocr", "deepseek32", "deepseek4", "eagle3", "ernie4_5", "ernie4_5-moe", "glm-dsa", "granite",
        "granitehybrid", "granitemoe", "graniteswitch", "internlm2", "llada", "llama", "llama-embed", "llama4", "maincoder", "minicpm",
        "mistral3", "mistral4", "muse-glimmer", "nanbeige", "neo-bert", "olmo", "plm", "pockettts", "smollm3", "starcoder",
        "xverse",
    };

    /// <summary>按 GGUF <c>general.architecture</c> 判定配对约定 (默认 NEOX, 与 llama.cpp default 分支一致)。</summary>
    public static RopePairing FromArch(string arch) =>
        NormArchs.Contains(arch) ? RopePairing.NormConsecutive : RopePairing.NeoxHalf;

    /// <summary>llama.cpp 侧的叫法 (日志/证据用, 便于与权威源逐字对账)。</summary>
    public static string ToLlamaCppName(RopePairing pairing) =>
        pairing == RopePairing.NormConsecutive ? "NORM" : "NEOX";
}
