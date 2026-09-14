using agent.contextgradient;

namespace agent.llamacpp;

/// <summary>
/// 本地推理/嵌入统一执行面: 一个 llama-server 进程同时提供生成 (/completion) 与嵌入 (/v1/embeddings)。
///
/// 端口化纪律落地:
///   • 可替换: 端口由 ITextEmbedder 等既有产品接口暴露, 实现可换 (本类 vs 旧 C# 引擎 vs 远端 API);
///   • 数值对账: 生成侧返回原始 token id, 与 llama-cli 基线逐位可比 (见 R408 对账测试);
///   • 被使用计数: RequestsServed / TokensGenerated / EmbeddingsServed 全部来自服务端响应, 非估算;
///   • 无设备负控: 二进制缺失/模型缺失/启动失败 ⇒ LlamaCppException(provider_unavailable|start_failed), 绝不静默兜底。
/// </summary>
public sealed class LlamaCppProvider : IAsyncDisposable
{
    private readonly LlamaServerHost _host;
    private readonly LlamaCppClient _client;

    private LlamaCppProvider(LlamaServerHost host, LlamaCppClient client)
    {
        _host = host;
        _client = client;
    }

    public static async Task<LlamaCppProvider> StartAsync(LlamaServerOptions options, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(options);
        var host = new LlamaServerHost(options);
        try
        {
            await host.StartAsync(ct).ConfigureAwait(false);
        }
        catch
        {
            await host.DisposeAsync().ConfigureAwait(false);
            throw;
        }

        return new LlamaCppProvider(host, new LlamaCppClient(host.BaseUrl));
    }

    public string BaseUrl => _client.BaseUrl;

    /// <summary>服务进程是否仍在运行 (零 I/O 健康探针; 供调用方决定重启/回退)。</summary>
    public bool IsRunning => _host.IsRunning;

    public long RequestsServed => _client.RequestsServed;

    public long TokensGenerated => _client.TokensGenerated;

    public long EmbeddingsServed => _client.EmbeddingsServed;

    public IReadOnlyList<string> ServerStderrTail => _host.StderrTail;

    /// <summary>生成 (默认 greedy 24-64 token, 与对账口径一致)。</summary>
    public Task<CompletionResult> GenerateAsync(string prompt, int maxTokens = 64, bool greedy = true, CancellationToken ct = default)
    {
        var opts = new CompletionOptions
        {
            Prompt = prompt,
            MaxTokens = maxTokens,
            Temperature = greedy ? 0f : 0.8f,
            Samplers = greedy ? ["temperature"] : ["top_k", "top_p", "min_p", "temperature"],
            CachePrompt = false,
        };
        return _client.CompleteAsync(opts, ct);
    }

    public async Task<float[]> EmbedAsync(string text, CancellationToken ct = default)
    {
        var vectors = await _client.EmbedAsync([text], ct).ConfigureAwait(false);
        if (vectors.Length == 0)
            throw new LlamaCppException(LlamaCppException.MalformedResponse, "/v1/embeddings 未返回任何向量 (2xx 但 data 为空)");
        return vectors[0];
    }

    public Task<float[][]> EmbedBatchAsync(IReadOnlyList<string> texts, CancellationToken ct = default)
        => _client.EmbedAsync(texts, ct);

    public Task<string?> HealthAsync(CancellationToken ct = default) => _client.HealthAsync(ct);

    public async ValueTask DisposeAsync()
    {
        _client.Dispose();
        await _host.DisposeAsync().ConfigureAwait(false);
    }
}

