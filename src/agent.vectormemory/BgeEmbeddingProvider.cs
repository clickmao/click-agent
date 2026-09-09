using LLama;
using LLama.Common;
using LLama.Native;

namespace agent.vectormemory;

/// <summary>
/// v0.11.0 R100: bge-small-zh 本地 embedding (vendored LLamaSharp 0.29, ProjectReference)。
/// 仅 JIT 部署形态注册 (NativeAOT 下 LLamaSharp native interop SIGSEGV — R90 实测红线)。
/// 机制: bge 仅用 CPU 档计算 (GpuLayerCount=0); 若宿主进程已加载本地 LLM,
/// libllama/libggml native 由 NativeApi 静态解析器保证同进程只加载一次 (共享复用)。
/// </summary>
public class BgeEmbeddingProvider : IEmbeddingProvider
{
    private readonly LLamaEmbedder _embedder;
    private readonly object _lock = new();
    public int Dimension => _embedder.EmbeddingSize;
    public string Name => "bge-local";

    private BgeEmbeddingProvider(LLamaEmbedder embedder) => _embedder = embedder;

    /// <summary>加载 bge gguf 模型 (CPU 变体 native; 共享 native 由解析器复用)</summary>
    public static BgeEmbeddingProvider Create(string modelPath, int gpuLayerCount = 0)
    {
        // v0.15.3 T-B (R-3): 走 BgeEmbedder 共享注册表 — 同 modelPath 复用 LLamaEmbedder
        // (消除第二份模型驻留; 参数差异以先到者为准 — Batch/UBatch 是吞吐参数不改向量)。
        var embedder = SharedEmbedderRegistry.GetOrCreate(modelPath, () =>
        {
            var parameters = new LLama.Common.ModelParams(modelPath)
            {
                ContextSize = 512,
                GpuLayerCount = gpuLayerCount,
                Threads = Math.Max(1, Environment.ProcessorCount / 2),
                BatchSize = 512,
                UBatchSize = 512,
            };
            var weights = LLamaWeights.LoadFromFile(parameters);
            return new LLamaEmbedder(weights, parameters);
        });
        return new BgeEmbeddingProvider(embedder);
    }

    public float[] Embed(string text)
    {
        lock (_lock)
        {
            var vectors = _embedder.GetEmbeddings(text).GetAwaiter().GetResult();
            var vec = vectors.Last().ToArray();
            // L2 归一化
            var mag = Math.Sqrt(vec.Sum(v => (double)v * v));
            if (mag > 0)
                for (var i = 0; i < vec.Length; i++)
                    vec[i] /= (float)mag;
            return vec;
        }
    }
}
