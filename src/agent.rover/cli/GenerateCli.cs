using System.Diagnostics;
using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using agent.rover.gguf;
using agent.rover.infer;
using agent.rover.token;

namespace agent.rover.cli;

/// <summary>
/// R400 · rover 生成链 CLI:
///   tokenize —— 分词器自检 / oracle 夹具逐条对账 / 单文本诊断 (可脱离 4.2 GB 模型, 走表快照);
///   generate —— chat template → 采样 → 解码环 (逐 token 时延 / 峰值 RSS / 机器可读台账)。
/// 输出沿用本仓机器可读 kv 行约定: 键{字段=值}。
/// </summary>
public static class GenerateCli
{
    public const string UsageLine =
        "  tokenize <gguf|--tables DIR> --selftest | --fixtures | --text \"...\"   分词器自检/对账/诊断\n" +
        "  generate <gguf> --prompt P [--chat [--system S]] [--max-tokens N] [--temperature T] [--top-k K] [--top-p P] [--seed S] [--ctx N] [--max-seconds S] [--out-text F] [--json F]";

    public static int Run(string[] a, TextWriter o)
        => a[0] switch
        {
            "tokenize" => Tokenize(a, o),
            "generate" => Generate(a, o),
            _ => 2,
        };

    // ── tokenize ─────────────────────────────────────────────────────────────

    private static int Tokenize(string[] a, TextWriter o)
    {
        if (a.Contains("--selftest"))
        {
            return SelfTest(o);
        }

        string? tables = Opt(a, "--tables");
        List<string> tokens;
        List<int> types;
        List<string> merges;
        string prov;
        if (tables != null)
        {
            if (!TableSnapshot.TryLoadRaw(tables, out tokens, out types, out merges, out prov, out string err))
            {
                o.WriteLine($"error{{kind=table_load message={err}}}");
                return 1;
            }
        }
        else if (a.Length >= 2 && !a[1].StartsWith("--", StringComparison.Ordinal))
        {
            using GgufReader r = GgufReader.Open(a[1]);
            LoadRawFromGguf(r, out tokens, out types, out merges, out prov);
        }
        else
        {
            o.WriteLine("usage: tokenize <gguf|--tables DIR> [--selftest | --fixtures | --text \"...\"]");
            return 2;
        }

        BpeTokenizer tk = new(tokens, types, merges);
        o.WriteLine($"tokenizer{{spec=gpt2/byte-level {prov}}}");
        if (a.Contains("--neg-control"))
        {
            return NegControl(a, o, tk, tokens, types, merges);
        }

        if (a.Contains("--fixtures"))
        {
            return Fixtures(a, o, tk);
        }

        string? text = Opt(a, "--text");
        if (text is null)
        {
            o.WriteLine("error{kind=missing_arg arg=--text|--fixtures|--selftest}");
            return 2;
        }

        List<string> pieces = tk.Pieces(text);
        List<int> ids = tk.Encode(text);
        o.WriteLine($"text{{len={text.Length} sha256={Sha256Hex(Encoding.UTF8.GetBytes(text))[..16]} pieces={pieces.Count} ids={ids.Count}}}");
        o.WriteLine($"pieces{{text={Esc(string.Join('\u0001', pieces))}}}");
        o.WriteLine($"ids{{list=[{string.Join(",", ids)}]}}");
        o.WriteLine($"roundtrip{{equal={(tk.Decode(ids) == text ? "true" : "false")} skip_specials={tk.Decode(ids, skipSpecialTokens: true) == text}}}");
        o.WriteLine($"decode{{raw={Esc(tk.Decode(ids, skipSpecialTokens: false))}}}");
        o.WriteLine("done{command=tokenize}");
        return 0;
    }

    private static int SelfTest(TextWriter o)
    {
        int pass = 0;
        int fail = 0;
        void Case(string id, bool ok, string detail)
        {
            if (ok)
            {
                pass++;
            }
            else
            {
                fail++;
            }

            o.WriteLine($"case{{id={id} verdict={(ok ? "ok" : "FAIL")} detail={detail}}}");
        }

        Case("byte_unicode_injective", ByteUnicode.SelfCheck(out string d1), d1);
        Case("pretokenizer_assets", Pretokenizer.SelfCheck(out string d2), d2);
        Case("chat_template_tags", ChatTemplate.SelfCheck(out string d3), d3);

        string sp = BpeTokenizer.DigestLines(TokenizerAssets.SplitTokens);
        Case("split_tokens_digest", sp == TokenizerAssets.SplitTokensDigest, $"recomputed={sp[..16]}");

        string sq = BpeTokenizer.DigestLines(TokenizerAssets.SpecialTokens);
        Case("special_tokens_digest", sq == TokenizerAssets.SpecialTokensDigest, $"recomputed={sq[..16]}");

        // chat 黄金样本 (jinja2 渲染, 独立引擎): 缺失时按 FormalAssertionContract「缺失≠错误」放行但不记通过
        const string golden = "eval/rover/tokref/chat_golden.jsonl";
        if (File.Exists(golden))
        {
            int n = 0;
            int ok = 0;
            foreach (string line in File.ReadLines(golden))
            {
                if (line.Trim().Length == 0)
                {
                    continue;
                }

                using JsonDocument d = JsonDocument.Parse(line);
                JsonElement root = d.RootElement;
                List<ChatMessage> msgs = [];
                foreach (JsonElement m in root.GetProperty("messages").EnumerateArray())
                {
                    msgs.Add(new ChatMessage(m.GetProperty("role").GetString()!, m.GetProperty("content").GetString()!));
                }

                string want = root.GetProperty("rendered").GetString()!;
                string got = ChatTemplate.Render(msgs, root.GetProperty("add_generation_prompt").GetBoolean());
                n++;
                if (got == want)
                {
                    ok++;
                }
                else
                {
                    o.WriteLine($"chat_mismatch{{name={root.GetProperty("name").GetString()} want_sha={Sha256Hex(Encoding.UTF8.GetBytes(want))[..16]} got_sha={Sha256Hex(Encoding.UTF8.GetBytes(got))[..16]}}}");
                }
            }

            Case("chat_golden", ok == n && n == ChatTemplate.GoldenCount, $"cases={n} pass={ok} (jinja2 oracle)");
        }
        else
        {
            o.WriteLine($"case{{id=chat_golden verdict=absent detail={golden} 不存在 (缺失≠错误, 不记通过)}}");
        }

        o.WriteLine($"selftest{{ran={pass + fail} pass={pass} fail={fail} tokens=0}}");
        return fail == 0 ? 0 : 1;
    }

    private static int Fixtures(string[] a, TextWriter o, BpeTokenizer tk)
    {
        string ff = Opt(a, "--fixtures-file") ?? "eval/rover/tokref/fixtures.jsonl";
        string pf = Opt(a, "--pretok-file") ?? "eval/rover/tokref/pretok_fixtures.jsonl";
        int fails = 0;

        int n = 0;
        int ok = 0;
        int bad = 0;
        foreach (string line in File.ReadLines(ff))
        {
            if (line.Trim().Length == 0)
            {
                continue;
            }

            using JsonDocument d = JsonDocument.Parse(line);
            string text = d.RootElement.GetProperty("text").GetString()!;
            int[] want = [.. d.RootElement.GetProperty("ids").EnumerateArray().Select(x => x.GetInt32())];
            List<int> got = tk.Encode(text);
            n++;
            if (got.Count == want.Length && got.SequenceEqual(want))
            {
                ok++;
                continue;
            }

            bad++;
            o.WriteLine($"mismatch{{kind=encode i={d.RootElement.GetProperty("i").GetInt32()} text_sha256={Sha256Hex(Encoding.UTF8.GetBytes(text))[..16]} want_len={want.Length} got_len={got.Count} first_diff={FirstDiff(want, got)}}}");
        }

        o.WriteLine($"fixtures_encode{{file={Path.GetFileName(ff)} cases={n} pass={ok} fail={bad}}}");
        fails += bad;

        n = 0;
        ok = 0;
        bad = 0;
        foreach (string line in File.ReadLines(pf))
        {
            if (line.Trim().Length == 0)
            {
                continue;
            }

            using JsonDocument d = JsonDocument.Parse(line);
            string text = d.RootElement.GetProperty("text").GetString()!;
            string[] want = [.. d.RootElement.GetProperty("pieces").EnumerateArray().Select(x => x.GetString()!)];
            List<string> got = tk.Pieces(text);
            n++;
            if (got.Count == want.Length && got.SequenceEqual(want, StringComparer.Ordinal))
            {
                ok++;
                continue;
            }

            bad++;
            o.WriteLine($"mismatch{{kind=pretok i={d.RootElement.GetProperty("i").GetInt32()} want_n={want.Length} got_n={got.Count} text_sha256={Sha256Hex(Encoding.UTF8.GetBytes(text))[..16]}}}");
        }

        o.WriteLine($"fixtures_pretok{{file={Path.GetFileName(pf)} cases={n} pass={ok} fail={bad}}}");
        fails += bad;

        // 压力批: 2000 条确定性随机对抗文本, encode + pretok 双断言
        string sf = Opt(a, "--stress-file") ?? "eval/rover/tokref/stress_fixtures.jsonl";
        n = 0;
        ok = 0;
        bad = 0;
        foreach (string line in File.ReadLines(sf))
        {
            if (line.Trim().Length == 0)
            {
                continue;
            }

            using JsonDocument d = JsonDocument.Parse(line);
            string text = d.RootElement.GetProperty("text").GetString()!;
            int[] want = [.. d.RootElement.GetProperty("ids").EnumerateArray().Select(x => x.GetInt32())];
            List<int> got = tk.Encode(text);
            n++;
            if (got.Count == want.Length && got.SequenceEqual(want))
            {
                ok++;
                continue;
            }

            bad++;
            if (bad <= 5)
            {
                o.WriteLine($"mismatch{{kind=stress_encode i={d.RootElement.GetProperty("i").GetInt32()} text_sha256={Sha256Hex(Encoding.UTF8.GetBytes(text))[..16]} first_diff={FirstDiff(want, got)}}}");
            }
        }

        o.WriteLine($"fixtures_stress_encode{{file={Path.GetFileName(sf)} cases={n} pass={ok} fail={bad}}}");
        fails += bad;

        string df = Opt(a, "--decode-file") ?? "eval/rover/tokref/decode_fixtures.jsonl";
        n = 0;
        ok = 0;
        bad = 0;
        foreach (string line in File.ReadLines(df))
        {
            if (line.Trim().Length == 0)
            {
                continue;
            }

            using JsonDocument d = JsonDocument.Parse(line);
            List<int> ids = [.. d.RootElement.GetProperty("ids").EnumerateArray().Select(x => x.GetInt32())];
            string wantText = d.RootElement.GetProperty("text").GetString()!;
            string wantRaw = d.RootElement.GetProperty("text_raw").GetString()!;
            n++;
            if (tk.Decode(ids) == wantText && tk.Decode(ids, skipSpecialTokens: false) == wantRaw)
            {
                ok++;
                continue;
            }

            bad++;
            if (bad <= 5)
            {
                o.WriteLine($"mismatch{{kind=decode i={d.RootElement.GetProperty("i").GetInt32()} len={ids.Count} skip_eq={(tk.Decode(ids) == wantText)} raw_eq={(tk.Decode(ids, skipSpecialTokens: false) == wantRaw)}}}");
            }
        }

        o.WriteLine($"fixtures_decode{{file={Path.GetFileName(df)} cases={n} pass={ok} fail={bad}}}");
        fails += bad;

        o.WriteLine($"done{{command=tokenize.fixtures pass={(fails == 0 ? "true" : "false")}}}");
        return fails == 0 ? 0 : 1;
    }

    // ── generate ─────────────────────────────────────────────────────────────

    private static int Generate(string[] a, TextWriter o)
    {
        if (a.Length < 2) { o.WriteLine("error{kind=missing_arg arg=gguf}"); return 2; }
        string path = a[1];
        string prompt = Opt(a, "--prompt") ?? string.Empty;
        string? system = Opt(a, "--system");
        bool chat = a.Contains("--chat");
        int maxTokens = int.Parse(Opt(a, "--max-tokens") ?? "16", CultureInfo.InvariantCulture);
        float temperature = float.Parse(Opt(a, "--temperature") ?? "0.7", CultureInfo.InvariantCulture);
        int topK = int.Parse(Opt(a, "--top-k") ?? "40", CultureInfo.InvariantCulture);
        float topP = float.Parse(Opt(a, "--top-p") ?? "0.95", CultureInfo.InvariantCulture);
        ulong seed = ulong.Parse(Opt(a, "--seed") ?? "12345", CultureInfo.InvariantCulture);
        double maxSeconds = double.Parse(Opt(a, "--max-seconds") ?? "0", CultureInfo.InvariantCulture);
        int budgetMb = int.Parse(Opt(a, "--budget-mb") ?? "96", CultureInfo.InvariantCulture);
        bool dropPages = a.Contains("--drop-pages");
        int? ctxOpt = Opt(a, "--ctx") is { } cs ? int.Parse(cs, CultureInfo.InvariantCulture) : null;

        long ws0 = Mem();
        using GgufReader r = GgufReader.Open(path);
        LoadRawFromGguf(r, out List<string> rawTokens, out List<int> rawTypes, out List<string> rawMerges, out string tokProv);
        BpeTokenizer tk = new(rawTokens, rawTypes, rawMerges);
        ModelConfig cfg = ModelConfig.From(r);
        long eos = r.TryGetLong("tokenizer.ggml.eos_token_id", out long e) ? e : -1;
        int bos = r.TryGetLong("tokenizer.ggml.bos_token_id", out long b) ? (int)b : -1;

        string promptText = chat
            ? ChatTemplate.Render(BuildMessages(system, prompt), addGenerationPrompt: true)
            : prompt;
        List<int> ids = tk.Encode(promptText);
        if (ids.Count == 0)
        {
            o.WriteLine("error{kind=empty_prompt}");
            return 2;
        }

        int maxPos = ctxOpt ?? Math.Max(ids.Count + maxTokens + 4, 64);
        if (maxPos < ids.Count + maxTokens)
        {
            maxPos = ids.Count + maxTokens;
        }

        o.WriteLine($"generate{{file={Path.GetFileName(path)} file_bytes={r.Mapped.Length} chat={(chat ? "true" : "false")} " +
                    $"prompt_tokens={ids.Count} max_tokens={maxTokens} temperature={temperature} top_k={topK} top_p={topP} seed={seed} " +
                    $"eos={eos} bos={bos} ctx={maxPos}}}");
        o.WriteLine($"tokenizer{{{tokProv}}}");
        o.WriteLine($"prompt{{sha256={Sha256Hex(Encoding.UTF8.GetBytes(promptText))} len={promptText.Length} text={Esc(promptText)}}}");
        o.WriteLine($"cfg{{arch={cfg.Arch} layers={cfg.NLayer} hidden={cfg.Hidden} vocab={tk.VocabSize}}}");

        using ForwardPass fp = new(r, cfg, maxPos, (long)budgetMb * 1048576, dropPages);
        Sampler sampler = new(new SamplerOptions(temperature, topK, topP, seed));

        Stopwatch total = Stopwatch.StartNew();
        Stopwatch sw = Stopwatch.StartNew();
        float[] logits = fp.Forward(ids, null, null);
        double prefillMs = sw.Elapsed.TotalMilliseconds;
        long peak = Mem();
        o.WriteLine($"prefill{{tokens={ids.Count} ms={prefillMs:F1} rss_kb={peak / 1024}}}");

        List<int> outp = [];
        List<double> stepMs = [];
        string stop = "max_tokens";
        for (int step = 0; step < maxTokens; step++)
        {
            int next = sampler.Next(logits);
            outp.Add(next);
            string tokenText = next >= 0 && next < tk.VocabSize ? tk.TokenString(next) : "<oob>";
            long rss = Mem();
            peak = Math.Max(peak, rss);
            if (next == eos)
            {
                o.WriteLine($"step{{index={step} id={next} token={Esc(tokenText)} stop=eos rss_kb={rss / 1024}}}");
                stop = "eos";
                break;
            }

            if (maxSeconds > 0 && total.Elapsed.TotalSeconds >= maxSeconds)
            {
                o.WriteLine($"step{{index={step} id={next} token={Esc(tokenText)} stop=seconds rss_kb={rss / 1024}}}");
                stop = "seconds";
                break;
            }

            sw.Restart();
            logits = fp.Forward([next], null, null);
            double ms = sw.Elapsed.TotalMilliseconds;
            stepMs.Add(ms);
            o.WriteLine($"step{{index={step} id={next} token={Esc(tokenText)} ms={ms:F1} rss_kb={rss / 1024} " +
                        $"streamed_bytes={fp.Stats.StreamedBytes} evicts={fp.Ledger.EvictCount}}}");
        }

        total.Stop();
        string text = tk.Decode(outp);
        string textRaw = tk.Decode(outp, skipSpecialTokens: false);
        double perTok = stepMs.Count > 0 ? stepMs.Sum() / stepMs.Count : 0;
        double tps = stepMs.Sum() > 0 ? stepMs.Count / (stepMs.Sum() / 1000.0) : 0;
        o.WriteLine($"gen_done{{steps={outp.Count} decoded={stepMs.Count} stop={stop} ms={total.Elapsed.TotalMilliseconds:F1} " +
                    $"ms_per_token={perTok:F1} tokens_per_s={tps:F4} peak_rss_kb={peak / 1024} ws_delta_kb={(peak - ws0) / 1024} " +
                    $"draws={sampler.Draws} streamed_bytes={fp.Stats.StreamedBytes} evicts={fp.Ledger.EvictCount}}}");
        o.WriteLine($"gen_text{{text={Esc(text)}}}");
        o.WriteLine($"gen_text_raw{{text={Esc(textRaw)}}}");

        string? outText = Opt(a, "--out-text");
        if (outText != null)
        {
            File.WriteAllText(outText, text, new UTF8Encoding(false));
            o.WriteLine($"out{{file={outText} bytes={(new FileInfo(outText)).Length}}}");
        }

        string? json = Opt(a, "--json");
        if (json != null)
        {
            WriteJson(json, path, r.Mapped.Length, promptText, ids, outp, stepMs, stop, total.Elapsed.TotalMilliseconds,
                perTok, tps, peak - ws0, prefillMs, sampler, tk, temperature, topK, topP, seed, eos);
            o.WriteLine($"out{{file={json} bytes={(new FileInfo(json)).Length}}}");
        }

        o.WriteLine("done{command=generate}");
        return 0;
    }

    private static List<ChatMessage> BuildMessages(string? system, string prompt)
    {
        List<ChatMessage> msgs = [];
        if (!string.IsNullOrEmpty(system))
        {
            msgs.Add(new ChatMessage("system", system));
        }

        msgs.Add(new ChatMessage("user", prompt));
        return msgs;
    }

    private static void WriteJson(string path, string gguf, long fileBytes, string promptText, List<int> promptIds,
        List<int> outp, List<double> stepMs, string stop, double totalMs, double perTok, double tps, long wsDelta,
        double prefillMs, Sampler sampler, BpeTokenizer tk, float temperature, int topK, float topP, ulong seed, long eos)
    {
        using FileStream fs = File.Create(path);
        using Utf8JsonWriter w = new(fs, new JsonWriterOptions { Indented = true });
        w.WriteStartObject();
        w.WriteString("schema", "rover-generate/1");
        w.WriteString("gguf", gguf);
        w.WriteNumber("gguf_bytes", fileBytes);
        w.WriteString("prompt_sha256", Sha256Hex(Encoding.UTF8.GetBytes(promptText)));
        w.WriteNumber("prompt_tokens", promptIds.Count);
        w.WriteStartArray("prompt_ids");
        foreach (int id in promptIds)
        {
            w.WriteNumberValue(id);
        }

        w.WriteEndArray();
        w.WriteNumber("temperature", temperature);
        w.WriteNumber("top_k", topK);
        w.WriteNumber("top_p", topP);
        w.WriteNumber("seed", seed);
        w.WriteNumber("eos", eos);
        w.WriteString("stop", stop);
        w.WriteNumber("steps", outp.Count);
        w.WriteNumber("ms_total", totalMs);
        w.WriteNumber("ms_prefill", prefillMs);
        w.WriteNumber("ms_per_token", perTok);
        w.WriteNumber("tokens_per_s", tps);
        w.WriteNumber("ws_delta_bytes", wsDelta);
        w.WriteNumber("rng_draws", sampler.Draws);
        w.WriteString("tokens_sha256", tk.TokensSha256);
        w.WriteString("merges_sha256", tk.MergesSha256);
        w.WriteStartArray("step_ms");
        foreach (double ms in stepMs)
        {
            w.WriteNumberValue(ms);
        }

        w.WriteEndArray();
        w.WriteStartArray("ids");
        foreach (int id in outp)
        {
            w.WriteNumberValue(id);
        }

        w.WriteEndArray();
        w.WriteString("text", tk.Decode(outp));
        w.WriteString("text_raw", tk.Decode(outp, skipSpecialTokens: false));
        w.WriteEndObject();
    }

    private static void LoadRawFromGguf(GgufReader r, out List<string> tokens, out List<int> types, out List<string> merges, out string prov)
    {
        tokens = r.GetStringArray("tokenizer.ggml.tokens");
        merges = r.GetStringArray("tokenizer.ggml.merges");
        types = new(tokens.Count);
        if (r.Kv.TryGetValue("tokenizer.ggml.token_type", out GgufValue tv) && tv.A?.Items is { } items)
        {
            foreach (GgufValue v in items)
            {
                types.Add((int)v.I);
            }
        }

        if (types.Count != tokens.Count)
        {
            throw new InvalidOperationException($"token_type 长度 {types.Count} != tokens {tokens.Count}");
        }

        prov = $"gguf tokens={tokens.Count} merges={merges.Count} " +
               $"tokens_sha256={BpeTokenizer.DigestLines(tokens)[..16]} merges_sha256={BpeTokenizer.DigestLines(merges)[..16]}";
    }

    /// <summary>
    /// 负控读数: 用变体分词器 (乱序/逆序/空 merges、朴素整片预分词) 跑同一批夹具,
    /// 量化「夹具集对被测组件的判别力」—— 没有这组读数的通过率是空心指标 (R399 铁律)。
    /// </summary>
    private static int NegControl(string[] a, TextWriter o, BpeTokenizer tk, List<string> tokens, List<int> types, List<string> merges)
    {
        string file = Opt(a, "--stress-file") ?? "eval/rover/tokref/stress_fixtures.jsonl";
        List<(string Text, List<int> Ids, int Pieces)> dep = [];
        foreach (string line in File.ReadLines(file))
        {
            if (line.Trim().Length == 0)
            {
                continue;
            }

            using JsonDocument d = JsonDocument.Parse(line);
            string text = d.RootElement.GetProperty("text").GetString()!;
            List<int> ids = tk.Encode(text);
            if (ids.Count > tk.Pieces(text).Count)
            {
                dep.Add((text, ids, 0));
            }
        }

        List<string> shuffled = [.. merges.OrderBy(m => Sha256Hex(Encoding.UTF8.GetBytes(m))[..16], StringComparer.Ordinal)];
        List<string> reversed = [.. Enumerable.Reverse(merges)];
        (string Name, List<string> Merges)[] variants =
        [
            ("shuffled", shuffled),
            ("reversed", reversed),
            ("empty", []),
        ];
        foreach ((string name, List<string> mv) in variants)
        {
            BpeTokenizer v = new(tokens, types, mv);
            int caught = dep.Count(x => !v.Encode(x.Text).SequenceEqual(x.Ids));
            o.WriteLine($"neg_control{{kind=merges:{name} dependent={dep.Count} caught={caught} rate={(dep.Count == 0 ? 1.0 : (double)caught / dep.Count):P1}}}");
        }

        // 朴素整片预分词 (不做任何切分) 在 pretok 夹具上的通过率
        int naivePass = 0;
        int total = 0;
        foreach (string line in File.ReadLines("eval/rover/tokref/pretok_fixtures.jsonl"))
        {
            if (line.Trim().Length == 0)
            {
                continue;
            }

            using JsonDocument d = JsonDocument.Parse(line);
            string text = d.RootElement.GetProperty("text").GetString()!;
            string[] want = [.. d.RootElement.GetProperty("pieces").EnumerateArray().Select(x => x.GetString()!)];
            total++;
            if (new[] { ByteUnicode.Encode(text) }.SequenceEqual(want, StringComparer.Ordinal))
            {
                naivePass++;
            }
        }

        o.WriteLine($"neg_control{{kind=naive_pretok naive_pass={naivePass} total={total} discriminated={total - naivePass}}}");

        // 空切分集: 含特殊符号的文本必须被打散
        BpeTokenizer noSplit = new(tokens, types, merges, splitTokens: []);
        const string spText = "a<｜end▁of▁sentence｜>b";
        o.WriteLine($"neg_control{{kind=no_split_tokens baseline_ids={tk.Encode(spText).Count} variant_ids={noSplit.Encode(spText).Count} changed={!noSplit.Encode(spText).SequenceEqual(tk.Encode(spText))}}}");
        o.WriteLine("done{command=tokenize.neg_control}");
        return 0;
    }

    // ── helpers ──────────────────────────────────────────────────────────────

    private static string? Opt(string[] a, string name)
    {
        for (int i = 0; i < a.Length - 1; i++)
        {
            if (a[i] == name)
            {
                return a[i + 1];
            }
        }

        return null;
    }

    private static long Mem()
    {
        using Process p = Process.GetCurrentProcess();
        p.Refresh();
        return p.WorkingSet64;
    }

    private static string FirstDiff(int[] want, List<int> got)
    {
        int n = Math.Min(want.Length, got.Count);
        for (int i = 0; i < n; i++)
        {
            if (want[i] != got[i])
            {
                return $"@{i} want={want[i]} got={got[i]}";
            }
        }

        return $"@{n} (长度差)";
    }

    private static string Sha256Hex(byte[] data) => Convert.ToHexStringLower(SHA256.HashData(data));

    private static string Esc(string s)
    {
        StringBuilder sb = new(s.Length + 8);
        foreach (char c in s)
        {
            switch (c)
            {
                case '\\': sb.Append("\\\\"); break;
                case '"': sb.Append("\\\""); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                default:
                    if (char.IsControl(c))
                    {
                        sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                    }
                    else
                    {
                        sb.Append(c);
                    }

                    break;
            }
        }

        return sb.ToString();
    }
}
