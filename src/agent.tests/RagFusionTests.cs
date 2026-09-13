using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.Json;
using agent.rag;
using Xunit;

namespace agent.tests;

/// <summary>
/// R404 (用户钦定): "优化后的 bge" 落地机检 —— 融合检索端口与 eval/bge 冻结口径**逐位对账**。
///
/// 判据 (预注册在此, 不许事后调):
///   ① 单路独立复现: 词法路 r@10 = 0.7500、dense-base r@10 = 0.7417 (Python 冻结值);
///   ② 融合复现: RRF(k0=10, w=1:1) 的 r@1/r@10/mrr@10 = 0.5333/0.8500/0.6439;
///   ③ 逐查询 0 起名次与 eval/bge/ranks/fusion-best.json 的 ranks **逐位相等** (不只看总分);
///   ④ 两侧样例: 词法/融合小样例手算值 + 单路降级计数 + 维度不匹配跳过计数 (判定器必须两侧都给样例)。
/// 环境不备 (无模型/无 fixture) 时**显式**跳过并落盘标记, 绝不静默通过。
/// </summary>
public class RagFusionTests
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

    // ── ④ 两侧样例: 纯函数判据 ─────────────────────────────────────────────
    [Fact]
    public void CharacterBigrams_MatchesPythonGrams()
    {
        // Python: "".join(ch for ch in s if not ch.isspace()) 再滑 2-gram 去重
        var g = FusionMath.CharacterBigrams("ab cd");   // 去空白 -> "abcd" -> {ab,bc,cd}
        Assert.Equal(3, g.Length);
        Assert.Contains("ab", g);
        Assert.Contains("bc", g);
        Assert.Contains("cd", g);
        Assert.DoesNotContain(" d", g);
        Assert.Equal(0, FusionMath.CharacterBigrams("").Length);
        Assert.Equal(0, FusionMath.CharacterBigrams(" \t\n ").Length);
        Assert.Single(FusionMath.CharacterBigrams("a b"));       // 去空白 -> "ab" -> 1 个
        Assert.Equal(2, FusionMath.CharacterBigrams("abc").Length); // {ab,bc}
    }

    [Fact]
    public void Jaccard_TwoSidedSamples()
    {
        var q = "abcd";                                  // {ab,bc,cd}
        var qset = new HashSet<string>(FusionMath.CharacterBigrams(q), StringComparer.Ordinal);
        var empty = new HashSet<string>(FusionMath.CharacterBigrams(""), StringComparer.Ordinal);
        Assert.Equal(1.0, FusionMath.Jaccard(qset, FusionMath.CharacterBigrams("abcd")), 12);
        Assert.Equal(0.0, FusionMath.Jaccard(qset, FusionMath.CharacterBigrams("wxyz")), 12);
        // "abef" -> {ab,be,ef}: 交 {ab} 并 {ab,bc,cd,be,ef} = 1/5
        Assert.Equal(0.2, FusionMath.Jaccard(qset, FusionMath.CharacterBigrams("abef")), 12);
        Assert.Equal(0.0, FusionMath.Jaccard(empty, FusionMath.CharacterBigrams("abcd")), 12);   // 空查询 ⇒ 0
        Assert.Equal(0.0, FusionMath.Jaccard(qset, Array.Empty<string>()), 12);                  // 空文档 ⇒ 0
    }

    [Fact]
    public void Rrf_HandComputed_Scores()
    {
        // 3 候选 x 2 路, k0=10 => score = 1/(10+rank+1) 两路相加
        var fuser = new RrfFuser(10);
        var routeA = new[] { 0, 1, 2 };   // A: d0 第0名, d1 第1名, d2 第2名
        var routeB = new[] { 2, 1, 0 };   // B: 反向
        var s = fuser.Scores(new List<int[]> { routeA, routeB }, new List<double> { 1.0, 1.0 }, 3);
        Assert.Equal(1.0 / 11 + 1.0 / 13, s[0], 12);
        Assert.Equal(2.0 / 12, s[1], 12);
        Assert.Equal(1.0 / 13 + 1.0 / 11, s[2], 12);
        Assert.Equal(2.0 / 11, fuser.MaxScore(new List<double> { 1.0, 1.0 }), 12);
    }

    [Fact]
    public void Fusion_SingleRouteFallback_IsCounted_NotSilent()
    {
        var opts = new FusionOptions { Enabled = true, K0 = 10 };
        var fusion = new FusionRecall(opts, dense: null, lexical: new LexicalRoute());   // 故意缺一路
        var cands = new List<RetrievalCandidate>
        {
            new() { Id = "d0", Text = "缓存 命中 统计" },
            new() { Id = "d1", Text = "完全无关的内容" },
        };
        var ranked = fusion.Rank(new QueryContext("缓存命中统计", null), cands);
        Assert.Equal(2, ranked.Count);
        Assert.Equal("d0", ranked[0].Key.Id);
        Assert.Equal(1, fusion.Counters.SingleRouteFallback);
        Assert.Equal(0, fusion.Counters.DenseUsed);
        Assert.Equal(1, fusion.Counters.LexicalUsed);
    }

    [Fact]
    public void DenseRoute_DimMismatch_SkippedAndCounted()
    {
        var dense = new DenseRoute();
        var cands = new List<RetrievalCandidate>
        {
            new() { Id = "old512", Text = "旧维度残留", Embedding = new float[512] },
            new() { Id = "new768", Text = "新维度", Embedding = new float[768] },
        };
        var q = new float[768];
        q[0] = 1f;
        cands[1].Embedding![0] = 1f;
        var ranks = dense.Rank(new QueryContext("x", q), cands);
        Assert.Equal(1, dense.SkippedDimMismatch);
        Assert.Equal(0, ranks[1]);      // 维度匹配且同向 => 第 0 名
        Assert.Equal(1, ranks[0]);      // 维度不匹配 => 沉底
    }

    // ── ①②③ 冻结集逐位对账 ────────────────────────────────────────────────
    [Fact]
    public void FrozenFixture_RoutesAndFusion_MatchPythonBitForBit()
    {
        var fix = Path.Combine(Repo, "eval", "bge", "fixtures");
        var corpusPath = Path.Combine(fix, "corpus.jsonl");
        var queriesPath = Path.Combine(fix, "queries.jsonl");
        var cacheDir = Path.Combine(Repo, "data", "bge", "cache");
        var goldenPath = Path.Combine(Repo, "eval", "bge", "ranks", "fusion-best.json");
        var evidDir = Path.Combine(Repo, "eval", "bge", "r404");
        Directory.CreateDirectory(evidDir);
        var evidPath = Path.Combine(evidDir, "csharp-fusion-replay.json");

        if (!File.Exists(corpusPath) || !File.Exists(queriesPath) || !File.Exists(goldenPath))
        {
            File.WriteAllText(evidPath, "{\"skipped\":\"fixture/golden missing\"}");
            return;
        }

        var corpus = new List<(string Id, string Text)>();
        foreach (var line in File.ReadLines(corpusPath))
            if (!string.IsNullOrWhiteSpace(line))
                using (var d = JsonDocument.Parse(line))
                    corpus.Add((d.RootElement.GetProperty("id").GetString()!,
                                d.RootElement.GetProperty("text").GetString()!));

        var qids = new List<string>();
        var golds = new List<string>();
        var qtexts = new List<string>();
        foreach (var line in File.ReadLines(queriesPath))
            if (!string.IsNullOrWhiteSpace(line))
                using (var d = JsonDocument.Parse(line))
                {
                    qids.Add(d.RootElement.GetProperty("qid").GetString()!);
                    golds.Add(d.RootElement.GetProperty("gold_id").GetString()!);
                    qtexts.Add(d.RootElement.GetProperty("query").GetString()!);
                }

        Assert.Equal(1299, corpus.Count);
        Assert.Equal(120, qtexts.Count);

        // 缓存向量 (Python/llama.cpp 产出; 文件头 = n,d 两个 int64 LE, 后接 n*d float32 LE)
        var cvecFile = Directory.GetFiles(cacheDir, "bge-base-zh-v1.5-q8__fuse_corpus_*_1299_*.f32").FirstOrDefault();
        var qvecFile = Directory.GetFiles(cacheDir, "bge-base-zh-v1.5-q8__fuse_queries_*_120_*.f32").FirstOrDefault();
        if (cvecFile is null || qvecFile is null)
        {
            File.WriteAllText(evidPath, "{\"skipped\":\"embedding cache missing\"}");
            return;
        }
        var cvecs = ReadVecCache(cvecFile);
        var qvecs = ReadVecCache(qvecFile);
        Assert.Equal(1299, cvecs.Count);
        Assert.Equal(120, qvecs.Count);
        Assert.Equal(768, cvecs[0].Length);

        var cands = new List<RetrievalCandidate>(1299);
        for (var i = 0; i < corpus.Count; i++)
            cands.Add(new RetrievalCandidate { Id = corpus[i].Id, Text = corpus[i].Text, Embedding = cvecs[i] });
        var cpos = new Dictionary<string, int>(StringComparer.Ordinal);
        for (var i = 0; i < corpus.Count; i++) cpos[corpus[i].Id] = i;

        var lexical = new LexicalRoute();
        var dense = new DenseRoute();
        var lexGold = new List<int>(120);
        var baseGold = new List<int>(120);
        for (var qi = 0; qi < qtexts.Count; qi++)
        {
            var ctx = new QueryContext(qtexts[qi], qvecs[qi]);
            lexGold.Add(lexical.Rank(ctx, cands)[cpos[golds[qi]]]);
            baseGold.Add(dense.Rank(ctx, cands)[cpos[golds[qi]]]);
        }

        var lexM = Metrics(lexGold);
        var baseM = Metrics(baseGold);
        Assert.Equal(0.7500, lexM["r@10"], 4);          // ① 词法路独立复现
        Assert.Equal(0.7417, baseM["r@10"], 4);         // ① dense-base 独立复现
        Assert.True(dense.SkippedDimMismatch == 0, "维度不匹配计数应为 0 (冻结集同维)");

        // ②③ 融合: 与 Python rrf_all 同序 (tie-break 索引升序) + 逐查询名次逐位相等
        var fusion = new FusionRecall(new FusionOptions { Enabled = true, K0 = 10, DenseWeight = 1.0, LexicalWeight = 1.0 }, dense, lexical);
        var fusedGold = new List<int>(120);
        for (var qi = 0; qi < qtexts.Count; qi++)
        {
            var ctx = new QueryContext(qtexts[qi], qvecs[qi]);
            var ranked = fusion.Rank(ctx, cands);
            var goldPos = -1;
            for (var i = 0; i < ranked.Count; i++)
                if (ReferenceEquals(ranked[i].Key, cands[cpos[golds[qi]]])) { goldPos = i; break; }
            Assert.True(goldPos >= 0, "金标准不在候选池内");
            fusedGold.Add(goldPos);
        }

        var fusedM = Metrics(fusedGold);
        Assert.Equal(0.5333, fusedM["r@1"], 4);
        Assert.Equal(0.8500, fusedM["r@10"], 4);
        Assert.Equal(0.6439, fusedM["mrr@10"], 4);

        using var golden = JsonDocument.Parse(File.ReadAllText(goldenPath));
        var goldenRanks = golden.RootElement.GetProperty("ranks").EnumerateArray().Select(e => e.GetInt32()).ToList();
        Assert.Equal(120, goldenRanks.Count);

        // 冻结文件 ranks 的口径用**它自己的 metrics** 反推 + 逐位形态双重确认 (不靠猜):
        //   · 0 起直读 ⇒ r@1 = 0, 与文件 metrics 0.5333 矛盾 ⇒ 不是原始 0 起名次;
        //   · 按 r1 直算 (1 起, >50 折 999) ⇒ 逐位复现文件 metrics;
        //   · 形态佐证: q#30 处文件值 999, 而该查询金标准真实 0 起名次 1174 (1175 > 50 折 999)。
        // 这正是仓库 recall_metrics 的折算口径 (">50 记 999")。
        var asRaw0 = Metrics(goldenRanks);
        Assert.True(Math.Abs(asRaw0["r@1"] - 0.5333) > 1e-9, "0 起直读也自洽 ⇒ 口径判定不成立, 需人工复核");
        var asR1 = MetricsFromR1(goldenRanks);
        Assert.Equal(0.5333, asR1["r@1"], 4);
        Assert.Equal(0.8500, asR1["r@10"], 4);
        Assert.Equal(0.6439, asR1["mrr@10"], 4);

        var firstDiff = -1;
        for (var i = 0; i < 120; i++) if (goldenRanks[i] != ToR1(fusedGold[i])) { firstDiff = i; break; }
        Assert.True(firstDiff < 0,
            $"逐查询名次与 Python 冻结值不一致: 首差 q#{firstDiff} python(r1)={goldenRanks.ElementAtOrDefault(firstDiff)} csharp(r1)={ToR1(fusedGold.ElementAtOrDefault(firstDiff))} (csharp 原始 0 起={fusedGold.ElementAtOrDefault(firstDiff)})");

        // 证据落盘 (打点)
        var evid = new System.Text.StringBuilder();
        evid.Append("{\"kind\":\"csharp_fusion_replay\",\"ts\":\"")
            .Append(DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture)).Append("\",");
        evid.Append("\"corpus\":").Append(corpus.Count).Append(",\"queries\":").Append(qtexts.Count).Append(',');
        evid.Append("\"lexical_r@10\":").Append(lexM["r@10"].ToString(CultureInfo.InvariantCulture)).Append(',');
        evid.Append("\"dense_base_r@10\":").Append(baseM["r@10"].ToString(CultureInfo.InvariantCulture)).Append(',');
        evid.Append("\"rrf_r@1\":").Append(fusedM["r@1"].ToString(CultureInfo.InvariantCulture)).Append(',');
        evid.Append("\"rrf_r@10\":").Append(fusedM["r@10"].ToString(CultureInfo.InvariantCulture)).Append(',');
        evid.Append("\"rrf_mrr@10\":").Append(fusedM["mrr@10"].ToString(CultureInfo.InvariantCulture)).Append(',');
        evid.Append("\"ranks_bitwise_equal_python\":true,\"fusion_calls\":").Append(fusion.Counters.FusionCalls).Append(',');
        evid.Append("\"dense_used\":").Append(fusion.Counters.DenseUsed).Append(',');
        evid.Append("\"lexical_used\":").Append(fusion.Counters.LexicalUsed).Append('}');
        File.WriteAllText(evidPath, evid.ToString());
    }

    /// <summary>与 eval/bge/fusion.py metrics_from_ranks 同式 (0 起名次 → 1 起, >50 记 999)。</summary>
    private static Dictionary<string, double> Metrics(List<int> ranks0)
        => MetricsFromR1(ranks0.Select(r => r + 1 <= 50 ? r + 1 : 999).ToList());

    /// <summary>文件内 ranks = 折算后的 r1 (1 起, >50 折 999) ⇒ 直接按 r1 判定。</summary>
    private static Dictionary<string, double> MetricsFromR1(List<int> r1)
    {
        var n = r1.Count;
        double At(int k) => Math.Round(r1.Count(r => r <= k) / (double)n, 4);
        var mrr = Math.Round(r1.Where(r => r <= 10).Sum(r => 1.0 / r) / n, 4);
        return new Dictionary<string, double>
        {
            ["r@1"] = At(1), ["r@5"] = At(5), ["r@10"] = At(10), ["r@20"] = At(20), ["mrr@10"] = mrr,
        };
    }

    /// <summary>0 起名次 → 折算 r1 (1 起, >50 折 999)。</summary>
    private static int ToR1(int rank0)
    {
        var r1 = rank0 + 1;
        return r1 <= 50 ? r1 : 999;
    }

    private static List<float[]> ReadVecCache(string path)
    {
        Assert.True(BitConverter.IsLittleEndian, "缓存为小端 float32; 大端机需转换");
        var bytes = File.ReadAllBytes(path);
        var n = (int)BitConverter.ToInt64(bytes, 0);
        var d = (int)BitConverter.ToInt64(bytes, 8);
        Assert.Equal(16 + (long)n * d * 4, bytes.LongLength);
        var outv = new List<float[]>(n);
        for (var i = 0; i < n; i++)
        {
            var v = new float[d];
            Buffer.BlockCopy(bytes, 16 + i * d * 4, v, 0, d * 4);
            outv.Add(v);
        }
        return outv;
    }
}
