// R480: 独立文本召回模块 —— 行为测试 (判据: 与独立暴力实现一致 / 极小常驻 / 增量正确 / 损坏 fail-closed)。
using System.Text;
using agent.recall;
using Xunit;

namespace agent.recall.tests;

public sealed class RecallIncrementalTests
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
    public void Update_AddsModifiesDeletes_AndPrunesUnchangedDirs()
    {
        string root = Path.Combine(Path.GetTempPath(), "recall_upd_" + Guid.NewGuid().ToString("N"));
        string indexDir = Path.Combine(root, "index");
        Directory.CreateDirectory(Path.Combine(root, "vault", "a"));
        Directory.CreateDirectory(Path.Combine(root, "vault", "b"));
        try
        {
            File.WriteAllText(Path.Combine(root, "vault", "a", "one.txt"), "第一次写入 包含 钾 关键字");
            File.WriteAllText(Path.Combine(root, "vault", "b", "two.txt"), "乙 文档 内容");
            string scanRoot = Path.Combine(root, "vault");
            var options = new RecallUpdateOptions
            {
                Scan = new RecallScanOptions { SkipDirectoryNames = new[] { "index" } },
            };
            var first = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.Equal(2, first.Added);
            Assert.True(first.WroteIndex);

            using (var index = RecallIndex.Open(indexDir))
            {
                Assert.Equal("vault/a/one.txt", index.Search("钾", 3)[0].Path);
            }

            var idle = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.False(idle.Dirty);
            Assert.False(idle.WroteIndex);
            Assert.True(idle.DirsPruned >= 1);

            File.WriteAllText(Path.Combine(root, "vault", "a", "one.txt"), "第二次写入 包含 铷 关键字 追加内容");
            File.WriteAllText(Path.Combine(root, "vault", "b", "three.txt"), "丙 文档 内容");
            var second = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.Equal(1, second.Modified);
            Assert.Equal(1, second.Added);
            using (var index = RecallIndex.Open(indexDir))
            {
                Assert.Equal("vault/a/one.txt", index.Search("铷", 3)[0].Path);
                Assert.Empty(index.Search("钾", 3));
                Assert.Equal("vault/b/three.txt", index.Search("丙", 3)[0].Path);
            }

            File.Delete(Path.Combine(root, "vault", "b", "three.txt"));
            var third = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.Equal(1, third.Deleted);
            using (var index = RecallIndex.Open(indexDir))
            {
                Assert.Empty(index.Search("丙", 3));
                Assert.Equal("vault/a/one.txt", index.Search("铷", 3)[0].Path);
            }
        }
        finally
        {
            Directory.Delete(root, true);
        }
    }

    [Fact]
    public void Update_AlternatingVerify_CatchesSameSizeContentRewrite()
    {
        // §D9 回归: 目录 mtime 对「纯内容改写」不可见 ⇒ 需要交替全量核验。本轮刻意用**等字节长度**改写
        // (size 不变, 只有文件 mtime 变) 逼出「文件级 (size, mtime) 比对必须真的发生过」这一条。
        string root = Path.Combine(Path.GetTempPath(), "recall_upd_d9_" + Guid.NewGuid().ToString("N"));
        string indexDir = Path.Combine(root, "index");
        Directory.CreateDirectory(Path.Combine(root, "vault", "d"));
        try
        {
            string target = Path.Combine(root, "vault", "d", "note.txt");
            string before = "前缀 钾 内容 尾部填充";
            string after = "前缀 铷 内容 尾部填充";
            Assert.Equal(System.Text.Encoding.UTF8.GetByteCount(before), System.Text.Encoding.UTF8.GetByteCount(after));
            File.WriteAllText(target, before);

            string scanRoot = Path.Combine(root, "vault");
            var options = new RecallUpdateOptions
            {
                Scan = new RecallScanOptions { SkipDirectoryNames = new[] { "index" } },
            };

            var first = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.Equal(1, first.Added);
            Assert.False(first.VerifiedAllDirs);
            Assert.False(first.PrevScanPruned);

            var idle = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.False(idle.Dirty);
            Assert.True(idle.DirsPruned >= 1);
            Assert.False(idle.VerifiedAllDirs);

            File.WriteAllText(target, after);
            var second = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.True(second.PrevScanPruned);
            Assert.True(second.VerifiedAllDirs);   // 上轮剪过 ⇒ 本轮强制核验
            Assert.Equal(0, second.DirsPruned);    // 核验轮该计数恒 0 (计划 §7 已注明)
            Assert.Equal(1, second.Modified);      // size 相同, 只能靠文件级 mtime 捕获
            using (var index = RecallIndex.Open(indexDir))
            {
                Assert.Equal("vault/d/note.txt", index.Search("铷", 3)[0].Path);
                Assert.Empty(index.Search("钾", 3));
            }

            var idle2 = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.False(idle2.Dirty);
            Assert.True(idle2.DirsPruned >= 1);    // 核验轮之后恢复剪枝 (交替)
            Assert.False(idle2.VerifiedAllDirs);
        }
        finally
        {
            Directory.Delete(root, true);
        }
    }

    [Fact]
    public void Links_In_Content_Are_Extracted_Stored_And_Returned()
    {
        string dir = TempDir();
        try
        {
            var docs = Corpus(3, i => i == 1
                ? "设计文档 参见 [索引设计](docs/plans/v0.96.0-r480-recall-module.md) 与 https://example.com/spec?a=1 以及 src/agent.recall/RecallIndex.cs"
                : "无关 内容 " + i);
            using var index = RecallIndex.Build(dir, docs);
            var hits = index.Search("索引设计", 3);
            Assert.NotEmpty(hits);
            Assert.Contains("docs/plans/v0.96.0-r480-recall-module.md", hits[0].Links);
            Assert.Contains("https://example.com/spec?a=1", hits[0].Links);
            Assert.Contains("src/agent.recall/RecallIndex.cs", hits[0].Links);
            // 地址也可被直接召回 (产出物自带地址 ⇒ 无需分类)
            Assert.Equal("doc-1", index.Search("RecallIndex.cs", 3)[0].Id);
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    [Fact]
    public void Relative_References_Resolve_Against_Referrer_Directory()
    {
        var options = new RecallLinkOptions();
        var sink = new List<string>();
        int n = RecallLinkExtractor.Extract(
            "见 [B](../reports/b.md) 与 [C](./c.md) 还有 src/x.cs 以及 https://example.com/p".AsSpan(),
            options,
            sink,
            "docs/plans/a.md");
        Assert.Equal(4, n);
        Assert.Contains("docs/reports/b.md", sink); // ../ ⇒ 按引用方目录回退一层
        Assert.Contains("docs/plans/c.md", sink);   // ./ ⇒ 按引用方目录展开
        Assert.Contains("src/x.cs", sink);          // 根相对 ⇒ 原样保留 (主力通路, 不得改写)
        Assert.Contains("https://example.com/p", sink);

        // 越根 fail-closed: 原值返回, 不猜目标
        var escaped = new List<string>();
        RecallLinkExtractor.Extract("x [E](../../../e.md)".AsSpan(), options, escaped, "a.md");
        Assert.Contains("../../../e.md", escaped);
    }

    [Fact]
    public void TaskState_Is_Durable_And_Feeds_Recall()
    {
        string root = TempDir();
        try
        {
            string indexDir = Path.Combine(root, "index");
            var store = new RecallTaskStateStore(root);
            store.Append("T-1", new TaskStateEvent
            {
                Ts = 1,
                Kind = "artifact",
                Text = "产出 报告",
                Artifacts = new[] { "docs/reports/r480.md" },
                Links = new[] { "docs/plans/v0.96.0-r480-recall-module.md" },
            });
            // 新实例读取 = 不依赖任何进程内/上下文状态
            var state = new RecallTaskStateStore(root).Load("T-1");
            Assert.Equal(1, state.EventCount);
            Assert.Equal("task://T-1", state.Address);
            Assert.Contains("docs/reports/r480.md", state.Artifacts);

            using (var builder = RecallIndexBuilder.Create(indexDir, new RecallWriteOptions()))
            {
                Assert.NotNull(builder);
            }
            using (var empty = RecallIndex.Open(indexDir))
            {
                Assert.Equal(0, empty.DocCount);
            }
            Assert.Equal(1, store.SyncToIndex("T-1", indexDir));
            using (var index = RecallIndex.Open(indexDir))
            {
                var hits = index.Search("报告", 3);
                Assert.NotEmpty(hits);
                Assert.Contains("task://T-1", hits[0].Path);
            }
        }
        finally
        {
            Directory.Delete(root, true);
        }
    }

    [Fact]
    public void Recall_Results_Feed_Back_Into_Task_State()
    {
        string root = TempDir();
        try
        {
            var docs = Corpus(2, i => "甲 " + i);
            using var index = RecallIndex.Build(Path.Combine(root, "index"), docs);
            var hits = index.Search("甲", 3);
            var store = new RecallTaskStateStore(root);
            store.RecordRecall("T-2", "甲", hits);
            var state = store.Load("T-2");
            Assert.Equal(1, state.EventCount);
            Assert.Contains(state.Artifacts, a => a.EndsWith("file-0", StringComparison.Ordinal));
        }
        finally
        {
            Directory.Delete(root, true);
        }
    }
}
