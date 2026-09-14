using System.Net.Http.Json;
using System.Text.Json;

namespace agent.llamacpp;

/// <summary>单次生成请求参数。默认口径 = R407 对账口径: 仅 temperature 采样器 + temp 0 (greedy)、关 cache_prompt。</summary>
public sealed record CompletionOptions
{
    public required string Prompt { get; init; }
    public int MaxTokens { get; init; } = 64;
    public string[] Samplers { get; init; } = ["temperature"];
    public float Temperature { get; init; }
    public int TopK { get; init; }
    public float TopP { get; init; } = 1f;
    public float MinP { get; init; }
    public float RepeatPenalty { get; init; } = 1f;
    public int Seed { get; init; }

    /// <summary>默认关: llama-server 文档明示启用后不同 batch 的 logits 不保证逐位一致 (对账不可复现)。</summary>
    public bool CachePrompt { get; init; }

    public bool ReturnTokens { get; init; } = true;
}

/// <summary>生成结果 (含原始 token id —— 数值对账的锚点)。</summary>
public sealed record CompletionResult(
    string Content,
    int[] Tokens,
    int PromptTokens,
    int PredictedTokens,
    double PredictedPerSecond,
    double PromptPerSecond,
    string RawJson);

/// <summary>
/// llama-server HTTP 客户端: 托管实现, 零 P/Invoke, 跨平台 (HttpClient 与进程二进制解耦)。
/// 端点契约: POST /completion (return_tokens ⇒ 原始 token id) / POST /v1/embeddings / GET /health。
/// </summary>
public sealed class LlamaCppClient : IDisposable
{
    private readonly HttpClient _http;
    private long _requests;
    private long _tokens;
    private long _embeddings;

    public LlamaCppClient(string baseUrl, TimeSpan? timeout = null)
    {
        _http = new HttpClient
        {
            BaseAddress = new Uri(baseUrl.TrimEnd('/') + "/"),
            Timeout = timeout ?? TimeSpan.FromMinutes(30),
        };
    }

    public string BaseUrl => _http.BaseAddress!.ToString().TrimEnd('/');

    /// <summary>被使用计数 (端口化纪律: 真实派发计数, 非估算)。</summary>
    public long RequestsServed => Interlocked.Read(ref _requests);

    /// <summary>已生成的 token 总数 (来自服务端返回的 tokens 字段)。</summary>
    public long TokensGenerated => Interlocked.Read(ref _tokens);

    /// <summary>已返回的向量条数。</summary>
    public long EmbeddingsServed => Interlocked.Read(ref _embeddings);

    public async Task<CompletionResult> CompleteAsync(CompletionOptions o, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(o);
        Interlocked.Increment(ref _requests);

        var req = new CompletionRequest
        {
            Prompt = o.Prompt,
            NPredict = o.MaxTokens,
            Samplers = o.Samplers,
            Temperature = o.Temperature,
            TopK = o.TopK,
            TopP = o.TopP,
            MinP = o.MinP,
            RepeatPenalty = o.RepeatPenalty,
            Seed = o.Seed,
            CachePrompt = o.CachePrompt,
            ReturnTokens = o.ReturnTokens,
            Stream = false,
            NProbs = 0,
        };

        using var resp = await _http.PostAsync("completion",
            JsonContent.Create(req, LlamaCppJsonContext.Default.CompletionRequest), ct).ConfigureAwait(false);
        var body = await resp.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode)
            throw new LlamaCppException(LlamaCppException.HttpError,
                $"POST /completion → {(int)resp.StatusCode}: {Truncate(body, 400)}");

        CompletionResponse? r;
        try { r = JsonSerializer.Deserialize(body, LlamaCppJsonContext.Default.CompletionResponse); }
        catch (JsonException ex)
        {
            throw new LlamaCppException(LlamaCppException.MalformedResponse,
                $"POST /completion 响应无法解析: {Truncate(body, 200)}", ex);
        }

        if (r is null)
            throw new LlamaCppException(LlamaCppException.MalformedResponse, "POST /completion 返回 null 响应体");

        var tokens = r.Tokens ?? [];
        if (tokens.Length > 0) Interlocked.Add(ref _tokens, tokens.Length);

        return new CompletionResult(
            r.Content ?? string.Empty,
            tokens,
            r.TokensEvaluated,
            r.TokensPredicted,
            r.Timings?.PredictedPerSecond ?? 0,
            r.Timings?.PromptPerSecond ?? 0,
            body);
    }

    /// <summary>文本 → 向量 (/v1/embeddings; 服务端按欧氏范数归一化)。批量输入 ≤ 服务端上限。</summary>
    public async Task<float[][]> EmbedAsync(IReadOnlyList<string> texts, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(texts);
        if (texts.Count == 0) return [];
        Interlocked.Increment(ref _requests);

        var req = new EmbeddingRequest { Input = [.. texts] };
        using var resp = await _http.PostAsync("v1/embeddings",
            JsonContent.Create(req, LlamaCppJsonContext.Default.EmbeddingRequest), ct).ConfigureAwait(false);
        var body = await resp.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode)
            throw new LlamaCppException(LlamaCppException.HttpError,
                $"POST /v1/embeddings → {(int)resp.StatusCode}: {Truncate(body, 400)}");

        EmbeddingResponse? r;
        try { r = JsonSerializer.Deserialize(body, LlamaCppJsonContext.Default.EmbeddingResponse); }
        catch (JsonException ex)
        {
            throw new LlamaCppException(LlamaCppException.MalformedResponse,
                $"POST /v1/embeddings 响应无法解析: {Truncate(body, 200)}", ex);
        }

        if (r is null || r.Data.Length == 0)
            throw new LlamaCppException(LlamaCppException.MalformedResponse, "POST /v1/embeddings 未返回向量");

        var vectors = r.Data.OrderBy(d => d.Index).Select(d => d.Embedding).ToArray();
        Interlocked.Add(ref _embeddings, vectors.Length);
        return vectors;
    }

    /// <summary>健康检查 (/health: 200 = 就绪; 503 = 仍在加载)。</summary>
    public async Task<string?> HealthAsync(CancellationToken ct = default)
    {
        using var resp = await _http.GetAsync("health", ct).ConfigureAwait(false);
        if (!resp.IsSuccessStatusCode) return null;
        var body = await resp.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
        try { return JsonSerializer.Deserialize(body, LlamaCppJsonContext.Default.HealthResponse)?.Status; }
        catch (JsonException) { return null; }
    }

    private static string Truncate(string s, int n) => s.Length <= n ? s : s[..n] + "…";

    public void Dispose() => _http.Dispose();
}
