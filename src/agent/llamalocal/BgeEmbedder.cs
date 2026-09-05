using LLama;
using LLama.Common;
using agent.contextgradient;

namespace agent.llamalocal;

/// <summary>
/// bge 本地嵌入器 (v7.15 P3, 压缩 P3 落点): LLamaSharp LLamaEmbedder + bge-small gguf
/// (/home/agentuser/models/bge-small-en-v1.5-q4_k_m.gguf — 永不上传/不入库)。
/// 惰性加载 + 双检锁; 模型缺失 → IsAvailable=false (DriftGuard 退锚词模式, 行为兼容)。
/// </summary>
public sealed class BgeEmbedder : ITextEmbedder, IDisposable
{
    private readonly string _modelPath;
    private readonly object _lock = new();
    private LLamaEmbedder? _embedder;
    private bool _initialized;

    public bool IsAvailable => File.Exists(_modelPath) && new FileInfo(_modelPath).Length > 0;

    public BgeEmbedder(string modelPath) => _modelPath = modelPath;

    public async Task<float[]> EmbedAsync(string text, CancellationToken ct = default)
    {
        if (!IsAvailable)
            throw new FileNotFoundException($"bge 模型不存在: {_modelPath}");
        EnsureInitialized();
        var batches = await _embedder!.GetEmbeddings(text, ct);
        // 单输入 → 取首组 (bge 输出即整句向量)
        return batches[0];
    }

    private void EnsureInitialized()
    {
        if (_initialized)
            return;
        lock (_lock)
        {
            if (_initialized)
                return;
            var parameters = new ModelParams(_modelPath)
            {
                ContextSize = 512,
                Threads = Math.Max(2, Environment.ProcessorCount / 2),
            };
            var weights = LLamaWeights.LoadFromFile(parameters);
            _embedder = new LLamaEmbedder(weights, parameters);
            _initialized = true;
        }
    }

    public void Dispose()
    {
        _embedder = null;
        _initialized = false;
    }
}
