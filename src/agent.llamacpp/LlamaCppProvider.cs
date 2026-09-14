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
public sealed class LlamaCppProvider : IAsyncDisposable, ILocalPromptRenderer
{
    private readonly LlamaServerHost _host;
    private readonly LlamaCppClient _client;
    private readonly SemaphoreSlim _propsLock = new(1, 1);
    private ModelProps? _props;
    private long _gateRejections;
    private long _literalCalls;

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

    /// <summary>已执行的模板渲染次数（被使用计数，非估算）。</summary>
    public long TemplateRenders => _client.TemplateRenders;

    /// <summary>被闸门拒收的生成请求数（手拼 prompt / 字面特殊 token / 空渲染）。</summary>
    public long PromptGateRejections => Interlocked.Read(ref _gateRejections);

    /// <summary>绕过闸门的诊断通路调用数（生产路径应当恒为 0；非 0 即缺口）。</summary>
    public long LiteralPromptCalls => Interlocked.Read(ref _literalCalls);

    /// <summary>模型身份与特殊 token（首次访问时经 GET /props 取得并缓存）。</summary>
    public ModelProps? Props => _props;

    public IReadOnlyList<string> ServerStderrTail => _host.StderrTail;

    /// <summary>取模型元数据（缓存；闸门规则的数据来源）。</summary>
    public async Task<ModelProps> EnsurePropsAsync(CancellationToken ct = default)
    {
        if (_props is { } cached) return cached;
        await _propsLock.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            _props ??= await _client.PropsAsync(ct).ConfigureAwait(false);
            return _props;
        }
        finally
        {
            _propsLock.Release();
        }
    }

    /// <summary>
    /// 渲染本地 prompt（ILocalPromptRenderer 唯一实现）：模板来自模型元数据，
    /// 产物过闸门后才返回；任何拒收都计入 PromptGateRejections 并抛出（不静默降级）。
    /// </summary>
    public async ValueTask<RenderedPrompt> RenderAsync(IReadOnlyList<ChatTurn> turns, CancellationToken ct = default)
    {
        var props = await EnsurePropsAsync(ct).ConfigureAwait(false);
        var text = await _client.ApplyTemplateAsync(turns, ct).ConfigureAwait(false);
        var rendered = new RenderedPrompt(text, LocalPromptProvenance.GgufJinja);
        try
        {
            LocalPromptGate.Validate(rendered, props);
        }
        catch (LlamaCppException)
        {
            Interlocked.Increment(ref _gateRejections);
            throw;
        }
        return rendered;
    }

    /// <summary>
    /// 生成（默认 greedy、关 cache_prompt，与 R407/R408 对账口径一致）。
    /// prompt 只接受结构化轮次 ⇒ 模板一定来自模型元数据（R409 闸门）。
    /// </summary>
    public async Task<CompletionResult> GenerateAsync(
        IReadOnlyList<ChatTurn> turns, int maxTokens = 64, bool greedy = true, CancellationToken ct = default)
    {
        var rendered = await RenderAsync(turns, ct).ConfigureAwait(false);
        return await CompleteRenderedAsync(rendered, maxTokens, greedy, ct).ConfigureAwait(false);
    }

    /// <summary>对已渲染产物直接生成（渲染与生成分离时使用；调用方须持有渲染凭证）。</summary>
    public Task<CompletionResult> CompleteRenderedAsync(
        RenderedPrompt rendered, int maxTokens = 64, bool greedy = true, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(rendered);
        return CompleteLiteralAsync(rendered.Text, maxTokens, greedy, ct);
    }

    /// <summary>
    /// 诊断/对账通路：直接把字面 prompt 交给 /completion（**绕过闸门**）。
    /// 仅用于与外部基线做 token id 逐位对比；调用计数见 LiteralPromptCalls，生产路径不得使用。
    /// </summary>
    public Task<CompletionResult> CompleteLiteralPromptAsync(
        string prompt, int maxTokens = 64, bool greedy = true, CancellationToken ct = default)
    {
        Interlocked.Increment(ref _literalCalls);
        return CompleteLiteralAsync(prompt, maxTokens, greedy, ct);
    }

    private Task<CompletionResult> CompleteLiteralAsync(string prompt, int maxTokens, bool greedy, CancellationToken ct)
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

    /// <summary>tokenize 透传（验证/对账通道；不在生成热路径上）。</summary>
    public Task<int[]> TokenizeAsync(string content, bool addSpecial = true, CancellationToken ct = default)
        => _client.TokenizeAsync(content, addSpecial, ct);

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

