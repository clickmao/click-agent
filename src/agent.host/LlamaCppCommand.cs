using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using agent.llamacpp;
using agent.modelqueue;

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
///   agenthost --llamacpp --model &lt;gguf&gt; --session-json &lt;req.json&gt; [--session-id &lt;s&gt;] [--context N] [--json &lt;out&gt;]
///            （R411 长驻多轮: 单进程内一个 server 逐轮生成，逐轮落 K2b 台账；红线越线 ⇒ exit 7）
///
/// R409 模板闸门: chat-text 走「模型元数据模板渲染」（服务端 /apply-template）⇒ 结构性无法手拼；
/// prompt/prompt-file 是**诊断通路**（绕过闸门、计入 LiteralPromptCalls），只用于与外部基线做 token id 逐位对账。
/// verify-template 对两条通路做 BOS 计数对账: 渲染通路必须恰好 1 个 BOS；字面串在默认 tokenization 下为 2 个（负控）。
///
/// 退出码: 0 正常（含 ids 一致）/ 2 用法错 / 3 id 与基线不一致 / 4 provider 不可用或 HTTP 失败 / 5 其它异常 / 6 模板验证未通过
///          7 = R411 会话 K2b 红线越线（非首轮前缀复用率未达 97% 且前缀短于算术必需长度）
/// </summary>
public static class LlamaCppCommand
{
    public static async Task<int> RunAsync(string[] args, TextWriter outp, TextWriter errp)
    {
        string? model = null, bin = null, prompt = null, promptFile = null, embed = null, jsonPath = null, expectIds = null, vecOut = null, chatText = null, systemFile = null;
        string? sessionJson = null, sessionIdOverride = null;
        var verifyTemplate = false;
        var contextSize = 6144;
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
                case "--system-file": systemFile = Val(args, ref i); break;
                case "--reuse":
                    var rv = Val(args, ref i);
                    if (rv is "on" or "session") reuse = CompletionReuse.Session;
                    else if (rv is "off" or "reconciliation") reuse = CompletionReuse.Reconciliation;
                    else { errp.WriteLine($"llamacpp: --reuse 只接受 on|off，实到 {rv}"); return 2; }
                    break;
                case "--session-json": sessionJson = Val(args, ref i); break;
                case "--session-id": sessionIdOverride = Val(args, ref i); break;
                case "--context":
                    var cs = Val(args, ref i);
                    if (!int.TryParse(cs, NumberStyles.Integer, CultureInfo.InvariantCulture, out contextSize) || contextSize <= 0)
                    { errp.WriteLine($"llamacpp: --context 非法: {cs}"); return 2; }
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
        var isSession = sessionJson is not null;
        if (!isEmbed && !verifyTemplate && !isSession && string.IsNullOrEmpty(prompt) && string.IsNullOrEmpty(promptFile) && string.IsNullOrEmpty(chatText))
        { errp.WriteLine("llamacpp: 缺 --chat-text/--prompt/--prompt-file（或 --embed-text / --verify-template / --session-json）"); return 2; }
        if (prompt is not null && promptFile is not null)
        { errp.WriteLine("llamacpp: --prompt 与 --prompt-file 只能给一个"); return 2; }

        var promptText = prompt;
        if (!isEmbed && promptText is null && promptFile is not null)
        {
            try { promptText = await File.ReadAllTextAsync(promptFile).ConfigureAwait(false); }
            catch (Exception ex) { errp.WriteLine($"llamacpp: prompt 文件不可读 {promptFile}: {ex.Message}"); return 2; }
        }

        // R410: 会话长前缀入口（K2b 的前提是「稳定长前缀 + 长驻 server + cache 开」）。
        string? systemText = null;
        if (systemFile is not null)
        {
            if (string.IsNullOrEmpty(chatText))
            { errp.WriteLine("llamacpp: --system-file 需要同时给 --chat-text"); return 2; }
            try { systemText = await File.ReadAllTextAsync(systemFile).ConfigureAwait(false); }
            catch (Exception ex) { errp.WriteLine($"llamacpp: system 文件不可读 {systemFile}: {ex.Message}"); return 2; }
        }

        // R411: 长驻多轮会话（单进程内一个 llama-server 跨轮复用；逐轮落 K2b 台账）。
        // 本路径自管宿主生命周期 ⇒ 必须发生在下面单发 provider 启动之前。
        if (sessionJson is not null)
        {
            // 输入解析失败 ⇒ 用法错 (exit 2)；运行期失败 ⇒ 4/5（与单发通路一致，绝不 core dump）。
            if (!TryReadSessionRequest(sessionJson, errp, out var request, out var sessionSystemText)) return 2;
            try
            {
                var (session, sessionOk) = await RunSessionAsync(
                    model, bin, request!, sessionSystemText, sessionIdOverride, maxTokens, contextSize).ConfigureAwait(false);
                var sjson = JsonSerializer.Serialize(session, LlamaCppE2EJsonContext.Default.LlamaCppSessionResult);
                outp.WriteLine(sjson);
                if (jsonPath is not null)
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(jsonPath))!);
                    await File.WriteAllTextAsync(jsonPath, sjson + "\n").ConfigureAwait(false);
                }
                if (!sessionOk)
                {
                    errp.WriteLine($"llamacpp: 会话 K2b 红线越线 (violations={session.Violations}, last_eff={session.EffectiveHitRateLast}) ⇒ exit 7");
                    return 7;
                }
                return 0;
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
                    : await RunGenerateAsync(provider, model, chatText, promptText, maxTokens, expectIds, reuse, systemText).ConfigureAwait(false);

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
        string? expectIds, CompletionReuse reuse, string? systemText = null)
    {
        // R409: chatText 走闸门（模板来自模型元数据）；literalPrompt 走诊断通路（绕过闸门，计入 LiteralPromptCalls）。
        // R410: reuse = 口径开关（Session=开前缀缓存，K2b 用；Reconciliation=关缓存，对账用）。
        // R410: systemText = 会话长前缀（K2b 复用对象；与 user 轮同处一个 message 列表）。
        string promptMode;
        CompletionResult r;
        string promptSha;
        if (chatText is not null)
        {
            promptMode = "chat_template";
            var turns = new List<ChatTurn>();
            if (!string.IsNullOrEmpty(systemText)) turns.Add(new ChatTurn("system", systemText));
            turns.Add(new ChatTurn("user", chatText));
            var rendered = await provider.RenderAsync(turns).ConfigureAwait(false);
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

    /// <summary>
    /// R411 长驻多轮会话：单进程内一个 llama-server，逐轮复用同一 KV 前缀缓存，逐轮落 K2b 台账。
    ///
    /// 判据（开跑前登记）:
    ///   ① **长驻**: 全程 <c>ProcessStarts == 1</c>（跨轮不重启；重启 ⇒ 前序 KV 缓存丢）；
    ///   ② **跨轮复用**: 非首轮 <c>CachedTokens &gt; 0</c> 且 携带复用率 ≥ 97%；
    ///   ③ **绝对长度**: 冷启首轮总长 ≥ 4224（R410: 比值不是 KPI）—— 比值达标但前缀太薄同样判越线；
    ///   ④ 任一越线 ⇒ <c>Violations &gt; 0</c> ⇒ 返回 false（exit 7）。
    /// 三条件缺「长驻」时 ②③ 全不成立（R410 实测: 每次新起 server ⇒ cached=0）。
    /// </summary>
    private static async Task<(LlamaCppSessionResult Result, bool Ok)> RunSessionAsync(
        string model, string? bin, LlamaCppSessionRequest req, string? systemText, string? sessionIdOverride, int maxTokens, int contextSize)
    {
        var sessionId = sessionIdOverride ?? req.SessionId ?? "e2e-session";
        var options = new LlamaCppGeneratorOptions
        {
            ModelPath = model,
            BinaryPath = bin,
            MaxTokens = req.MaxTokens ?? maxTokens,
            ContextSize = contextSize,
        };

        await using var generator = new LlamaCppTextGenerator(options);
        var ledger = new LocalSessionCacheLedger();
        LocalCacheObservation lastObs = default;
        generator.OnTurnCompleted = (key, turn, total, cached, ceiling) =>
            lastObs = ledger.Observe(key, turn, total, cached, ceiling, model);

        var history = new List<ChatTurn>();
        if (systemText is not null) history.Add(new ChatTurn("system", systemText));
        var turns = new List<LlamaCppSessionTurnResult>();
        var systemTokens = 0;

        for (var k = 0; k < req.Turns.Count; k++)
        {
            history.Add(new ChatTurn("user", req.Turns[k]));
            var r = await generator.GenerateTurnAsync(history, sessionId, k + 1).ConfigureAwait(false);
            if (k == 0) systemTokens = generator.LastPromptTokens;   // 冷启首轮总长 = 前缀 + 首轮输入 + 模板
            var cached = Math.Max(0, r.CachedTokens);
            turns.Add(new LlamaCppSessionTurnResult
            {
                Turn = k + 1,
                PromptTokens = generator.LastPromptTokens,
                PromptTokensRecomputed = generator.LastPromptTokensRecomputed,
                CachedTokens = cached,
                GeneratedTokens = generator.LastGeneratedTokens,
                CarryOverTokens = lastObs.CarryOverTokens,
                CarryOverReuse = lastObs.CarryOverReuse,
                SessionReuseRatio = lastObs.SessionReuseRatio,
                PrefixTokens = lastObs.PrefixTokens,
                PrefixLengthSatisfied = lastObs.PrefixLengthSatisfied,
                RedlineApplies = lastObs.RedlineApplies,
                Violated = lastObs.Violated,
                Diagnosis = lastObs.Diagnosis,
                Content = r.Content,
                ProcessStarts = generator.ProcessStarts,
            });
            // 助手输出回填历史 ⇒ 下一轮的前缀 = 本轮全量 ⇒ 可复用性由服务端前缀匹配决定（真实会话形态）。
            history.Add(new ChatTurn("assistant", r.Content ?? string.Empty));
        }

        var last = turns[^1];
        var result = new LlamaCppSessionResult
        {
            SessionId = sessionId,
            Model = model,
            ProcessStarts = generator.ProcessStarts,
            Turns = generator.TurnsGenerated,
            Observations = ledger.Observations,
            Violations = ledger.Violations,
            NotApplicable = ledger.NotApplicable,
            Abstained = ledger.Abstained,
            CacheMissTurns = generator.CacheMissTurns,
            SystemTokens = systemTokens,
            RequiredPrefixTokens = LocalSessionCacheLedger.RequiredPrefixTokens,
            CarryOverReuseLast = last.CarryOverReuse,
            SessionReuseRatioLast = last.SessionReuseRatio,
            EffectiveHitRateLast = last.CarryOverReuse,
            LongLived = generator.ProcessStarts == 1,
            CrossTurnReuse = last.CachedTokens > 0,
            TurnResults = turns,
        };
        return (result, ledger.Violations == 0);
    }

    /// <summary>
    /// 读入并校验 <c>--session-json</c> 请求。**解析/校验失败一律走用法错 (exit 2)**，不抛到运行期。
    /// 键名大小写不敏感（见 <see cref="LlamaCppE2EJsonContext"/> 的 <c>PropertyNameCaseInsensitive</c>）
    /// —— 请求文件格式不得对大小写敏感（R411 首跑就踩了这个坑：小写 `turns` 反序列化成空）。
    /// </summary>
    private static bool TryReadSessionRequest(string path, TextWriter errp,
        out LlamaCppSessionRequest? request, out string? systemText)
    {
        request = null;
        systemText = null;
        if (!File.Exists(path)) { errp.WriteLine($"llamacpp: --session-json 文件不存在 {path}"); return false; }

        string raw;
        try { raw = File.ReadAllText(path); }
        catch (Exception ex) { errp.WriteLine($"llamacpp: --session-json 不可读 {path}: {ex.Message}"); return false; }

        try { request = JsonSerializer.Deserialize(raw, LlamaCppE2EJsonContext.Default.LlamaCppSessionRequest); }
        catch (Exception ex) { errp.WriteLine($"llamacpp: --session-json 不可解析 {path}: {ex.Message}"); return false; }

        if (request is null || request.Turns.Count == 0)
        {
            errp.WriteLine($"llamacpp: --session-json 无 turns（键名大小写不敏感，但 turns 必须非空） {path}");
            return false;
        }

        systemText = request.SystemText;
        if (!string.IsNullOrEmpty(request.SystemFile))
        {
            if (!File.Exists(request.SystemFile)) { errp.WriteLine($"llamacpp: system 文件不存在 {request.SystemFile}"); return false; }
            try { systemText = File.ReadAllText(request.SystemFile); }
            catch (Exception ex) { errp.WriteLine($"llamacpp: system 文件不可读 {request.SystemFile}: {ex.Message}"); return false; }
        }
        return true;
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

/// <summary>R411 多轮会话请求（长驻进程内逐轮生成；K2b 观测用）。</summary>
public sealed class LlamaCppSessionRequest
{
    public string? SessionId { get; set; }
    /// <summary>稳定长前缀（system 文本）文件；与 <see cref="SystemText"/> 二者其一。</summary>
    public string? SystemFile { get; set; }
    public string? SystemText { get; set; }
    public List<string> Turns { get; set; } = [];
    public int? MaxTokens { get; set; }
}

/// <summary>
/// R411 单轮读数。口径（独立实现钉死，**别按字段名猜**）:
/// <see cref="PromptTokens"/> = **总长** = llama.cpp <c>tokens_evaluated</c>（含 BOS）；
/// <see cref="PromptTokensRecomputed"/> = 总长 − 命中 = <c>timings.prompt_n</c>。
/// </summary>
public sealed class LlamaCppSessionTurnResult
{
    public int Turn { get; set; }
    /// <summary>本轮 prompt 总长（tokens_evaluated）。</summary>
    public int PromptTokens { get; set; }
    /// <summary>本轮重算 token 数（总长 − 命中）。</summary>
    public int PromptTokensRecomputed { get; set; }
    public int CachedTokens { get; set; }
    /// <summary>本轮生成 token 数（下一轮的可复用上限 = 本轮总长 + 本轮生成）。</summary>
    public int GeneratedTokens { get; set; }
    /// <summary>可复用上限 = 上一轮总长 + 上一轮生成（首轮 0）。</summary>
    public int CarryOverTokens { get; set; }
    /// <summary>携带复用率 = 命中 / 可复用上限（R380 口径的本地等价物）。</summary>
    public double CarryOverReuse { get; set; } = -1;
    /// <summary>会话整体复用率 = 命中 / 本轮总长（直接决定 token 成本）。</summary>
    public double SessionReuseRatio { get; set; } = -1;
    /// <summary>本会话冷启首轮总长（≈ 常驻前缀厚度）。</summary>
    public int PrefixTokens { get; set; }
    /// <summary>前缀绝对长度是否达稳健界（4224 token）。</summary>
    public bool PrefixLengthSatisfied { get; set; }
    public bool RedlineApplies { get; set; }
    public bool Violated { get; set; }
    public string? Diagnosis { get; set; }
    public string? Content { get; set; }
    /// <summary>每轮都必须 = 1 ⇒ 长驻（>1 = 发生重启，前序 KV 缓存已丢）。</summary>
    public long ProcessStarts { get; set; }
}

/// <summary>R411 会话汇总（判据: ①长驻 ②跨轮复用 ③比值+绝对长度双条件不越线）。</summary>
public sealed class LlamaCppSessionResult
{
    public string Mode { get; set; } = "session";
    public string SessionId { get; set; } = "";
    public string Model { get; set; } = "";
    public string ReuseMode { get; set; } = "Session";
    public long ProcessStarts { get; set; }
    public long Turns { get; set; }
    public long Observations { get; set; }
    public long Violations { get; set; }
    public long NotApplicable { get; set; }
    /// <summary>弃权次数（命中 &gt; 可复用上限 ⇒ 口径不符，不出判决）。</summary>
    public long Abstained { get; set; }
    /// <summary>非首轮「前缀没被复用」轮次数（>0 = 长驻/前缀稳定任一不成立）。</summary>
    public long CacheMissTurns { get; set; }
    /// <summary>冷启首轮总长（≈ 稳定前缀 + 首轮输入 + 模板开销）。</summary>
    public int SystemTokens { get; set; }
    /// <summary>红线要求的前缀绝对长度（4224）。</summary>
    public int RequiredPrefixTokens { get; set; }
    public double CarryOverReuseLast { get; set; } = -1;
    public double SessionReuseRatioLast { get; set; } = -1;
    public double EffectiveHitRateLast { get; set; } = -1;
    public bool LongLived { get; set; }
    public bool CrossTurnReuse { get; set; }
    public List<LlamaCppSessionTurnResult> TurnResults { get; set; } = [];
}

/// <summary>
/// E2E CLI 的 JSON 上下文（STJ 源生成，AOT 安全）。
/// R411: <c>PropertyNameCaseInsensitive</c> —— 请求文件（<c>--session-json</c>）的键名不得对大小写敏感。
/// 只影响**读取**；输出命名不变（既有消费脚本按精确键名读，不受影响）。
/// </summary>
[JsonSourceGenerationOptions(PropertyNameCaseInsensitive = true)]
[JsonSerializable(typeof(LlamaCppE2EResult))]
[JsonSerializable(typeof(TemplateVerifyResult))]
[JsonSerializable(typeof(LlamaCppSessionRequest))]
[JsonSerializable(typeof(LlamaCppSessionTurnResult))]
[JsonSerializable(typeof(LlamaCppSessionResult))]
[JsonSerializable(typeof(float[]))]
internal sealed partial class LlamaCppE2EJsonContext : JsonSerializerContext;
