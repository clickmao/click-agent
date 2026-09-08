using System.Net.Http.Headers;
using agent.config;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.modelqueue;

/// <summary>
/// v0.12.0 CogView 文生图客户端 (计划2 §1) — 协议真机核实 2026-09-08:
/// POST {endpoint} {"model":"cogview-3-flash","prompt":"...","size":"1024x1024"} → {"data":[{"url":...}]}
/// 打点: AgentTelemetry point=image_gen (kv: model, prompt_chars, size, ms, ok, file_bytes)。
/// </summary>
public sealed class CogViewClient
{
    private static readonly JsonSerializerOptions JsonOpts = new(JsonSerializerDefaults.Web);
    private readonly HttpClient _http;
    private readonly string _apiKey;

    public CogViewClient(HttpClient http, string apiKey)
    {
        _http = http;
        _apiKey = apiKey;
    }

    /// <summary>生图请求 DTO (source-gen 友好: 显式属性, 禁匿名类型)</summary>
    public sealed class CogViewRequest
    {
        [JsonPropertyName("model")]
        public string Model { get; set; } = "cogview-3-flash";

        [JsonPropertyName("prompt")]
        public string Prompt { get; set; } = string.Empty;

        [JsonPropertyName("size")]
        public string Size { get; set; } = "1024x1024";
    }

    public sealed class CogViewResponse
    {
        [JsonPropertyName("data")]
        public List<CogViewImage>? Data { get; set; }

        [JsonPropertyName("error")]
        public CogViewError? Error { get; set; }
    }

    public sealed class CogViewImage
    {
        [JsonPropertyName("url")]
        public string Url { get; set; } = string.Empty;
    }

    public sealed class CogViewError
    {
        [JsonPropertyName("code")]
        public string Code { get; set; } = string.Empty;

        [JsonPropertyName("message")]
        public string Message { get; set; } = string.Empty;
    }

    /// <summary>生图结果 — Url 为远端地址, LocalPath 为已下载落盘路径 (可选)。</summary>
    public sealed class CogViewResult
    {
        public bool Ok { get; set; }
        public string? Url { get; set; }
        public string? LocalPath { get; set; }
        public string? Error { get; set; }
        public int WallMs { get; set; }
        public long FileBytes { get; set; }
    }

    /// <summary>
    /// 生成图像并可选下载落盘。任何失败不抛异常 — 结果对象携带 Error (打点/上层判定)。
    /// </summary>
    public async Task<CogViewResult> GenerateAsync(
        string prompt, string endpoint, string model, string size,
        string? savePath = null, CancellationToken ct = default)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var result = new CogViewResult();
        try
        {
            var req = new HttpRequestMessage(HttpMethod.Post, endpoint)
            {
                Content = new StringContent(
                    JsonSerializer.Serialize(new CogViewRequest { Model = model, Prompt = prompt, Size = size }, JsonOpts),
                    Encoding.UTF8, "application/json"),
            };
            req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _apiKey);

            using var resp = await _http.SendAsync(req, ct);
            var body = await resp.Content.ReadAsStringAsync(ct);
            if (!resp.IsSuccessStatusCode)
            {
                result.Error = $"HTTP {(int)resp.StatusCode}: {Truncate(body)}";
                return Finish(result, sw, prompt, model, size);
            }

            var parsed = JsonSerializer.Deserialize<CogViewResponse>(body, JsonOpts);
            if (parsed?.Error is { } err)
            {
                result.Error = $"{err.Code}: {Truncate(err.Message)}";
                return Finish(result, sw, prompt, model, size);
            }
            var url = parsed?.Data is { Count: > 0 } list ? list[0].Url : null;
            if (string.IsNullOrEmpty(url))
            {
                result.Error = "响应无 data[0].url";
                return Finish(result, sw, prompt, model, size);
            }
            result.Url = url;

            if (savePath != null)
            {
                var imgBytes = await _http.GetByteArrayAsync(url, ct);
                Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(savePath))!);
                await File.WriteAllBytesAsync(savePath, imgBytes, ct);
                result.LocalPath = savePath;
                result.FileBytes = imgBytes.Length;
                if (result.FileBytes < 10_000)
                    result.Error = $"图像过小 ({result.FileBytes}B) — 疑似空图";
            }
            result.Ok = string.IsNullOrEmpty(result.Error);
            return Finish(result, sw, prompt, model, size);
        }
        catch (OperationCanceledException) when (ct.IsCancellationRequested)
        {
            result.Error = "cancelled";
            return Finish(result, sw, prompt, model, size);
        }
        catch (Exception ex)
        {
            result.Error = Truncate(ex.Message);
            return Finish(result, sw, prompt, model, size);
        }
    }

    private static CogViewResult Finish(CogViewResult r, System.Diagnostics.Stopwatch sw, string prompt, string model, string size)
    {
        r.WallMs = (int)sw.ElapsedMilliseconds;
        try
        {
            AgentTelemetry.Emit("image_gen", "CogViewClient",
                ("model", model),
                ("prompt_chars", prompt.Length),
                ("size", size),
                ("ms", r.WallMs),
                ("ok", r.Ok),
                ("file_bytes", r.FileBytes),
                ("error", r.Error));
        }
        catch { /* 打点绝不影响主链路 */ }
        return r;
    }

    private static string Truncate(string s) => s.Length <= 200 ? s : s[..200];
}
