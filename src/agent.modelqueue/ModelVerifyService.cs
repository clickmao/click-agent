using System.Text.Json;

namespace agent.modelqueue;

/// <summary>模型校验结果 (C.6.5 — JSON 输出)</summary>
public sealed class ModelVerifyResult
{
    public string Command { get; set; } = "model_verify";
    public string Model { get; set; } = string.Empty;
    public bool Ok { get; set; }

    /// <summary>HTTP 状态码 (0 = 网络/ DNS 失败)</summary>
    public int HttpStatusCode { get; set; }

    /// <summary>判定说明 (401/403 = 地址正确+鉴权拒绝 = 合法; 404/DNS = 参数错误)</summary>
    public string Verdict { get; set; } = string.Empty;

    public string? Error { get; set; }
}

/// <summary>
/// 模型目录真实性校验 (v7.15 C.6.5 — 用户硬性要求):
/// 新增模型默认参数必须真实正确 → 实际 http 请求校验:
/// 向 endpoint 发最小 chat completions 请求 (max_tokens=1), api-key 随意填 "sk-invalid-probe" —
/// 期望 401/403 (地址正确+鉴权拒绝) = 合法; 404/DNS 失败/超时 = 地址错误。
/// 合法性判据不依赖真 key, 任何人任何时候可跑。
/// </summary>
public sealed class ModelVerifyService
{
    private readonly ModelCatalog _catalog;
    private readonly IHttpClientFactory _httpClientFactory;

    public ModelVerifyService(ModelCatalog catalog, IHttpClientFactory httpClientFactory)
    {
        _catalog = catalog;
        _httpClientFactory = httpClientFactory;
    }

    public async Task<ModelVerifyResult> VerifyAsync(string modelId, CancellationToken ct = default)
    {
        var entry = _catalog.Find(modelId);
        if (entry is null)
        {
            return new ModelVerifyResult
            {
                Model = modelId, Ok = false, Error = "目录中无此模型 id",
            };
        }

        var result = new ModelVerifyResult { Model = entry.Id };
        try
        {
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            cts.CancelAfter(TimeSpan.FromSeconds(15));
            var client = _httpClientFactory.CreateClient("modelqueue");
            var probe = new QueueChatRequest
            {
                Model = entry.Id,
                Messages = new()
                {
                    new QueueChatMessage { Role = "user", Content = "ping" },
                },
                MaxTokens = 1,
            };
            using var http = new HttpRequestMessage(HttpMethod.Post, entry.Endpoint)
            {
                Content = new StringContent(
                    JsonSerializer.Serialize(probe, ModelQueueJsonContext.Default.QueueChatRequest),
                    new System.Net.Http.Headers.MediaTypeHeaderValue("application/json")),
            };
            // 随意填的假 key — 期望鉴权层拒绝 (C.6.5: "api-key可以随意填写")
            http.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue(
                "Bearer", "sk-invalid-probe");

            using var resp = await client.SendAsync(http, cts.Token);
            result.HttpStatusCode = (int)resp.StatusCode;
            var code = (int)resp.StatusCode;
            if (code is 401 or 403)
            {
                result.Ok = true;
                result.Verdict = $"HTTP {code} = 地址正确且鉴权拒绝 (假 key 符合预期) — 模型参数合法";
            }
            else if (code == 404)
            {
                result.Ok = false;
                result.Verdict = "HTTP 404 = 端点路径错误 (检查 endpoint 配置)";
            }
            else if (code == 429)
            {
                // 429 = 地址正确且请求到达业务层 (限流) — 同样证明端点合法
                result.Ok = true;
                result.Verdict = "HTTP 429 = 端点正确且触发限流 — 模型参数合法";
            }
            else
            {
                result.Ok = false;
                result.Verdict = $"HTTP {code} = 未预期状态 (人工复核)";
            }
        }
        catch (HttpRequestException ex)
        {
            result.Ok = false;
            result.Error = $"网络失败 (DNS/连接): {ex.Message}";
        }
        catch (TaskCanceledException) when (!ct.IsCancellationRequested)
        {
            result.Ok = false;
            result.Error = "校验请求 15s 超时 (端点不可达/过慢/DNS 阻塞)";
        }
        catch (Exception ex)
        {
            // 兜底: RST/TLS 断/DNS 等一切网络异常 → 归一 UNREACHABLE (verify 契约: 恒返回结果, 不冒泡)
            result.Ok = false;
            result.Error = $"网络不可达: {ex.GetType().Name}: {ex.Message}";
        }
        return result;
    }
}
