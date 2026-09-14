using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using agent.llamacpp;

namespace agent.host;

/// <summary>
/// v0.30.0 R408（用户钦定：本地 GGUF 引擎整线退役 → llama.cpp 进程化接入）：
/// `--llamacpp` —— 用真实 llama-server 进程做一次生成/嵌入，并把读数写成 JSON。
///
/// 设计铁律：
///  1) **零 P/Invoke**：与 llama.cpp 的边界只有「进程 + loopback HTTP」，跨平台（每 RID 一份官方二进制）；
///  2) **可对账**：`--expect-ids` 给定外部基线 token id 序列 ⇒ 逐位比对，不一致 exit 3（不静默）；
///  3) **可观测**：端口被使用计数 (requests/tokens/embeddings) 与 base_url 一并落盘；
///  4) **不伪造**：二进制/模型缺失 ⇒ exit 4 `provider_unavailable`（显式失败，无兜底）；
///  5) **不 core dump**：HTTP 期异常一律收敛为退出码，绝不冒泡成未处理异常。
///
/// 用法:
///   agenthost --llamacpp --model &lt;gguf&gt; [--bin &lt;llama-server&gt;] (--prompt &lt;s&gt; | --prompt-file &lt;f&gt;)
///            [--max-tokens N] [--expect-ids a,b,c] [--json &lt;out&gt;]
///   agenthost --llamacpp --model &lt;embed-gguf&gt; --embed-text &lt;text&gt; [--json &lt;out&gt;]
///
/// 退出码: 0 正常（含 ids 一致）/ 2 用法错 / 3 id 与基线不一致 / 4 provider 不可用或 HTTP 失败 / 5 其它异常
/// </summary>
public static class LlamaCppCommand
{
    public static async Task<int> RunAsync(string[] args, TextWriter outp, TextWriter errp)
    {
        string? model = null, bin = null, prompt = null, promptFile = null, embed = null, jsonPath = null, expectIds = null, vecOut = null;
        var maxTokens = 24;
        for (var i = 1; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--model": model = Val(args, ref i); break;
                case "--bin": bin = Val(args, ref i); break;
                case "--prompt": prompt = Val(args, ref i); break;
                case "--prompt-file": promptFile = Val(args, ref i); break;
                case "--embed-text": embed = Val(args, ref i); break;
                case "--vec-out": vecOut = Val(args, ref i); break;
                case "--json": jsonPath = Val(args, ref i); break;
                case "--expect-ids": expectIds = Val(args, ref i); break;
                case "--max-tokens":
                    var mt = Val(args, ref i);
                    if (!int.TryParse(mt, NumberStyles.Integer, CultureInfo.InvariantCulture, out maxTokens) || maxTokens <= 0)
                    { errp.WriteLine($"llamacpp: --max-tokens 非法: {mt}"); return 2; }
                    break;
                default:
                    errp.WriteLine($"llamacpp: 未知参数 {args[i]}");
                    return 2;
            }
        }
        if (string.IsNullOrEmpty(model)) { errp.WriteLine("llamacpp: 缺 --model <gguf>"); return 2; }
        var isEmbed = !string.IsNullOrEmpty(embed);
        if (!isEmbed && string.IsNullOrEmpty(prompt) && string.IsNullOrEmpty(promptFile))
        { errp.WriteLine("llamacpp: 缺 --prompt/--prompt-file（或 --embed-text）"); return 2; }

        var promptText = prompt;
        if (!isEmbed && promptText is null && promptFile is not null)
        {
            try { promptText = await File.ReadAllTextAsync(promptFile).ConfigureAwait(false); }
            catch (Exception ex) { errp.WriteLine($"llamacpp: prompt 文件不可读 {promptFile}: {ex.Message}"); return 2; }
        }

        // EmbeddingMode: llama-server 的 /v1/embeddings 必须启动时加 --embeddings，
        // 且该开关与文本生成互斥（llama.cpp 限制）⇒ 生成/嵌入是两种进程形态。
        var opts = new LlamaServerOptions { ModelPath = model, BinaryPath = bin, Threads = 1, EmbeddingMode = isEmbed };
        try
        {
            await using var provider = await LlamaCppProvider.StartAsync(opts).ConfigureAwait(false);
            try
            {
                var result = isEmbed
                    ? await RunEmbedAsync(provider, model, embed!, vecOut).ConfigureAwait(false)
                    : await RunGenerateAsync(provider, model, promptText!, maxTokens, expectIds).ConfigureAwait(false);

                var json = JsonSerializer.Serialize(result, LlamaCppE2EJsonContext.Default.LlamaCppE2EResult);
                outp.WriteLine(json);
                if (jsonPath is not null)
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(jsonPath))!);
                    await File.WriteAllTextAsync(jsonPath, json + "\n").ConfigureAwait(false);
                }
                if (result.IdsMatch == false)
                {
                    errp.WriteLine("llamacpp: token id 与外部基线不一致 (exit 3)");
                    return 3;
                }
                return 0;
            }
            catch (LlamaCppException ex)
            {
                // 显式失败: provider_unavailable / http_error / malformed_response —— 绝不静默兜底
                errp.WriteLine($"llamacpp: {ex.Code}: {ex.Message}");
                return 4;
            }
        }
        catch (LlamaCppException ex)
        {
            errp.WriteLine($"llamacpp: {ex.Code}: {ex.Message}");
            return 4;
        }
        catch (Exception ex)
        {
            errp.WriteLine($"llamacpp: 内部异常 {ex.GetType().Name}: {ex.Message}");
            return 5;
        }
    }

    private static async Task<LlamaCppE2EResult> RunGenerateAsync(
        LlamaCppProvider provider, string model, string promptText, int maxTokens, string? expectIds)
    {
        var r = await provider.GenerateAsync(promptText, maxTokens).ConfigureAwait(false);
        int[] expected = [];
        if (!string.IsNullOrEmpty(expectIds))
        {
            expected = expectIds.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                .Select(s => int.Parse(s, CultureInfo.InvariantCulture)).ToArray();
        }
        return new LlamaCppE2EResult
        {
            Mode = "generate",
            BaseUrl = provider.BaseUrl,
            Model = model,
            PromptSha256 = Sha256Hex(Encoding.UTF8.GetBytes(promptText)),
            Content = r.Content,
            TokenIds = r.Tokens,
            TokensPredicted = r.PredictedTokens,
            TokensEvaluated = r.PromptTokens,
            PredictedPerSecond = Math.Round(r.PredictedPerSecond, 3),
            PromptPerSecond = Math.Round(r.PromptPerSecond, 3),
            ExpectedIds = expected,
            IdsMatch = expected.Length == 0 ? null : r.Tokens.SequenceEqual(expected),
            Requests = provider.RequestsServed,
            TokensGenerated = provider.TokensGenerated,
            EmbeddingsServed = provider.EmbeddingsServed,
        };
    }

    private static async Task<LlamaCppE2EResult> RunEmbedAsync(LlamaCppProvider provider, string model, string text, string? vecOut)
    {
        var vec = await provider.EmbedAsync(text).ConfigureAwait(false);
        if (vecOut is not null)
        {
            // 全量向量单独落盘 (跨实现对账用; 主结果只留 head+sha256 以免日志膨胀)
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(vecOut))!);
            await File.WriteAllTextAsync(vecOut, JsonSerializer.Serialize(vec, LlamaCppE2EJsonContext.Default.SingleArray)).ConfigureAwait(false);
        }
        var bytes = new byte[vec.Length * 4];
        Buffer.BlockCopy(vec, 0, bytes, 0, bytes.Length);
        double l2 = 0;
        foreach (var v in vec) l2 += (double)v * v;
        return new LlamaCppE2EResult
        {
            Mode = "embed",
            BaseUrl = provider.BaseUrl,
            Model = model,
            PromptSha256 = Sha256Hex(Encoding.UTF8.GetBytes(text)),
            EmbeddingDim = vec.Length,
            EmbeddingL2Norm = Math.Round(Math.Sqrt(l2), 6),
            EmbeddingSha256 = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant(),
            EmbeddingHead = vec.Take(8).Select(v => MathF.Round(v, 6)).ToArray(),
            Requests = provider.RequestsServed,
            TokensGenerated = provider.TokensGenerated,
            EmbeddingsServed = provider.EmbeddingsServed,
        };
    }

    private static string? Val(string[] args, ref int i) => i + 1 < args.Length ? args[++i] : null;

    private static string Sha256Hex(byte[] data) => Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant();
}

/// <summary>E2E 结果载体（字段可空语义: 未产出的读数显式为 null/0，读方不得当作"已测到"）。</summary>
public sealed class LlamaCppE2EResult
{
    public string Mode { get; set; } = "";
    public string BaseUrl { get; set; } = "";
    public string Model { get; set; } = "";
    public string PromptSha256 { get; set; } = "";
    public string? Content { get; set; }
    public int[]? TokenIds { get; set; }
    public int TokensPredicted { get; set; }
    public int TokensEvaluated { get; set; }
    public double PredictedPerSecond { get; set; }
    public double PromptPerSecond { get; set; }
    public int[]? ExpectedIds { get; set; }
    public bool? IdsMatch { get; set; }
    public int EmbeddingDim { get; set; }
    public double EmbeddingL2Norm { get; set; }
    public string? EmbeddingSha256 { get; set; }
    public float[]? EmbeddingHead { get; set; }
    public long Requests { get; set; }
    public long TokensGenerated { get; set; }
    public long EmbeddingsServed { get; set; }
}

[JsonSerializable(typeof(LlamaCppE2EResult))]
[JsonSerializable(typeof(float[]))]
internal sealed partial class LlamaCppE2EJsonContext : JsonSerializerContext;
