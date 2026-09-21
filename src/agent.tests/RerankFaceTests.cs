using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using agent.rag;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace agent.tests;

/// <summary>
/// R623（用户钦定 KPI 2026-09-19 落地 + DoD 面 4 首测）：在**产品真身** <see cref="RAGRecall"/> 路径上
/// 测上下文精排段（漏斗第二级：召回 → 粗排 → **精排** → 装配）的四件套
/// （NDCG@k / MRR / Precision@k / Recall@N）+ **生效遥测**（RerankApplied / LastRerankSwaps）。
///
/// 纪律（预注册见 eval/rover/r623/prereg-r623.json + 增补件 prereg-r623-v2addendum.json）：
///   ① **代码事实**：精排段在 `Take(TopK)` **之后**执行 ⇒ 池尺寸即精排的可重排空间 ⇒ 测量必须给足池；
///   ② **前置天花板**：精排只重排不补召回 ⇒ 读数只在 Recall@N == 1（gold 在池内）的查询上聚合；
///   ③ **轴关 = 旧行为**：RerankEnabled=false 时 RerankApplied 必须恒 0（对照臂）；
///   ④ **两侧控制**（判据器判别力自证）：退化打分器不得优于粗排；oracle 置顶打分器必须近满分；
///   ⑤ **零新增夹具**：语料/查询 = 既有冻结件 eval/bge/fixtures；
///   ⑥ 本面**零远端调用 / 零 LLM** ⇒ tokens 与命中率**未测**，不得补记；
///   ⑦ **先落盘后断言**（失败判据也必须留证据；器具不得吞掉读数）。
///
/// 环境变量（测量形态，非阈值）：
///   AGENTFRAMEWORK_R623_SHAPE = fusion（缺省，= 生产 DI 形状）/ legacy（旧 hybrid 路，诊断列）
///   AGENTFRAMEWORK_R623_TOPK  = 召回池尺寸（缺省 50；精排在 Take(TopK) 之后 ⇒ 池 = 可重排空间）
/// fixture 缺失时显式落盘 skipped 并 return，绝不静默通过。
/// </summary>
public class RerankFaceTests
{
    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        if (dir == null) throw new DirectoryNotFoundException("找不到仓库根 (agent.sln)");
        return dir.FullName;
    }

    private static readonly string Repo = FindRepoRoot();

    private static readonly string Shape =
        (Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R623_SHAPE") ?? "fusion").Trim().ToLowerInvariant();

    private static readonly int PoolK =
        int.TryParse(Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R623_TOPK"), out var k) && k > 0 ? k : 50;

    // ── R624（面 4 达标路径 · 召回面）：**召回 dense 路的向量源**形态轴 ──────────────────────
    //   hash（缺省，= R623 现档：EmbeddingFunction=null ⇒ RAGRecall 走词袋哈希兜底）/
    //   vec （生产形态：bge-q8.gguf 语义向量 ∧ 输入截断 440ch，= ServiceCollectionExtensions.cs:233-235 的 EmbeddingFunction）/
    //   zero（负控：常量零向量 ⇒ 判据必须对向量源有牙）。
    //   缺省 = hash ⇒ 全量套件与 R623 读数**逐位零回归**（形态轴未生效时行为一字不变）。
    private static readonly string EmbedMode =
        (Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R623_EMBED") ?? "hash").Trim().ToLowerInvariant();

    private const int MaxEmbedChars = 440;   // = RAGRecall.GenerateEmbedding 的 maxEmbedChars（调用 EmbeddingFunction 前的截断窗）

    /// <summary>读 .f32 向量件（头 = u64 n + u64 d，小端 float32）—— 与 eval/bge 冻结 cache 同格式。</summary>
    private static (int N, int D, float[] Data) ReadF32(string path)
    {
        using var fs = File.OpenRead(path);
        using var br = new BinaryReader(fs);
        var n = (int)br.ReadUInt64();
        var d = (int)br.ReadUInt64();
        var data = new float[n * d];
        for (var i = 0; i < data.Length; i++) data[i] = br.ReadSingle();
        return (n, d, data);
    }

    /// <summary>向量源形态轴：按**截断后的文本**（= EmbeddingFunction 实收输入）建查表。</summary>
    private sealed class VecStore
    {
        private readonly Dictionary<string, float[]> _map = new(StringComparer.Ordinal);
        public int Hits;
        public int Miss;
        public int Dim;
        public string CorpusPath = "";
        public string QueriesPath = "";
        public string CorpusSha12 = "";
        public string QueriesSha12 = "";
        public int CorpusN;
        public int QueriesN;
        public string VecDir = "";
        public int MissLong;                  // 收到的文本 > 440（未截断）⇒ 生产形态未按 440 截断（诊断字段）
        public int MissShort;                 // 收到的文本 ≤ 440 却查不到（= 真漏挂）
        public int ChunksN;
        public string ChunksSha12 = "";
        public int MissDumpN;
        public int ExtraN;
        public string ExtraSha12 = "";
        private readonly HashSet<string> _dumped = new(StringComparer.Ordinal);
        public static readonly string MissDumpPath =
            Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R624_MISSDUMP") ?? "";
        private readonly List<string> _missSamples = new();

        public float[] Embed(string text)
        {
            if (_map.TryGetValue(text, out var v)) { Hits++; return v; }
            Miss++;                       // 未命中 = 可见失败（返回零向量则必然低分，不会静默当成好结果）
            // 实发文本落盘（默认关）：键集以**产品实收文本**为真值锚，而非源码重建（skill R450 教训）
            if (MissDumpPath.Length > 0 && _dumped.Add(text))
            {
                File.AppendAllText(MissDumpPath, JsonSerializer.Serialize(text) + "\n");
                MissDumpN++;
            }
            if (text.Length > MaxEmbedChars) MissLong++;
            else
            {
                MissShort++;
                if (_missSamples.Count < 40) _missSamples.Add(text.Length + ":" + text[..Math.Min(40, text.Length)]);
            }
            return new float[Dim > 0 ? Dim : 512];
        }

        public static VecStore Load(string dir, string corpusPath, string queriesPath, List<(string Id, string Text)> corpus, List<string> queries)
        {
            var s = new VecStore();
            s.VecDir = dir;
            s.CorpusPath = Path.Combine(dir, "corpus-trunc440.f32");
            s.QueriesPath = Path.Combine(dir, "queries-trunc440.f32");
            var (cn, cd, cdata) = ReadF32(s.CorpusPath);
            var (qn, qd, qdata) = ReadF32(s.QueriesPath);
            if (cd != qd) throw new InvalidOperationException($"向量维度不一致 corpus={cd} queries={qd}");
            if (cn != corpus.Count || qn != queries.Count)
                throw new InvalidOperationException($"向量条数不符 corpus {cn}/{corpus.Count} queries {qn}/{queries.Count}");
            s.Dim = cd; s.CorpusN = cn; s.QueriesN = qn;
            s.CorpusSha12 = Sha12(s.CorpusPath); s.QueriesSha12 = Sha12(s.QueriesPath);
            for (var i = 0; i < cn; i++)
            {
                var t = corpus[i].Text.Length > MaxEmbedChars ? corpus[i].Text[..MaxEmbedChars] : corpus[i].Text;
                s._map[t] = cdata[(i * cd)..((i + 1) * cd)];
            }
            for (var i = 0; i < qn; i++)
            {
                var t = queries[i].Length > MaxEmbedChars ? queries[i][..MaxEmbedChars] : queries[i];
                s._map[t] = qdata[(i * qd)..((i + 1) * qd)];
            }

            // ── 追加键件（生产形态补块 / 实发文本补挂）──
            // 补块：RAGRecall 对 >440ch 文档切 chunk（每块独立向量，Id=base#cN）
            //   代码证据 src/agent.rag/RAGRecall.cs:203-228（chunkSize=440, chunkIdx>=1 独立 GenerateEmbedding）。
            // 补挂：键集以**产品实收文本**落盘件为真值锚（skill R450：源码重建会静默漂移）。
            void AddKeys(string f32name, string keysname, bool isChunks)
            {
                var fp = Path.Combine(dir, f32name);
                var kp = Path.Combine(dir, keysname);
                if (!File.Exists(fp) || !File.Exists(kp)) return;
                var (en, ed, edata) = ReadF32(fp);
                if (ed != cd) throw new InvalidOperationException($"追加键件维度不一致 {ed} vs {cd}");
                var keys = File.ReadAllText(kp)
                    .Split('\n', StringSplitOptions.RemoveEmptyEntries)
                    .Select(l => JsonSerializer.Deserialize<string>(l)!).ToList();
                if (keys.Count != en) throw new InvalidOperationException($"追加键件键数不符 {keys.Count}/{en}");
                for (var i = 0; i < en; i++) s._map[keys[i]] = edata[(i * ed)..((i + 1) * ed)];
                if (isChunks) { s.ChunksN = en; s.ChunksSha12 = Sha12(fp); }
                else { s.ExtraN = en; s.ExtraSha12 = Sha12(fp); }
            }
            AddKeys("chunks.f32", "keys-chunks.jsonl", true);
            AddKeys("extra.f32", "keys-extra.jsonl", false);
            return s;
        }

        public Dictionary<string, object?> Describe() => new()
        {
            ["vec_dir"] = VecDir.StartsWith(Repo, StringComparison.Ordinal)
                            ? VecDir[(Repo.Length + 1)..].Replace('\\', '/') : VecDir,
            ["corpus_sha12"] = CorpusSha12, ["corpus_n"] = CorpusN,
            ["queries_sha12"] = QueriesSha12, ["queries_n"] = QueriesN,
            ["dim"] = Dim, ["hits"] = Hits, ["miss"] = Miss,
            ["miss_long"] = MissLong, ["miss_short"] = MissShort,
            ["chunks_n"] = ChunksN, ["chunks_sha12"] = ChunksSha12,
            ["extra_n"] = ExtraN, ["extra_sha12"] = ExtraSha12,
            ["miss_dump_n"] = MissDumpN,
            ["miss_samples"] = _missSamples,
            ["max_embed_chars"] = MaxEmbedChars,
        };
    }

    private static string OutPath()
    {
        var overridePath = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R623_OUT");
        if (!string.IsNullOrWhiteSpace(overridePath)) return overridePath!;
        var name = "rerank-face-readings-" + Shape + "-k" + PoolK + ".json";
        return Path.Combine(Repo, "eval", "rover", "r623", name);
    }

    private sealed class PoolScorer : IRerankScorer
    {
        private readonly Func<string, string, double, double> _f;
        public PoolScorer(Func<string, string, double, double> f) => _f = f;
        public double Score(string query, string document, double coarseScore) => _f(query, document, coarseScore);
    }

    private static double Median(List<double> xs)
    {
        if (xs.Count == 0) return double.NaN;
        var s = new List<double>(xs);
        s.Sort();
        var n = s.Count;
        return n % 2 == 1 ? s[n / 2] : (s[n / 2 - 1] + s[n / 2]) / 2.0;
    }

    /// <summary>R625 成本列：分位数（最近秩法）。仅用于信息字段，不作红绿判据（R410）。</summary>
    private static double Pct(List<double> xs, double p)
    {
        if (xs.Count == 0) return double.NaN;
        var s = new List<double>(xs);
        s.Sort();
        var idx = (int)Math.Min(s.Count - 1, Math.Max(0, Math.Round(p * (s.Count - 1))));
        return s[idx];
    }

    [Fact]
    public void FrozenFixture_RerankFourMetrics_OnProductPath()
    {
        var outPath = OutPath();
        var corpusPath = Path.Combine(Repo, "eval", "bge", "fixtures", "corpus.jsonl");
        var queriesPath = Path.Combine(Repo, "eval", "bge", "fixtures", "queries.jsonl");
        Directory.CreateDirectory(Path.GetDirectoryName(outPath)!);

        if (!File.Exists(corpusPath) || !File.Exists(queriesPath))
        {
            File.WriteAllText(outPath, "{\"skipped\":\"fixture missing\"}");
            return;
        }

        // ── 冻结件读取（既有件，零新增语义）────────────────────────────────
        var corpus = new List<(string Id, string Text)>();
        foreach (var line in File.ReadLines(corpusPath))
            if (!string.IsNullOrWhiteSpace(line))
                using (var d = JsonDocument.Parse(line))
                    corpus.Add((d.RootElement.GetProperty("id").GetString()!,
                                d.RootElement.GetProperty("text").GetString()!));

        var qids = new List<string>();
        var qtexts = new List<string>();
        var golds = new List<string>();
        foreach (var line in File.ReadLines(queriesPath))
            if (!string.IsNullOrWhiteSpace(line))
                using (var d = JsonDocument.Parse(line))
                {
                    qids.Add(d.RootElement.GetProperty("qid").GetString()!);
                    qtexts.Add(d.RootElement.GetProperty("query").GetString()!);
                    golds.Add(d.RootElement.GetProperty("gold_id").GetString()!);
                }

        Assert.Equal(1299, corpus.Count);
        Assert.Equal(120, qtexts.Count);
        var goldText = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var (id, text) in corpus) goldText[id] = text;

        // ── 召回向量源形态轴（R624）：hash（= R623 现档）/ vec（生产形态）/ zero（负控）──
        VecStore? vecStore = null;
        Func<string, float[]>? embedFn = null;
        switch (EmbedMode)
        {
            case "vec":
                vecStore = VecStore.Load(
                    Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R623_VEC_DIR")
                    ?? Path.Combine(Repo, "eval", "rover", "r624", "vec"),
                    corpusPath, queriesPath, corpus, qtexts);
                embedFn = vecStore.Embed;
                break;
            case "zero":
                embedFn = _ => new float[512];
                break;
            default:
                embedFn = null;                 // hash = 缺省 = 逐位零回归
                break;
        }

        // ── 两臂（唯一变量 = RerankEnabled）；落盘路径各自独立 ⇒ 零串染 ──
        // 形态 = 生产 DI（ServiceCollectionExtensions.cs:240：Fusion{Enabled,K0=10,w=1:1}）或 legacy 旧 hybrid 路。
        // R624：召回向量源由 EmbedMode 轴决定（hash 缺省 = R623 现档；vec = 生产 DI 的 EmbeddingFunction 形态）。
        string TempPath(string tag) => Path.Combine(Path.GetTempPath(), $"r623-{tag}-{Guid.NewGuid():N}.jsonl");

        RAGConfig NewCfg(bool rerank)
        {
            var cfg = new RAGConfig
            {
                RerankEnabled = rerank,
                PersistPathOverride = TempPath(rerank ? "T" : "C"),
                EmbeddingFunction = embedFn,
            };
            if (Shape == "fusion")
                cfg.Fusion = new FusionOptions { Enabled = true, K0 = 10, DenseWeight = 1.0, LexicalWeight = 1.0 };
            return cfg;
        }

        var recallT = new RAGRecall(NullLogger<RAGRecall>.Instance, NewCfg(true));
        var recallC = new RAGRecall(NullLogger<RAGRecall>.Instance, NewCfg(false));

        var docs = corpus.Select(c => new RAGDocument { Id = c.Id, Content = c.Text }).ToList();
        recallT.IndexBatchAsync(docs).GetAwaiter().GetResult();
        recallC.IndexBatchAsync(corpus.Select(c => new RAGDocument { Id = c.Id, Content = c.Text }))
               .GetAwaiter().GetResult();

        // ── 同池重排打分器（两侧控制）────────────────────────────────────
        var negScorer = new PoolScorer((_, _, coarse) => -coarse);      // 退化：反向（不得优于粗排）

        const int K = 10;
        var rows = new List<Dictionary<string, object?>>();
        var gated = 0;
        var swapsPositive = 0;
        var swapsTotal = 0;
        var poolIdentical = 0;
        var poolMismatch = new List<string>();
        var poolLens = new List<double>();
        var latencyUsC = new List<double>();          // R625 成本列：纯召回（C 档）逐查询耗时
        var latencyUsT = new List<double>();          // R625 成本列：召回 + 精排（T 档）逐查询耗时
        var latencyUsPairDiff = new List<double>();   // R625 成本列：配对差 = 精排段成本（T − C）
        var consumedCharsC = new List<double>();      // R625 成本列：装配面候选集合字符数（C 档）
        var consumedCharsT = new List<double>();      // R625 成本列：装配面候选集合字符数（T 档）


        foreach (var qi in Enumerable.Range(0, qtexts.Count))
        {
            var q = qtexts[qi];
            var gold = golds[qi];

                // 组装后的**精排段成本列**（R410：墙钟只作信息字段，不作红绿判据）
                var stopwatch = System.Diagnostics.Stopwatch.StartNew();
                var resC = recallC.RecallAsync(new RecallRequest { Query = q, TopK = PoolK }).GetAwaiter().GetResult();
                stopwatch.Stop();
                var cUsQuery = stopwatch.Elapsed.TotalMilliseconds * 1000.0;
                stopwatch.Restart();
                var resT = recallT.RecallAsync(new RecallRequest { Query = q, TopK = PoolK }).GetAwaiter().GetResult();
                stopwatch.Stop();
                var tUsQuery = stopwatch.Elapsed.TotalMilliseconds * 1000.0;
                latencyUsC.Add(cUsQuery); latencyUsT.Add(tUsQuery); latencyUsPairDiff.Add(tUsQuery - cUsQuery);
                consumedCharsC.Add(resC.Sum(r => (double)(r.Document?.Content ?? "").Length));
                consumedCharsT.Add(resT.Sum(r => (double)(r.Document?.Content ?? "").Length));

            swapsTotal += recallT.LastRerankSwaps;
            if (recallT.LastRerankSwaps > 0) swapsPositive++;

            var idsC = resC.Select(r => r.Document?.Id ?? "").ToList();
            var idsT = resT.Select(r => r.Document?.Id ?? "").ToList();
            // 同池不变量按**集合**判：精排只重排 ⇒ 集合不变、顺序可变（顺序变 = 生效证据，见 swaps 计数）。
            if (idsC.OrderBy(x => x, StringComparer.Ordinal).SequenceEqual(
                    idsT.OrderBy(x => x, StringComparer.Ordinal), StringComparer.Ordinal))
                poolIdentical++;
            else poolMismatch.Add(qids[qi]);
            poolLens.Add(idsC.Count);

            var pool = resC.Select(r => new RerankCandidate(
                r.Document?.Id ?? "", r.Document?.Content ?? "", r.Score)).ToArray();
            var idxNeg = RerankStage.OrderIndices(pool, q, negScorer);
            var posScorer = new PoolScorer((_, doc, __) =>
                goldText.TryGetValue(gold, out var gt) && string.Equals(doc, gt, StringComparison.Ordinal) ? 1.0 : 0.0);
            var idxPos = RerankStage.OrderIndices(pool, q, posScorer);

            List<int> Gains(IEnumerable<string> ordered) =>
                ordered.Select(id => string.Equals(id, gold, StringComparison.Ordinal) ? 2 : 0).ToList();

            var gC = Gains(idsC);
            var gT = Gains(idsT);
            var gN = Gains(idxNeg.Select(i => pool[i].Id));
            var gP = Gains(idxPos.Select(i => pool[i].Id));

            var inPool = idsC.Any(id => string.Equals(id, gold, StringComparison.Ordinal));
            if (inPool) gated++;

            Dictionary<string, object?> Metrics(List<int> g) => new()
            {
                ["ndcg@1"] = RerankMetrics.NdcgAtK(g, 1),
                ["ndcg@5"] = RerankMetrics.NdcgAtK(g, 5),
                ["ndcg@10"] = RerankMetrics.NdcgAtK(g, 10),
                ["mrr"] = RerankMetrics.Mrr(g),
                ["p@1"] = RerankMetrics.PrecisionAtK(g, 1),
                ["p@5"] = RerankMetrics.PrecisionAtK(g, 5),
                ["p@10"] = RerankMetrics.PrecisionAtK(g, 10),
                ["recall@N"] = RerankMetrics.RecallAtN(1, inPool ? 1 : 0),
                ["gold_rank"] = g.FindIndex(0, x => x >= 1) + 1,        // 0 = 不在池内
                ["status"] = RerankMetrics.Measure(g, 10, 1, inPool ? 1 : 0).Status,
            };

            rows.Add(new Dictionary<string, object?>
            {
                ["qid"] = qids[qi],
                ["gold_in_pool"] = inPool,
                ["pool_len"] = pool.Length,
                ["last_rerank_swaps_T"] = recallT.LastRerankSwaps,
                ["C"] = Metrics(gC),
                ["T"] = Metrics(gT),
                ["NEG"] = Metrics(gN),
                ["POS"] = Metrics(gP),
            });
        }

        // ── 聚合（只在 R@N == 1 的查询上；口径见预注册 P3）──────────────────
        List<double> Col(string arm, string key) => rows
            .Where(r => (bool)r["gold_in_pool"]!)
            .Select(r => (double)((Dictionary<string, object?>)r[arm]!)[key]!)
            .ToList();

        var keys = new[] { "ndcg@1", "ndcg@5", "ndcg@10", "mrr", "p@1", "p@5", "p@10" };
        var agg = new Dictionary<string, Dictionary<string, double>>();
        foreach (var arm in new[] { "C", "T", "NEG", "POS" })
        {
            agg[arm] = new Dictionary<string, double>();
            foreach (var key in keys)
            {
                agg[arm]["median_" + key] = Median(Col(arm, key));
                agg[arm]["mean_" + key] = Col(arm, key).DefaultIfEmpty(double.NaN).Average();
            }
        }

        var criteria = new Dictionary<string, object?>
        {
            ["P1_telemetry"] = recallT.RerankApplied == qtexts.Count && recallC.RerankApplied == 0 && swapsPositive >= 1,
            ["P1_T_rerank_applied"] = recallT.RerankApplied,
            ["P1_C_rerank_applied"] = recallC.RerankApplied,
            ["P1_T_swaps_positive_queries"] = swapsPositive,
            ["P2_four_metrics_present"] = rows.Count > 0 && Col("T", "ndcg@10").Count > 0,
            ["P3_gate_gated_ge_60"] = gated >= 60,
            ["P4_cost_column_present"] = latencyUsC.Count == rows.Count && latencyUsT.Count == rows.Count
                                         && latencyUsPairDiff.Count == rows.Count && consumedCharsT.Count == rows.Count,
            ["P4_pos_median_ge_099"] = agg["POS"]["median_ndcg@10"] >= 0.99,
            ["P4_neg_not_better_than_C"] = agg["NEG"]["median_ndcg@10"] <= agg["C"]["median_ndcg@10"] + 0.02,
        };

        // ── 先落盘（失败判据也必须留证据）────────────────────────────────
        var payload = new Dictionary<string, object?>
        {
            ["schema"] = "rerank-face-readings/1",
            ["round"] = "R623",
            ["ts"] = DateTimeOffset.Now.ToString("yyyy-MM-ddTHH:mm:sszzz"),
            ["shape"] = Shape,
            ["axis"] = "RAGConfig.RerankEnabled (T=true / C=false)",
            ["pool_k"] = PoolK,
            ["embed_source"] = EmbedMode,                       // R624 形态轴：hash / vec / zero
            ["vector_store"] = vecStore?.Describe(),            // R624：vec 形态的向量件身份 + 查表命中/未命中
            ["fusion_counters_C"] = recallC.FusionCounters is null ? null : new Dictionary<string, object?>
            {
                ["dense_used"] = recallC.FusionCounters!.DenseUsed,
                ["lexical_used"] = recallC.FusionCounters!.LexicalUsed,
                ["candidates_scored"] = recallC.FusionCounters!.CandidatesScored,
                ["dim_mismatch_skipped"] = recallC.FusionCounters!.DimMismatchSkipped,
                ["single_route_fallback"] = recallC.FusionCounters!.SingleRouteFallback,
                ["bigram_memo_hits"] = recallC.FusionCounters!.BigramMemoHits,
            },
            ["frozen"] = new Dictionary<string, object?>
            {
                ["corpus"] = "eval/bge/fixtures/corpus.jsonl",
                ["corpus_sha12"] = Sha12(corpusPath),
                ["docs"] = corpus.Count,
                ["queries"] = "eval/bge/fixtures/queries.jsonl",
                ["queries_sha12"] = Sha12(queriesPath),
                ["n_queries"] = qtexts.Count,
                ["grading"] = "single-gold (grade 2 / else 0)",
            },
            ["telemetry"] = new Dictionary<string, object?>
            {
                ["pool_set_identical"] = poolIdentical,
                ["pool_mismatch"] = poolMismatch,
                ["pool_len_median"] = Median(poolLens),
                ["gated_recall_at_N_eq_1"] = gated,
                ["gated_ratio"] = Math.Round((double)gated / qtexts.Count, 4),
            },
            ["cost_informational"] = new Dictionary<string, object?>
            {
                ["ground_rule"] = "R410：墙钟只作信息字段，不作红绿判据；单位入字段名",
                ["unit_latency_us"] = "microseconds",
                ["latency_us_C_median"] = Median(latencyUsC),
                ["latency_us_T_median"] = Median(latencyUsT),
                ["latency_us_pair_diff_median"] = Median(latencyUsPairDiff),
                ["latency_us_pair_diff_p90"] = Pct(latencyUsPairDiff, 0.90),
                ["latency_us_pair_diff_min"] = latencyUsPairDiff.Count == 0 ? double.NaN : latencyUsPairDiff.Min(),
                ["latency_us_pair_diff_max"] = latencyUsPairDiff.Count == 0 ? double.NaN : latencyUsPairDiff.Max(),
                ["candidates_scored_C"] = recallC.FusionCounters?.CandidatesScored,
                ["assembled_chars_T_sum"] = consumedCharsT.Sum(),
                ["assembled_chars_C_sum"] = consumedCharsC.Sum(),
                ["token_estimator"] = "chars/3（同源：src/agent/contextassembler/ContextAssembler.Recall.cs 的 approx = Length/3）",
                ["token_est_T"] = Math.Round(consumedCharsT.Sum() / 3.0, 1),
                ["token_est_C"] = Math.Round(consumedCharsC.Sum() / 3.0, 1),
                ["remote_calls"] = 0,
            },

            ["criteria"] = criteria,
            ["aggregates"] = agg,
            ["per_query"] = rows,
        };
        File.WriteAllText(outPath,
            JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true }));

        // ── 器具硬断言（接线 / 同池 / 两侧控制分离）──────────────────────
        Assert.True((bool)criteria["P1_telemetry"]!,
            "P1 不成立：T_rerank_applied=" + recallT.RerankApplied + " C_rerank_applied=" + recallC.RerankApplied
            + " swaps_positive=" + swapsPositive);
        Assert.Equal(0, poolMismatch.Count);
        Assert.True((bool)criteria["P4_pos_median_ge_099"]!,
            "P4 不成立：POS 中位 " + agg["POS"]["median_ndcg@10"].ToString("F4"));
        Assert.True((bool)criteria["P4_neg_not_better_than_C"]!,
            "P4 不成立：NEG " + agg["NEG"]["median_ndcg@10"].ToString("F4")
            + " > C " + agg["C"]["median_ndcg@10"].ToString("F4") + " + 0.02");
        Assert.True((bool)criteria["P3_gate_gated_ge_60"]!,
            "P3 不成立：R@N==1 的查询数 " + gated + " < 60 ⇒ 不可判（rc=3）");
    }

    private static string Sha12(string path)
    {
        using var sha = System.Security.Cryptography.SHA256.Create();
        var hex = Convert.ToHexString(sha.ComputeHash(File.ReadAllBytes(path))).ToLowerInvariant();
        return hex.Substring(0, 12);
    }
}
