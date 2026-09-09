using LLama;
using LLama.Common;

namespace agent.vectormemory;

/// <summary>
/// v0.15.3 T-B (R-3 双加载消除): 跨组件 LLamaEmbedder 共享注册表 (modelPath → 实例)。
/// ITextEmbedder (BgeEmbedder, llamalocal) 与 RAG EmbeddingFunction (BgeEmbeddingProvider) 同模型
/// 共用一份 LLamaWeights+LLamaEmbedder — 消除第二份数百 MB 级模型驻留。
/// 参数差异以先到者为准 (同模型向量语义一致; Batch/UBatch 是吞吐参数)。
/// </summary>
public static class SharedEmbedderRegistry
{
    private static readonly System.Collections.Concurrent.ConcurrentDictionary<string, LLamaEmbedder> Shared = new();

    public static LLamaEmbedder GetOrCreate(string modelPath, Func<LLamaEmbedder> factory)
        => Shared.GetOrAdd(NormPath(modelPath), _ => factory());

    public static string NormPath(string p) => Path.GetFullPath(p).TrimEnd(Path.DirectorySeparatorChar);
}
