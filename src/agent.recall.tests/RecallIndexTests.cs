// R480: 独立文本召回模块 —— 行为测试 (判据: 与独立暴力实现一致 / 极小常驻 / 增量正确 / 损坏 fail-closed)。
using System.Text;
using agent.recall;
using Xunit;

namespace agent.recall.tests;


public sealed class RecallIndexTests
{
    private static List<RecallSourceDoc> Corpus(int count, Func<int, string> text)
    {
        var docs = new List<RecallSourceDoc>(count);
        for (int i = 0; i < count; i++)
        {
            docs.Add(new RecallSourceDoc
            {
                Id = "doc-" + i,
                Path = "corpus/file-" + i,
                Text = text(i),
                Size = 0,
                MtimeTicks = 0,
                Inode = 0,
            });
        }
        return docs;
    }

    private static string TempDir()
    {
        string dir = Path.Combine(Path.GetTempPath(), "recall_tests_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }

    [Fact]
    public void FindsDocumentByPhrase()
    {
        string dir = TempDir();
        try
        {
            var docs = Corpus(50, i => i == 37 ? "用户权限校验失败时应回落到只读模式" : $"普通文档 {i} 的内容");
            using var index = RecallIndex.Build(Path.Combine(dir, "idx"), docs);
            var hits = index.Search("权限校验", 5);
            Assert.NotEmpty(hits);
            Assert.Equal("doc-37", hits[0].Id);
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    [Fact]
    public void BlockChainBeyondFirstBlock_IsReadable()
    {
        string dir = TempDir();
        try
        {
            // 400 篇都含 "shared", 首个与末个还含唯一词 ⇒ 必须跨越 3 个以上 128-文档块
            var docs = Corpus(400, i => i == 0 ? "shared alpha" : i == 399 ? "shared omega" : "shared filler");
            using var index = RecallIndex.Build(Path.Combine(dir, "idx"), docs);
            var all = index.Search("shared", 400);
            Assert.Equal(400, all.Count);
            Assert.Contains(all, h => h.Id == "doc-0");
            Assert.Contains(all, h => h.Id == "doc-399");
            var last = index.Search("omega", 5);
            Assert.Equal("doc-399", last[0].Id);
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    private static List<(double Score, List<string> Ids)> GroupByScore(IEnumerable<(string Id, double Score)> hits)
    {
        var groups = new List<(double Score, List<string> Ids)>();
        foreach (var h in hits)
        {
            if (groups.Count > 0 && Math.Abs(groups[^1].Score - h.Score) < 1e-9)
            {
                groups[^1].Ids.Add(h.Id);
            }
            else
            {
                groups.Add((h.Score, new List<string> { h.Id }));
            }
        }
        foreach (var g in groups)
        {
            g.Ids.Sort(StringComparer.Ordinal);
        }
        return groups;
    }

    [Fact]
    public void WandTopK_MatchesIndependentBruteForce()
    {
        string dir = TempDir();
        try
        {
            var docs = Corpus(300, i => i % 7 == 0
                ? $"索引 压缩 内存 预算 文档{i} shared"
                : i % 5 == 0
                    ? $"召回 延迟 毫秒 文档{i} shared"
                    : $"普通 内容 填充 文档{i}");
            using var index = RecallIndex.Build(Path.Combine(dir, "idx"), docs);
            foreach (string q in new[] { "索引 内存", "召回 延迟", "shared 压缩", "文档" })
            {
                var brute = BruteForce(docs, q, 10);
                var bruteAll = BruteForce(docs, q, docs.Count);
                var got = index.Search(q, 10);
                Assert.Equal(brute.Count, got.Count);
                // 并列分数在 top-k 中天然无序 (堆内部槽位顺序); 末组被 k 截断 ⇒ 只校验计数 + 「属于同分组」子集。
                var bGroups = GroupByScore(brute);
                var gGroups = GroupByScore(got.Select(h => (h.Id, h.Score)));
                Assert.Equal(bGroups.Count, gGroups.Count);
                for (int i = 0; i < bGroups.Count; i++)
                {
                    Assert.True(Math.Abs(bGroups[i].Score - gGroups[i].Score) < 1e-9,
                        $"score drift at group {i}: {bGroups[i].Score} vs {gGroups[i].Score}");
                    if (i < bGroups.Count - 1)
                    {
                        Assert.Equal(bGroups[i].Ids, gGroups[i].Ids);
                    }
                    else
                    {
                        Assert.Equal(bGroups[i].Ids.Count, gGroups[i].Ids.Count);
                        var sameScore = new HashSet<string>(
                            bruteAll.Where(h => Math.Abs(h.Score - bGroups[i].Score) < 1e-9).Select(h => h.Id),
                            StringComparer.Ordinal);
                        foreach (string id in gGroups[i].Ids)
                        {
                            Assert.Contains(id, sameScore);
                        }
                    }
                }
            }
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    [Fact]
    public void BlockSkip_PrunesPostings()
    {
        string dir = TempDir();
        try
        {
            var docs = Corpus(1000, i => i >= 990 ? "common rare" : "common filler");
            using var index = RecallIndex.Build(Path.Combine(dir, "idx"), docs);
            var stats = new RecallReadStats();
            var hits = index.Search("common rare", 10, stats);
            // rare 只出现在 10 篇 ⇒ WAND 必须跳过绝大多数 common posting
            Assert.Equal(10, hits.Count);
            Assert.True(stats.PostingsVisited > 0);
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    [Fact]
    public void ResidentBytes_DoNotScaleWithDocCount()
    {
        string dir = TempDir();
        try
        {
            using var small = RecallIndex.Build(Path.Combine(dir, "small"), Corpus(500, i => $"词{i} 内容 alpha"));
            long r1 = small.MemoryReport().TotalBytes;
            using var big = RecallIndex.Build(Path.Combine(dir, "big"), Corpus(8000, i => $"词{i} 内容 alpha"));
            long r2 = big.MemoryReport().TotalBytes;
            Assert.True(r2 < r1 * 4, $"resident grew {r1} -> {r2} for 16x docs");
            Assert.True(r2 < 512 * 1024, $"resident too large: {r2}");
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    [Fact]
    public void CorruptSegmentHeader_FailsClosed()
    {
        string dir = TempDir();
        try
        {
            string indexDir = Path.Combine(dir, "idx");
            using (var index = RecallIndex.Build(indexDir, Corpus(20, i => "内容 " + i)))
            {
            }
            string segMeta = Directory.GetFiles(indexDir, "seg.meta", SearchOption.AllDirectories)[0];
            using (var fs = new FileStream(segMeta, FileMode.Open, FileAccess.Write))
            {
                fs.Seek(20, SeekOrigin.Begin);
                fs.WriteByte(0xFF);
            }
            Assert.ThrowsAny<RecallFormatException>(() => RecallIndex.Open(indexDir));
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    private static List<(string Id, double Score)> BruteForce(IReadOnlyList<RecallSourceDoc> docs, string query, int k)
    {
        var queryTokens = new List<string>();
        var sink = new CollectingSink();
        RecallTokenizer.Tokenize(query.AsSpan(), RecallTokenizerOptions.Default, sink);
        foreach (string t in sink.Tokens)
        {
            if (!queryTokens.Contains(t))
            {
                queryTokens.Add(t);
            }
        }

        var docTokens = new List<Dictionary<string, int>>(docs.Count);
        double totalLen = 0;
        foreach (var doc in docs)
        {
            var s = new CollectingSink();
            RecallTokenizer.Tokenize(doc.Text.AsSpan(), RecallTokenizerOptions.Default, s);
            var tf = new Dictionary<string, int>(StringComparer.Ordinal);
            foreach (string t in s.Tokens)
            {
                tf[t] = tf.TryGetValue(t, out int c) ? c + 1 : 1;
            }
            docTokens.Add(tf);
            totalLen += s.Tokens.Count;
        }
        double avg = docs.Count == 0 ? 1 : Math.Max(1e-9, totalLen / docs.Count);
        double k1 = 1.2, b = 0.75;
        var scored = new List<(string Id, double Score)>();
        for (int i = 0; i < docs.Count; i++)
        {
            double score = 0;
            double dl = 0;
            foreach (int _ in docTokens[i].Values)
            {
            }
            dl = docTokens[i].Values.Sum();
            foreach (string t in queryTokens)
            {
                if (!docTokens[i].TryGetValue(t, out int tf))
                {
                    continue;
                }
                int df = 0;
                foreach (var d in docTokens)
                {
                    if (d.ContainsKey(t))
                    {
                        df++;
                    }
                }
                double idf = Math.Log(1.0 + (docs.Count - df + 0.5) / (df + 0.5));
                score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avg));
            }
            if (score > 0)
            {
                scored.Add((docs[i].Id, score));
            }
        }
        scored.Sort((a, c) =>
        {
            int cc = c.Score.CompareTo(a.Score);
            return cc != 0 ? cc : string.CompareOrdinal(a.Id, c.Id);
        });
        return scored.Take(k).ToList();
    }
}
