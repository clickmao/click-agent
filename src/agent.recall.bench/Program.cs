// R480: 独立文本召回模块 —— 测量器具 (真实语料质量臂 + 同比例压缩规模臂 + 增量保鲜臂)。
// 纪律: 所有数字来自本进程真实执行; 合成语料一律在 JSON 里标 "synthetic": true, 不与真实语料混算。
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using agent.recall;

namespace agent.recall.bench;

internal static class Program
{
    private static int Main(string[] args)
    {
        var opt = Parse(args);
        if (string.IsNullOrEmpty(opt.WorkRoot))
        {
            opt.WorkRoot = Path.Combine(Path.GetTempPath(), "recall_bench_" + Guid.NewGuid().ToString("N"));
        }
        Directory.CreateDirectory(opt.WorkRoot);
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(opt.Out)) ?? ".");

        var sw = Stopwatch.StartNew();
        var (docs, queries) = LoadCorpus(opt);
        var json = new JsonOut();
        json.BeginObject();
        json.Prop("tool", "agent.recall.bench");
        json.Prop("corpus", opt.Corpus);
        json.Prop("corpus_docs", docs.Count);
        json.Prop("queries", queries.Count);
        json.Prop("k", opt.K);
        json.Prop("host_cpu_count", Environment.ProcessorCount);
        json.Prop("measure_utc", DateTime.UtcNow.ToString("O"));

        var armA = RealArm(opt, docs, queries);
        json.PropRaw("arm_real_corpus", armA);

        var armB = ScaleArm(opt, docs);
        json.PropRaw("arm_scaled_corpus", armB);

        var armC = RefreshArm(opt);
        json.PropRaw("arm_incremental_refresh", armC);

        json.Prop("total_wall_ms", sw.ElapsedMilliseconds);
        json.EndObject();
        File.WriteAllText(opt.Out, json.ToString(), new UTF8Encoding(false));
        Console.WriteLine(json.ToString());
        try
        {
            Directory.Delete(opt.WorkRoot, true);
        }
        catch (IOException)
        {
        }
        return 0;
    }

    // ---------- 真实语料质量臂 ----------

    private static string RealArm(BenchOptions opt, List<RecallSourceDoc> docs, List<Query> queries)
    {
        string dir = Path.Combine(opt.WorkRoot, "real");
        var stats = new RecallReadStats();
        var swBuild = Stopwatch.StartNew();
        using var index = RecallIndex.Build(dir, docs, null, stats);
        swBuild.Stop();
        long indexBytes = DirBytes(dir);
        var mem = index.MemoryReport();

        // 预热一遍 (避免 JIT/页缓存首触污染分位)
        foreach (var q in queries)
        {
            index.Search(q.Text, opt.K);
        }

        var lat = new List<double>(queries.Count);
        int hit1 = 0, hit5 = 0, hit10 = 0;
        double mrr = 0;
        long visits = 0, blocks = 0, skipped = 0, reads = 0, bytesRead = 0;
        foreach (var q in queries)
        {
            var s = new RecallReadStats();
            var sw = Stopwatch.StartNew();
            var hits = index.Search(q.Text, opt.K, s);
            sw.Stop();
            lat.Add(sw.Elapsed.TotalMilliseconds);
            visits += s.PostingsVisited;
            blocks += s.BlocksScanned;
            skipped += s.BlocksSkipped;
            reads += s.Reads;
            bytesRead += s.BytesRead;
            for (int i = 0; i < hits.Count; i++)
            {
                if (hits[i].Id == q.GoldId)
                {
                    if (i == 0)
                    {
                        hit1++;
                    }
                    if (i < 5)
                    {
                        hit5++;
                    }
                    hit10++;
                    mrr += 1.0 / (i + 1);
                    break;
                }
            }
        }

        var o = new JsonOut();
        o.BeginObject();
        o.Prop("synthetic", false);
        o.Prop("docs", docs.Count);
        o.Prop("query_count", queries.Count);
        o.Prop("build_ms", swBuild.ElapsedMilliseconds);
        o.Prop("build_docs_per_sec", swBuild.ElapsedMilliseconds == 0 ? 0 : Math.Round(docs.Count * 1000.0 / swBuild.ElapsedMilliseconds, 1));
        o.Prop("index_bytes", indexBytes);
        o.Prop("index_bytes_per_doc", docs.Count == 0 ? 0 : Math.Round((double)indexBytes / docs.Count, 1));
        o.Prop("resident_bytes_total", mem.TotalBytes);
        o.Prop("rss_mb_after_open", RssMb());
        o.Prop("recall_at_1", Math.Round((double)hit1 / Math.Max(1, queries.Count), 4));
        o.Prop("recall_at_5", Math.Round((double)hit5 / Math.Max(1, queries.Count), 4));
        o.Prop("recall_at_10", Math.Round((double)hit10 / Math.Max(1, queries.Count), 4));
        o.Prop("mrr", Math.Round(mrr / Math.Max(1, queries.Count), 4));
        o.Prop("latency_ms_p50", Math.Round(Percentile(lat, 50), 3));
        o.Prop("latency_ms_p95", Math.Round(Percentile(lat, 95), 3));
        o.Prop("latency_ms_p99", Math.Round(Percentile(lat, 99), 3));
        o.Prop("latency_ms_max", Math.Round(lat.Count == 0 ? 0 : lat.Max(), 3));
        o.Prop("postings_visited_total", visits);
        o.Prop("blocks_scanned_total", blocks);
        o.Prop("blocks_skipped_total", skipped);
        o.Prop("preads_total", reads);
        o.Prop("pread_bytes_total", bytesRead);
        o.EndObject();
        return o.ToString();
    }

    // ---------- 同比例压缩规模臂 ----------

    private static string ScaleArm(BenchOptions opt, List<RecallSourceDoc> docs)
    {
        var rnd = new Random(opt.Seed);
        var vocab = BuildVocab(docs);
        var lengths = docLengths(docs);
        var queries = BuildScaleQueries(vocab.Terms);
        var o = new JsonOut();
        o.BeginObject();
        o.Prop("synthetic", true);
        o.Prop("note", "同比例压缩: 词频分布与文档长度分布取自真实语料, 规模按比例缩小, 不外推结论到真实分布");
        o.PropRaw("vocab_terms", vocab.Terms.Count.ToString());
        o.BeginArray("scales");
        var rows = new List<(int Docs, double P50, double P95, long Bytes, long Resident, long Visits, double BuildMs)>();
        foreach (int mult in opt.Scales)
        {
            int n = Math.Max(1, docs.Count * mult);
            string dir = Path.Combine(opt.WorkRoot, "scale_" + mult);
            var synth = GenerateCorpus(n, vocab, lengths, rnd);
            var swBuild = Stopwatch.StartNew();
            using var index = RecallIndex.Build(dir, synth);
            swBuild.Stop();
            long bytes = DirBytes(dir);
            long resident = index.MemoryReport().TotalBytes;
            foreach (var t in queries)
            {
                index.Search(t, opt.K);
            }
            var lat = new List<double>();
            long visits = 0;
            foreach (var t in queries)
            {
                var s = new RecallReadStats();
                var sw = Stopwatch.StartNew();
                index.Search(t, opt.K, s);
                sw.Stop();
                lat.Add(sw.Elapsed.TotalMilliseconds);
                visits += s.PostingsVisited;
            }
            rows.Add((n, Percentile(lat, 50), Percentile(lat, 95), bytes, resident, visits, swBuild.Elapsed.TotalMilliseconds));
            var r = new JsonOut();
            r.BeginObject();
            r.Prop("docs", n);
            r.Prop("build_ms", swBuild.ElapsedMilliseconds);
            r.Prop("index_bytes", bytes);
            r.Prop("resident_bytes", resident);
            r.Prop("latency_ms_p50", Math.Round(Percentile(lat, 50), 3));
            r.Prop("latency_ms_p95", Math.Round(Percentile(lat, 95), 3));
            r.Prop("postings_visited_total", visits);
            r.Prop("rss_mb", RssMb());
            r.EndObject();
            o.Raw(r.ToString());
            try
            {
                Directory.Delete(dir, true);
            }
            catch (IOException)
            {
            }
        }
        o.EndArray();
        if (rows.Count >= 2)
        {
            // 由最小与最大两点的 postings 访问量估计增长指数, 并给出到 1e6 文档的分位外推
            var lo = rows[0];
            var hi = rows[^1];
            double docRatio = (double)hi.Docs / lo.Docs;
            double latRatio = Math.Max(1e-9, hi.P50) / Math.Max(1e-9, lo.P50);
            double exponent = docRatio > 1 ? Math.Log(latRatio) / Math.Log(docRatio) : 1;
            double to1e6 = lo.P50 * Math.Pow(1_000_000.0 / lo.Docs, exponent);
            o.BeginObject("extrapolation");
            o.Prop("model", "p50 = c * docs^exponent (两点估计, 不假定线性)");
            o.Prop("doc_ratio", Math.Round(docRatio, 2));
            o.Prop("p50_ratio", Math.Round(latRatio, 3));
            o.Prop("exponent", Math.Round(exponent, 3));
            o.Prop("p50_ms_at_1e6_projected", Math.Round(to1e6, 3));
            o.Prop("target_ms", 50);
            o.Prop("target_met", to1e6 <= 50);
            o.EndObject();
        }
        o.EndObject();
        return o.ToString();
    }

    private static List<string> BuildScaleQueries(List<(string Term, int Weight)> vocab)
    {
        var qs = new List<string>();
        // 高频 / 中频 / 低频 三种负载
        foreach (int idx in new[] { 0, 1, 2, vocab.Count / 2, vocab.Count - 3, vocab.Count - 2, vocab.Count - 1 })
        {
            if (idx >= 0 && idx < vocab.Count)
            {
                qs.Add(vocab[idx].Term);
            }
        }
        for (int i = 0; i + 1 < vocab.Count; i += Math.Max(1, vocab.Count / 8))
        {
            qs.Add(vocab[i].Term + " " + vocab[Math.Min(vocab.Count - 1, i + 1)].Term);
        }
        return qs.Where(q => q.Length > 0).Distinct().ToList();
    }

    private static List<RecallSourceDoc> GenerateCorpus(int n, VocabSampler vocab, List<int> lengths, Random rnd)
    {
        var docs = new List<RecallSourceDoc>(n);
        var sb = new StringBuilder(1024);
        for (int i = 0; i < n; i++)
        {
            int len = lengths[rnd.Next(lengths.Count)];
            sb.Clear();
            for (int t = 0; t < len; t++)
            {
                sb.Append(vocab.Sample(rnd));
                sb.Append(' ');
            }
            docs.Add(new RecallSourceDoc
            {
                Id = "syn-" + i,
                Path = "synthetic/" + (i % 512) + "/doc-" + i,
                Text = sb.ToString(),
                Size = 0,
                MtimeTicks = 0,
                Inode = 0,
            });
        }
        return docs;
    }

    /// <summary>按真实词频分布抽样 (累积权重 + 二分) ⇒ 合成语料的词频形状与真实语料同比例。</summary>
    internal sealed class VocabSampler
    {
        public required List<(string Term, int Weight)> Terms { get; init; }
        public required long[] Cumulative { get; init; }

        public string Sample(Random rnd)
        {
            long total = Cumulative[^1];
            long pick = (long)(rnd.NextDouble() * total);
            int lo = 0, hi = Cumulative.Length - 1;
            while (lo < hi)
            {
                int mid = (lo + hi) / 2;
                if (Cumulative[mid] <= pick)
                {
                    lo = mid + 1;
                }
                else
                {
                    hi = mid;
                }
            }
            return Terms[lo].Term;
        }
    }

    private static VocabSampler BuildVocab(List<RecallSourceDoc> docs)
    {
        var counts = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (var d in docs)
        {
            var sink = new CountingSink(counts);
            RecallTokenizer.Tokenize(d.Text.AsSpan(), RecallTokenizerOptions.Default, sink);
        }
        var list = counts.Select(kv => (kv.Key, kv.Value)).ToList();
        list.Sort((a, b) =>
        {
            int c = b.Item2.CompareTo(a.Item2);
            return c != 0 ? c : string.CompareOrdinal(a.Item1, b.Item1);
        });
        var cum = new long[list.Count];
        long run = 0;
        for (int i = 0; i < list.Count; i++)
        {
            run += list[i].Item2;
            cum[i] = run;
        }
        return new VocabSampler { Terms = list, Cumulative = cum };
    }

    private sealed class CountingSink : ITokenSink
    {
        private readonly Dictionary<string, int> _counts;

        public CountingSink(Dictionary<string, int> counts) => _counts = counts;

        public void AddToken(ReadOnlySpan<byte> token)
        {
            string t = Encoding.UTF8.GetString(token);
            _counts[t] = _counts.TryGetValue(t, out int c) ? c + 1 : 1;
        }
    }

    private static List<int> docLengths(List<RecallSourceDoc> docs)
    {
        var lens = new List<int>(docs.Count);
        foreach (var d in docs)
        {
            var sink = new CollectingCountSink();
            RecallTokenizer.Tokenize(d.Text.AsSpan(), RecallTokenizerOptions.Default, sink);
            lens.Add(Math.Max(1, sink.Count));
        }
        return lens;
    }

    private sealed class CollectingCountSink : ITokenSink
    {
        public int Count { get; private set; }

        public void AddToken(ReadOnlySpan<byte> token) => Count++;
    }

    // ---------- 增量保鲜臂 ----------

    private static string RefreshArm(BenchOptions opt)
    {
        string root = Path.GetFullPath(opt.RefreshRoot);
        string indexDir = Path.Combine(opt.WorkRoot, "refresh");
        var o = new JsonOut();
        o.BeginObject();
        o.Prop("root", root);
        o.Prop("root_exists", Directory.Exists(root));
        if (!Directory.Exists(root))
        {
            o.Prop("skipped", "root not found");
            o.EndObject();
            return o.ToString();
        }
        var options = new RecallUpdateOptions();
        var full = RecallIndexUpdater.Update(root, indexDir, options);
        var idle = RecallIndexUpdater.Update(root, indexDir, options);
        string probe = Path.Combine(root, "recall_refresh_probe.md");
        string probe2 = Path.Combine(root, "recall_refresh_probe2.md");
        var inserts = new List<(string Path, string Text)>();
        try
        {
            File.WriteAllText(probe, "增量保鲜探针 铱 内容 alpha", new UTF8Encoding(false));
            File.WriteAllText(probe2, "增量保鲜探针 锇 内容 beta", new UTF8Encoding(false));
            var inc = RecallIndexUpdater.Update(root, indexDir, options);
            o.Prop("full_ms", full.TotalMs);
            o.Prop("full_files_seen", full.FilesSeen);
            o.Prop("full_docs_indexed", full.DocsIndexed);
            o.Prop("full_index_bytes", DirBytes(indexDir));
            o.Prop("idle_ms", idle.TotalMs);
            o.Prop("idle_scan_ms", idle.ScanMs);
            o.Prop("idle_dirs_pruned", idle.DirsPruned);
            o.Prop("idle_files_seen", idle.FilesSeen);
            o.Prop("idle_wrote_index", idle.WroteIndex);
            o.Prop("incremental_ms", inc.TotalMs);
            o.Prop("incremental_added", inc.Added);
            o.Prop("incremental_docs_indexed", inc.DocsIndexed);
            using var index = RecallIndex.Open(indexDir);
            var hits = index.Search("铱", 5);
            o.Prop("incremental_hit_ok", hits.Count > 0 && hits[0].Path.EndsWith("recall_refresh_probe.md", StringComparison.Ordinal));
        }
        finally
        {
            foreach (string p in new[] { probe, probe2 })
            {
                try
                {
                    File.Delete(p);
                }
                catch (IOException)
                {
                }
            }
            RecallIndexUpdater.Update(root, indexDir, options);
        }
        o.EndObject();
        return o.ToString();
    }

    // ---------- 载入 ----------

    private sealed class Query
    {
        public required string Qid { get; init; }
        public required string GoldId { get; init; }
        public required string Text { get; init; }
    }

    private static (List<RecallSourceDoc>, List<Query>) LoadCorpus(BenchOptions opt)
    {
        var docs = new List<RecallSourceDoc>();
        foreach (string line in File.ReadLines(opt.Corpus))
        {
            if (line.Length == 0)
            {
                continue;
            }
            using var doc = JsonDocument.Parse(line);
            var r = doc.RootElement;
            docs.Add(new RecallSourceDoc
            {
                Id = r.GetProperty("id").GetString() ?? "",
                Path = r.TryGetProperty("src", out var s) ? s.GetString() ?? "" : "",
                Text = r.GetProperty("text").GetString() ?? "",
                Size = 0,
                MtimeTicks = 0,
                Inode = 0,
            });
        }
        var queries = new List<Query>();
        foreach (string line in File.ReadLines(opt.Queries))
        {
            if (line.Length == 0)
            {
                continue;
            }
            using var doc = JsonDocument.Parse(line);
            var r = doc.RootElement;
            queries.Add(new Query
            {
                Qid = r.GetProperty("qid").GetString() ?? "",
                GoldId = r.GetProperty("gold_id").GetString() ?? "",
                Text = r.GetProperty("query").GetString() ?? "",
            });
        }
        return (docs, queries);
    }

    // ---------- 工具 ----------

    private static double Percentile(List<double> values, int p)
    {
        if (values.Count == 0)
        {
            return 0;
        }
        var sorted = values.OrderBy(v => v).ToList();
        int idx = (int)Math.Ceiling(p / 100.0 * sorted.Count) - 1;
        return sorted[Math.Clamp(idx, 0, sorted.Count - 1)];
    }

    private static long DirBytes(string dir)
    {
        long total = 0;
        foreach (string f in Directory.EnumerateFiles(dir, "*", SearchOption.AllDirectories))
        {
            total += new FileInfo(f).Length;
        }
        return total;
    }

    private static double RssMb()
    {
        try
        {
            string statm = File.ReadAllText("/proc/self/statm");
            string[] parts = statm.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length > 1 && long.TryParse(parts[1], out long pages))
            {
                return Math.Round(pages * 4096.0 / (1024 * 1024), 1);
            }
        }
        catch (IOException)
        {
        }
        return -1;
    }

    private static BenchOptions Parse(string[] args)
    {
        var opt = new BenchOptions();
        for (int i = 0; i < args.Length; i++)
        {
            string a = args[i];
            string Next() => i + 1 < args.Length ? args[++i] : "";
            switch (a)
            {
                case "--corpus": opt.Corpus = Next(); break;
                case "--queries": opt.Queries = Next(); break;
                case "--out": opt.Out = Next(); break;
                case "--workroot": opt.WorkRoot = Next(); break;
                case "--refresh-root": opt.RefreshRoot = Next(); break;
                case "--k": opt.K = int.Parse(Next()); break;
                case "--seed": opt.Seed = int.Parse(Next()); break;
                case "--scales": opt.Scales = Next().Split(',', StringSplitOptions.RemoveEmptyEntries).Select(int.Parse).ToArray(); break;
            }
        }
        return opt;
    }
}
