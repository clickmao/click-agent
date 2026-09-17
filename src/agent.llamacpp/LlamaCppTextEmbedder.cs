using agent.contextgradient;

namespace agent.llamacpp;

/// <summary>
/// <see cref="ITextEmbedder"/> 的 llama.cpp 进程化实现 —— 懒启动一个**专用** llama-server
/// (`--embeddings`; 该开关与文本生成互斥, 故与生成服务各起一个进程)。
///
/// 端口化纪律:
///  • <see cref="IsAvailable"/> = 纯配置判定 (模型文件在 ∧ 二进制可解析), 零 I/O、零进程、零副作用
///    —— 调用方据此走锚词回退 (与既有 NullTextEmbedder 语义一致);
///  • <see cref="EmbedAsync"/> 失败**抛** <see cref="LlamaCppException"/> (带 code), 不静默兜底;
///  • 被使用计数: <see cref="ProcessStarts"/>/<see cref="RequestsServed"/>/<see cref="EmbeddingsServed"/>;
///  • 零 P/Invoke: 边界只有「进程 + loopback HTTP」, 跨平台 (每 RID 一份官方二进制)。
/// </summary>
public sealed class LlamaCppTextEmbedder : ITextEmbedder, IAsyncDisposable
{
    private readonly LlamaCppEmbedderOptions _o;
    private readonly SemaphoreSlim _gate = new(1, 1);
    private LlamaCppProvider? _provider;
    private long _starts;

    public LlamaCppTextEmbedder(LlamaCppEmbedderOptions options) => _o = options;

    /// <summary>纯配置判定 (无副作用)。</summary>
    public bool IsAvailable => File.Exists(_o.ModelPath) && ResolveBinary() is not null;

    public string? BinaryPath => ResolveBinary();

    public long ProcessStarts => Interlocked.Read(ref _starts);
    public long RequestsServed => _provider?.RequestsServed ?? 0;
    public long EmbeddingsServed => _provider?.EmbeddingsServed ?? 0;
    public string? BaseUrl => _provider?.BaseUrl;

    public async Task<float[]> EmbedAsync(string text, CancellationToken ct = default)
    {
        var provider = await EnsureProviderAsync(ct).ConfigureAwait(false);
        return await provider.EmbedAsync(text, ct).ConfigureAwait(false);
    }

    private async Task<LlamaCppProvider> EnsureProviderAsync(CancellationToken ct)
    {
        var existing = _provider;
        if (existing is { IsRunning: true }) return existing;

        await _gate.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            if (_provider is { IsRunning: true }) return _provider;
            if (_provider is not null && !_o.AllowRestart)
                throw new LlamaCppException(LlamaCppException.ProviderUnavailable, "嵌入服务已停止且 AllowRestart=false");
            if (_provider is not null) await _provider.DisposeAsync().ConfigureAwait(false);

            var provider = await LlamaCppProvider.StartAsync(new LlamaServerOptions
            {
                ModelPath = _o.ModelPath,
                BinaryPath = _o.BinaryPath,
                BinaryEnvVar = _o.BinaryEnvVar,
                ContextSize = _o.ContextSize,
                Threads = _o.Threads,
                Parallel = _o.Parallel,
                StartTimeoutMs = _o.StartTimeoutMs,
                EmbeddingMode = true,   // 必需: /v1/embeddings 只在 --embeddings 形态存在
            }, ct).ConfigureAwait(false);

            _provider = provider;
            Interlocked.Increment(ref _starts);
            return provider;
        }
        finally
        {
            _gate.Release();
        }
    }

    private string? ResolveBinary()
    {
        try
        {
            var opts = new LlamaServerOptions { ModelPath = _o.ModelPath, BinaryPath = _o.BinaryPath, BinaryEnvVar = _o.BinaryEnvVar };
            return LlamaServerHost.TryResolveBinary(opts, out var path, out _) ? path : null;
        }
        catch { return null; }
    }

    public async ValueTask DisposeAsync()
    {
        if (_provider is not null)
        {
            await _provider.DisposeAsync().ConfigureAwait(false);
            _provider = null;
        }
        _gate.Dispose();
    }
}
