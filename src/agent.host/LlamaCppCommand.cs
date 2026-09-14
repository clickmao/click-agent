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
///   agenthost --llamacpp --model &lt;gguf&gt; [--bin &lt;llama-server&gt;] (--chat-text &lt;s&gt; | --prompt &lt;s&gt; | --prompt-file &lt;f&gt;)
///            [--max-tokens N] [--expect-ids a,b,c] [--reuse on|off] [--json &lt;out&gt;]
///            （--reuse on = Session 口径开前缀缓存/K2b 用；off = Reconciliation 关缓存/对账用，默认 off）
///   agenthost --llamacpp --model &lt;gguf&gt; --verify-template [--chat-text &lt;s&gt;] [--prompt-file &lt;f&gt;]
///   agenthost --llamacpp --model &lt;embed-gguf&gt; --embed-text &lt;text&gt; [--json &lt;out&gt;]
///
/// R409 模板闸门: chat-text 走「模型元数据模板渲染」（服务端 /apply-template）⇒ 结构性无法手拼；
/// prompt/prompt-file 是**诊断通路**（绕过闸门、计入 LiteralPromptCalls），只用于与外部基线做 token id 逐位对账。
/// verify-template 对两条通路做 BOS 计数对账: 渲染通路必须恰好 1 个 BOS；字面串在默认 tokenization 下为 2 个（负控）。
///
/// 退出码: 0 正常（含 ids 一致）/ 2 用法错 / 3 id 与基线不一致 / 4 provider 不可用或 HTTP 失败 / 5 其它异常 / 6 模板验证未通过
/// </summary>
public static class LlamaCppCommand
{
    public static async Task<int> RunAsync(string[] args, TextWriter outp, TextWriter errp)
    {
        string? model = null, bin = null, prompt = null, promptFile = null, embed = null, jsonPath = null, expectIds = null, vecOut = null, chatText = null;
        var verifyTemplate = false;
        var reuse = CompletionReuse.Reconciliation;   // E2E 默认对账口径; 生产/会话演示须显式 --reuse on
        var maxTokens = 24;
        for (var i = 1; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--model": model = Val(args, ref i); break;
                case "--bin": bin = Val(args, ref i); break;
                case "--prompt": prompt = Val(args, ref i); break;
                case "--prompt-file": promptFile = Val(args, ref i); break;
                case "--chat-text": chatText = Val(args, ref i); break;
                case "--reuse":
                    var rv = Val(args, ref i);
                    if (rv is "on" or "session") reuse = CompletionReuse.Session;
                    else if (rv is "off" or "reconciliation") reuse = CompletionReuse.Reconciliation;
                    else { errp.WriteLine($"llamacpp: --reuse 只接受 on|off，实到 {rv}"); return 2; }
                    break;
                case "--verify-template": verifyTemplate = true; break;
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
        if (!isEmbed && !verifyTemplate && string.IsNullOrEmpty(prompt) && string.IsNullOrEmpty(promptFile) && string.IsNullOrEmpty(chatText))
        { errp.WriteLine("llamacpp: 缺 --chat-text/--prompt/--prompt-file（或 --embed-text / --verify-template）"); return 2; }
        if (prompt is not null && promptFile is not null)
        { errp.WriteLine("llamacpp: --prompt 与 --prompt-file 只能给一个"); return 2; }

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
                if (verifyTemplate)
                {
                    var (verify, verifyJson, verifyOk) = await RunVerifyTemplateAsync(provider, model, chatText, promptText).ConfigureAwait(false);
                    outp.WriteLine(verifyJson);
                    if (jsonPath is not null)
                    {
                        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(jsonPath))!);
                        await File.WriteAllTextAsync(jsonPath, verifyJson + "\n").ConfigureAwait(false);
                    }
                    if (!verifyOk)
                    {
                        errp.WriteLine($"llamacpp: 模板验证未通过 [{verify.Verdict}] (exit 6)");
                        return 6;
                    }
                    return 0;
                }

                var result = isEmbed
                    ? await RunEmbedAsync(provider, model, embed!, vecOut).ConfigureAwait(false)
                    : await RunGenerateAsync(provider, model, chatText, promptText, maxTokens, expectIds, reuse).ConfigureAwait(false);

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
        LlamaCppProvider provider, string model, string? chatText, string? literalPrompt, int maxTokens,
        string? expectIds, CompletionReuse reuse)
    {
        // R409: chatText 走闸门（模板来自模型元数据）；literalPrompt 走诊断通路（绕过闸门，计入 LiteralPromptCalls）。
        // R410: reuse = 口径开关（Session=开前缀缓存，K2b 用；Reconciliation=关缓存，对账用）。
        string promptMode;
        CompletionResult r;
        string promptSha;
        if (chatText is not null)
        {
            promptMode = "chat_template";
            var rendered = await provider.RenderAsync([new ChatTurn("user", chatText)]).ConfigureAwait(false);
            promptSha = Sha256Hex(Encoding.UTF8.GetBytes(rendered.Text));
            r = await provider.CompleteRenderedAsync(rendered, maxTokens, reuse: reuse).ConfigureAwait(false);
        }
        else
        {
            promptMode = "literal";
            promptSha = Sha256Hex(Encoding.UTF8.GetBytes(literalPrompt!));
            r = await provider.CompleteLiteralPromptAsync(literalPrompt!, maxTokens, reuse: reuse).ConfigureAwait(false);
        }

        int[] expected = [];
        if (!string.IsNullOrEmpty(expectIds))
        {
            expected = expectIds.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                .Select(s => int.Parse(s, CultureInfo.InvariantCulture)).ToArray();
        }
        return new LlamaCppE2EResult
        {
            Mode = "generate",
            PromptMode = promptMode,
            BaseUrl = provider.BaseUrl,
            Model = model,
            PromptSha256 = promptSha,
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
            TemplateRenders = provider.TemplateRenders,
            PromptGateRejections = provider.PromptGateRejections,
            LiteralPromptCalls = provider.LiteralPromptCalls,
            ReuseMode = reuse.ToString(),
            CachedTokens = r.CachedTokens,
            SessionReuseCalls = provider.SessionReuseCalls,
            ReconciliationCalls = provider.ReconciliationCalls,
            SessionCacheMisses = provider.SessionCacheMisses,
        };
    }

    /// <summary>
    /// R409 模板验证（判据预注册，两条通路对照）:
    ///   臂 A（受闸门保护）: messages → /apply-template 渲染 → tokenize(add_special=true) ⇒ 必须恰好 1 个 BOS；
    ///   臂 B（负控，可选）: 给定字面 prompt 文件 → tokenize(add_special=true) ⇒ 预期 2 个 BOS（BOS 文本 + 自动 BOS）；
    ///   交叉等价: ids(臂B, add_special=false) ≡ ids(臂A, add_special=true) 时记 IdsEquivalent=true。
    /// 通过判据: 臂 A 恰好 1 个 BOS 且（若给了负控）臂 B 恰好 2 个 BOS。
    /// </summary>
    private static async Task<(TemplateVerifyResult Result, string Json, bool Ok)> RunVerifyTemplateAsync(
        LlamaCppProvider provider, string model, string? chatText, string? literalPrompt)
    {
        var props = await provider.EnsurePropsAsync().ConfigureAwait(false);
        var probe = chatText ?? "What is 12*12? Answer with the number.";

        // BOS id 不硬编码：用模型元数据里的 BOS 文本自测（tokenize(add_special=false) ⇒ 结果只应含该文本本身）
        int[] bosIds = props.BosToken is { Length: > 0 } bt
            ? await provider.TokenizeAsync(bt, addSpecial: false).ConfigureAwait(false)
            : [];
        int? bosId = bosIds.Length == 1 ? bosIds[0] : null;

        var rendered = await provider.RenderAsync([new ChatTurn("user", probe)]).ConfigureAwait(false);
        var renderedTokens = await provider.TokenizeAsync(rendered.Text, addSpecial: true).ConfigureAwait(false);

        var result = new TemplateVerifyResult
        {
            Mode = "verify_template",
            BaseUrl = provider.BaseUrl,
            Model = model,
            BosToken = props.BosToken,
            EosToken = props.EosToken,
            ChatTemplateLength = props.ChatTemplateLength,
            BosId = bosId,
            RenderedBytes = Encoding.UTF8.GetByteCount(rendered.Text),
            RenderedSha256 = Sha256Hex(Encoding.UTF8.GetBytes(rendered.Text)),
            RenderedTokens = renderedTokens.Length,
            RenderedBosCount = bosId is null ? 0 : renderedTokens.Count(t => t == bosId.Value),
            RenderedHeadIds = [.. renderedTokens.Take(6)],
            TemplateRenders = provider.TemplateRenders,
        };

        if (literalPrompt is not null)
        {
            var litTokens = await provider.TokenizeAsync(literalPrompt, addSpecial: true).ConfigureAwait(false);
            var litNoSpecial = await provider.TokenizeAsync(literalPrompt, addSpecial: false).ConfigureAwait(false);
            result.LiteralBytes = Encoding.UTF8.GetByteCount(literalPrompt);
            result.LiteralSha256 = Sha256Hex(Encoding.UTF8.GetBytes(literalPrompt));
            result.LiteralTokens = litTokens.Length;
            result.LiteralBosCount = bosId is null ? 0 : litTokens.Count(t => t == bosId.Value);
            result.LiteralTokensNoSpecial = litNoSpecial.Length;
            result.IdsEquivalent = litNoSpecial.SequenceEqual(renderedTokens);
        }

        result.Verdict = bosId is null
            ? "no_bos_metadata"
            : renderedTokens.Length == 0
                ? "empty"
                : result.RenderedBosCount == 1
                    ? "gated_single_bos"
                    : "gated_bos_count_" + result.RenderedBosCount.ToString(CultureInfo.InvariantCulture);

        // 通过判据（预注册）：渲染通路 BOS 计数 == 1；若给出负控，其默认 tokenization 下 BOS 计数必须 > 1（证明确有冗余）。
        var ok = result.Verdict == "gated_single_bos"
                 && (result.LiteralBosCount is null || result.LiteralBosCount > 1);
        return (result, JsonSerializer.Serialize(result, LlamaCppE2EJsonContext.Default.TemplateVerifyResult), ok);
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
    /// <summary>prompt 通路来源: "chat_template" = 经 /apply-template 渲染（受闸门保护）；"literal" = 诊断通路（绕过闸门，计入 LiteralPromptCalls）。</summary>
    public string PromptMode { get; set; } = "";
    /// <summary>R410 生成口径: "Session"（开前缀缓存，K2b 用）/"Reconciliation"（关缓存，对账用）。</summary>
    public string ReuseMode { get; set; } = "";
    /// <summary>服务端自报的复用前缀 token 数（cache_n）；Reconciliation 口径下恒 0。</summary>
    public int CachedTokens { get; set; }
    /// <summary>被使用计数: 会话口径调用数。</summary>
    public long SessionReuseCalls { get; set; }
    /// <summary>被使用计数: 对账口径调用数。</summary>
    public long ReconciliationCalls { get; set; }
    /// <summary>会话口径下前缀未命中次数（静默失效可见化）。</summary>
    public long SessionCacheMisses { get; set; }
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
    /// <summary>被使用计数: 模板渲染次数（受闸门保护的生成通路）。</summary>
    public long TemplateRenders { get; set; }
    /// <summary>被使用计数: 被闸门拒收的生成请求数。</summary>
    public long PromptGateRejections { get; set; }
    /// <summary>被使用计数: 诊断字面通路调用次数（非 0 说明有调用方绕过模板闸门）。</summary>
    public long LiteralPromptCalls { get; set; }
}

/// <summary>R409 模板验证结果（判据预注册; 字段可空语义同 E2EResult）。</summary>
public sealed class TemplateVerifyResult
{
    public string Mode { get; set; } = "verify_template";
    public string BaseUrl { get; set; } = "";
    public string Model { get; set; } = "";
    public string? BosToken { get; set; }
    public string? EosToken { get; set; }
    public int ChatTemplateLength { get; set; }
    /// <summary>由模型元数据 BOS 文本自测得到的 token id（不硬编码）。</summary>
    public int? BosId { get; set; }
    /// <summary>臂 A（受闸门保护）: 渲染产物字节数 / sha256 / token 数 / BOS 计数 / 首 6 个 id。</summary>
    public int RenderedBytes { get; set; }
    public string RenderedSha256 { get; set; } = "";
    public int RenderedTokens { get; set; }
    public int RenderedBosCount { get; set; }
    public int[] RenderedHeadIds { get; set; } = [];
    /// <summary>臂 B（负控，未提供时为 null）: 字面串在默认/非默认 tokenization 下的读数。</summary>
    public int? LiteralBytes { get; set; }
    public string? LiteralSha256 { get; set; }
    public int? LiteralTokens { get; set; }
    public int? LiteralBosCount { get; set; }
    public int? LiteralTokensNoSpecial { get; set; }
    /// <summary>交叉等价: ids(字面串, add_special=false) ≡ ids(渲染产物, add_special=true)。</summary>
    public bool? IdsEquivalent { get; set; }
    public string Verdict { get; set; } = "";
    public long TemplateRenders { get; set; }
}

[JsonSerializable(typeof(LlamaCppE2EResult))]
[JsonSerializable(typeof(TemplateVerifyResult))]
[JsonSerializable(typeof(float[]))]
internal sealed partial class LlamaCppE2EJsonContext : JsonSerializerContext;
