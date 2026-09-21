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

        // ── 两臂（唯一变量 = RerankEnabled）；落盘路径各自独立 ⇒ 零串染 ──
        // 形态 = 生产 DI（ServiceCollectionExtensions.cs:240：Fusion{Enabled,K0=10,w=1:1}）或 legacy 旧 hybrid 路。
        string TempPath(string tag) => Path.Combine(Path.GetTempPath(), $"r623-{tag}-{Guid.NewGuid():N}.jsonl");

        RAGConfig NewCfg(bool rerank)
        {
            var cfg = new RAGConfig { RerankEnabled = rerank, PersistPathOverride = TempPath(rerank ? "T" : "C") };
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

        foreach (var qi in Enumerable.Range(0, qtexts.Count))
        {
            var q = qtexts[qi];
            var gold = golds[qi];

            var resC = recallC.RecallAsync(new RecallRequest { Query = q, TopK = PoolK }).GetAwaiter().GetResult();
            var resT = recallT.RecallAsync(new RecallRequest { Query = q, TopK = PoolK }).GetAwaiter().GetResult();
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
