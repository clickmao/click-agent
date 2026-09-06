using System.Text.Json;

namespace agent.modelqueue;

/// <summary>余额查询结果 (C.3.5: JSON 输出可被程序解析; 不支持/失败诚实报错, 不编造数字)</summary>
public sealed class BalanceResult
{
    public string Command { get; set; } = "balance";
    public bool Ok { get; set; }
    public string Model { get; set; } = string.Empty;
    public string? Provider { get; set; }

    /// <summary>余额数值 (provider 语义不同: OpenAI=USD 上限, DeepSeek=USD 余额)</summary>
    public double? TotalGranted { get; set; }
    public double? TotalUsed { get; set; }
    public double? TotalRemaining { get; set; }

    /// <summary>v0.11.0 R15: 原始币种 (USD/CNY/…) — 空串=未声明 (按 USD 处理并标注)</summary>
    public string Currency { get; set; } = string.Empty;

    public string? Error { get; set; }

    /// <summary>provider 不支持时的调研备注 (目录 balance_schemes.note)</summary>
    public string? Note { get; set; }
}

/// <summary>
/// 余额查询服务 (v7.15 C.3.5 + C.6.4):
/// 按目录 balance_schemes scheme 分派 — 各 provider 接口差异大 (调研结论见 models.yaml 注释):
///   openai = /dashboard/billing/subscription (hard_limit_usd 作额度上界; credit_grants 已废弃)
///   deepseek = GET /user/balance (balance_infos[0].balance)
///   其他 provider → ok:false + provider_not_supported (诚实报错)
/// 凭据零落盘: key 只从 api_key_env 环境变量读。10s 超时不阻断 REPL。
/// </summary>
public sealed class BalanceQueryService
{
    private readonly ModelCatalog _catalog;
    private readonly IHttpClientFactory _httpClientFactory;

    public BalanceQueryService(ModelCatalog catalog, IHttpClientFactory httpClientFactory)
    {
        _catalog = catalog;
        _httpClientFactory = httpClientFactory;
    }

    public async Task<BalanceResult> QueryAsync(string? modelId = null, CancellationToken ct = default)
    {
        var entry = _catalog.Find(modelId) ?? _catalog.Models.FirstOrDefault();
        if (entry is null)
        {
            return new BalanceResult { Ok = false, Error = "模型目录为空", Model = modelId ?? "" };
        }

        var result = new BalanceResult { Model = entry.Id, Provider = entry.Provider };

        if (!_catalog.BalanceSchemes.TryGetValue(entry.Provider, out var scheme))
        {
            result.Error = "provider_not_supported";
            result.Note = $"provider {entry.Provider} 无余额查询方案 (目录 balance_schemes 未配置)";
            return result;
        }

        var apiKey = Environment.GetEnvironmentVariable(entry.ApiKeyEnv);
        if (string.IsNullOrEmpty(apiKey))
        {
            result.Error = $"环境变量 {entry.ApiKeyEnv} 未设置";
            return result;
        }

        try
        {
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            cts.CancelAfter(TimeSpan.FromSeconds(10));
            var client = _httpClientFactory.CreateClient("modelqueue");
            using var http = new HttpRequestMessage(HttpMethod.Get, scheme.Endpoint);
            http.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", apiKey);
            using var resp = await client.SendAsync(http, cts.Token);
            var body = await resp.Content.ReadAsStringAsync(cts.Token);

            if (!resp.IsSuccessStatusCode)
            {
                result.Error = $"provider_http_{(int)resp.StatusCode}";
                result.Note = $"余额端点返回非成功状态 (端点/鉴权问题): {scheme.Endpoint}";
                return result;
            }

            using var doc = JsonDocument.Parse(body);
            switch (entry.Provider.ToLowerInvariant())
            {
                case "openai":
                {
                    // subscription: hard_limit_usd / system_hard_limit_usd — 额度上界 (诚实标注语义)
                    if (doc.RootElement.TryGetProperty("hard_limit_usd", out var hard))
                    {
                        result.TotalGranted = hard.GetDouble();
                        result.Note = "OpenAI subscription 端点: hard_limit_usd 为额度上界 (credit_grants 已废弃)";
                    }
                    else
                    {
                        result.Error = "unexpected_response_shape";
                    }
                    break;
                }
                case "deepseek":
                {
                    // /user/balance 真实 shape (2026-09-06 真机溯源):
                    // {"is_available":true,"balance_infos":[{"currency":"CNY","total_balance":"9.49",...}]}
                    // v0.11.0 修复: 字段是 total_balance (旧代码读 balance → 永远 shape 失配); currency 透出 Note
                    if (doc.RootElement.TryGetProperty("balance_infos", out var infos) &&
                        infos.ValueKind == JsonValueKind.Array && infos.GetArrayLength() > 0 &&
                        infos[0].TryGetProperty("total_balance", out var bal) &&
                        double.TryParse(bal.GetString(), System.Globalization.CultureInfo.InvariantCulture, out var v))
                    {
                        result.TotalRemaining = v;
                        if (infos[0].TryGetProperty("currency", out var cur))
                        {
                            result.Currency = cur.GetString() ?? string.Empty;
                            result.Note = $"币种 {result.Currency}";
                        }
                    }
                    else
                    {
                        result.Error = "unexpected_response_shape";
                    }
                    break;
                }
                default:
                    result.Error = "provider_not_supported";
                    break;
            }
            result.Ok = result.Error is null;
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            result.Error = "timeout";
            result.Note = "余额查询 10s 超时 (不阻断 REPL)";
        }
        catch (HttpRequestException ex)
        {
            result.Error = $"network_error: {ex.Message}";
        }
        catch (JsonException)
        {
            result.Error = "invalid_provider_response";
        }
        return result;
    }
}
