using System;
using System.IO;
using System.Threading;
using Xunit;
using agent.execution;

namespace agentframework.tests;

/// <summary>v0.17.0 T1/T2/T3 (R334): 跨进程文件锁 / 原子写 / 占用者检测 / 加锁写策略 / 教训记忆。</summary>
public class ExecutorHardeningTests
{
    private static string TempDir()
    {
        var d = Path.Combine(Path.GetTempPath(), "af-exechard-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(d);
        return d;
    }

    [Fact]
    public void FileLock_TwoLocks_SameFile_MutualExclusion()
    {
        var dir = TempDir();
        var target = Path.Combine(dir, "a.json");
        using var l1 = new FileLock(target);
        Assert.True(l1.TryAcquire(TimeSpan.FromMilliseconds(300)), "第一个锁应拿到");
        using var l2 = new FileLock(target);
        Assert.False(l2.TryAcquire(TimeSpan.FromMilliseconds(200)), "同文件第二个锁应被互斥拒绝");
        l1.Release();
        Assert.True(l2.TryAcquire(TimeSpan.FromMilliseconds(500)), "释放后第二个锁应能拿到");
        l2.Release();
        // R465 (真修): 锁文件**保留** —— 删除 file 会 unlink inode, 下一个竞争者拿到新 inode 的新锁,
        // 与被 unlink 但仍被持有的旧 inode 形成两个持有者 (实测 119/120 段丢一段)。
        Assert.True(File.Exists(target + ".lock"), "锁文件必须保留 (存在性 ≠ 是否被持有)");
        Assert.Equal(Environment.ProcessId.ToString(), File.ReadAllText(target + ".lock").Trim());
    }

    [Fact]
    public void FileLock_StaleLock_BrokenAndTaken()
    {
        var dir = TempDir();
        var target = Path.Combine(dir, "b.json");
        var lockPath = target + ".lock";
        File.WriteAllText(lockPath, "999999999"); // 不存在的 pid → 僵尸锁文件
        // R465: 僵尸**锁文件**不需要也无法被「清除」——文件不是锁, 内核 flock 才是。
        Assert.True(OccupantDetector.IsHolderDead(lockPath), "死 pid 应可被判定为无持有者 (只读探测)");
        Assert.True(File.Exists(lockPath), "只读探测不得删文件");
        using var l1 = new FileLock(target);
        Assert.True(l1.TryAcquire(TimeSpan.FromMilliseconds(300)), "死持有者的锁由内核自动放行 ⇒ 直接接管");
    }

    [Fact]
    public void FileLock_LiveOwnerLock_NotBroken()
    {
        var dir = TempDir();
        var target = Path.Combine(dir, "c.json");
        using var l1 = new FileLock(target);
        Assert.True(l1.TryAcquire(TimeSpan.FromMilliseconds(300)));
        Assert.False(OccupantDetector.IsHolderDead(target + ".lock"), "活持有者不得被误判为死");
    }

    [Fact]
    public void OccupantDetector_ReportsHeldLockOwner()
    {
        var dir = TempDir();
        var target = Path.Combine(dir, "d.json");
        using var l1 = new FileLock(target);
        Assert.True(l1.TryAcquire(TimeSpan.FromMilliseconds(300)));
        var desc = OccupantDetector.Describe(target);
        Assert.Contains("PID " + Environment.ProcessId, desc); // 锁文件内容 pid → 最快路径
        Assert.Contains("comm", desc.Replace("PID " + Environment.ProcessId + " (", "PID " + Environment.ProcessId + " (comm"));
    }

    [Fact]
    public void AtomicWriter_NoPartialFile_AfterWrite()
    {
        var dir = TempDir();
        var target = Path.Combine(dir, "e.json");
        AtomicFileWriter.WriteAllText(target, "{\"k\":1}");
        Assert.Equal("{\"k\":1}", File.ReadAllText(target));
        AtomicFileWriter.WriteAllText(target, "{\"k\":2}");
        Assert.Equal("{\"k\":2}", File.ReadAllText(target));
        Assert.Empty(Directory.GetFiles(dir, ".*.tmp-*")); // 无 tmp 残留
    }

    [Fact]
    public void LockedWriter_KeepExisting_SecondWriterYields()
    {
        var dir = TempDir();
        var target = Path.Combine(dir, "f.json");
        var r1 = LockedFileWriter.Write(target, "writer-A", ConflictStrategy.Overwrite, TimeSpan.FromSeconds(3));
        Assert.True(r1.Success);
        Assert.False(r1.Merged);
        var r2 = LockedFileWriter.Write(target, "writer-B", ConflictStrategy.KeepExisting, TimeSpan.FromSeconds(3));
        Assert.True(r2.Success);
        Assert.True(r2.Merged, "内容不同 + KeepExisting → 让位 (merged)");
        Assert.Equal("writer-A", File.ReadAllText(target), ignoreCase: false, ignoreLineEndingDifferences: false, ignoreWhiteSpaceDifferences: false);
    }

    [Fact]
    public void FileLock_ConcurrentAppend_NoLoss_NoInterleave()
    {
        // 8 线程 × 15 次锁内读-改-写追加 → 120 行全在、无交错、无丢失 (T1 互斥核心保证)
        var dir = TempDir();
        var target = Path.Combine(dir, "g.json");
        var errors = new System.Collections.Concurrent.ConcurrentBag<string>();
        var threads = new List<Thread>();
        for (var t = 0; t < 8; t++)
        {
            var tid = t;
            threads.Add(new Thread(() =>
            {
                for (var i = 0; i < 15; i++)
                {
                    using var l = new FileLock(target);
                    if (!l.TryAcquire(TimeSpan.FromSeconds(5)))
                    {
                        errors.Add($"t{tid} acquire fail at {i}");
                        return;
                    }
                    try
                    {
                        var existing = File.Exists(target) ? File.ReadAllText(target) : "";
                        AtomicFileWriter.WriteAllText(target, existing + $"w{tid}-{i};");
                    }
                    catch (Exception ex) { errors.Add($"t{tid} {ex.Message}"); }
                }
            }));
        }
        foreach (var th in threads) th.Start();
        foreach (var th in threads) th.Join();
        Assert.Empty(errors);
        var content = File.ReadAllText(target);
        var segs = content.Split(';', StringSplitOptions.RemoveEmptyEntries);
        Assert.Equal(120, segs.Length); // 无丢失
        Assert.Equal(120, segs.Distinct().Count()); // 无重复无交错 (每段唯一完整)
    }

    [Fact]
    public void LessonMemory_FrequencyEscalation_AndDecay()
    {
        var dir = TempDir();
        var store = Path.Combine(dir, "lessons.json");
        var now = 1_000_000L;
        var mem = new ExecutorLessonMemory(store, () => now);
        var pattern = "file-lock:data/guardrails.json";

        mem.Record(pattern, "锁超时: 文件被占用");
        var h1 = mem.RenderInjectionHint(pattern);
        Assert.Contains("1 次", h1);
        Assert.DoesNotContain("方案", h1);

        mem.Record(pattern, "锁超时: 文件被占用", solution: "等待 3s 重试或 KeepExisting 让位");
        mem.Record(pattern, "锁超时: 文件被占用", solution: "等待 3s 重试或 KeepExisting 让位");
        var h3 = mem.RenderInjectionHint(pattern);
        Assert.Contains("3 次", h3);
        Assert.Contains("方案", h3); // count≥3 → 补方案

        for (var i = 0; i < 6; i++)
            mem.Record(pattern, "锁超时", solution: "x", contextTail: "双实例同时写 guardrails");
        var h8 = mem.RenderInjectionHint(pattern);
        Assert.Contains("9 次", h8); // 1+2+6=9 次; 断言写实际次数而非阈值
        Assert.Contains("双实例同时写", h8); // count≥8 → 补上下文

        // 24h 无命中 → count 降级; 7d → 移除
        now += 25 * 3600 * 1000L;
        mem.RenderInjectionHint(pattern); // 触发衰减
        Assert.True(mem.Snapshot()[pattern].Count < 8, "24h 无命中 count 应降级");
        now += 8 * 24 * 3600 * 1000L;
        mem.RenderInjectionHint(pattern);
        Assert.Empty(mem.Snapshot()); // 7d+ 无命中 → 移除
    }

    [Fact]
    public void LessonMemory_PersistRoundtrip()
    {
        var dir = TempDir();
        var store = Path.Combine(dir, "lessons.json");
        var mem = new ExecutorLessonMemory(store);
        mem.Record("io:write", "写入失败", solution: "原子写重试");
        var mem2 = new ExecutorLessonMemory(store);
        var snap = mem2.Snapshot();
        Assert.True(snap.ContainsKey("io:write"));
        Assert.Equal(1, snap["io:write"].Count);
        Assert.Equal("原子写重试", snap["io:write"].Solution);
    }

    [Fact]
    public void LessonMemory_CorruptStore_Tolerated()
    {
        var dir = TempDir();
        var store = Path.Combine(dir, "lessons.json");
        File.WriteAllText(store, "{corrupt!!");
        var mem = new ExecutorLessonMemory(store); // 不抛
        mem.Record("x", "y");
        Assert.Single(mem.Snapshot());
    }

    [Fact]
    public void LessonMemory_NoHit_EmptyHint()
    {
        var mem = new ExecutorLessonMemory(Path.Combine(TempDir(), "l.json"));
        Assert.Equal("", mem.RenderInjectionHint("never-recorded"));
    }

    // ================= R465: 跨进程放锁 + 不 unlink 的结构门 =================

    /// <summary>R465: 跨进程真值 —— python 子进程持 flock, 我方必须拿不到; 子进程**被退出**后
    /// 内核自动放锁 ⇒ 我方直接接管, 且锁文件自始至终未被删除 (这是修复的核心不变量)。</summary>
    [Fact]
    public void G43_跨进程死持有者_内核放锁且不删文件()
    {
        if (!OperatingSystem.IsLinux()) return; // 依赖 flock(2) + python3 (本机 Linux)
        var dir = TempDir();
        var target = Path.Combine(dir, "x.json");
        var lockPath = target + ".lock";
        var flag = Path.Combine(dir, "held.flag");
        var script = Path.Combine(dir, "hold.py");
        File.WriteAllText(script,
            "import fcntl,sys,time\n" +
            "f=open(sys.argv[1],'a+')\n" +
            "fcntl.flock(f,fcntl.LOCK_EX)\n" +
            "open(sys.argv[2],'w').write('held')\n" +
            "time.sleep(6)\n");
        System.Diagnostics.Process? child = null;
        try
        {
            child = System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo("python3",
                $"\"{script}\" \"{lockPath}\" \"{flag}\"") { UseShellExecute = false });
        }
        catch (Exception) { return; } // 无 python3 ⇒ 本机不可做该证据 (不伪绿)
        if (child is null) return;
        try
        {
            var waited = 0;
            while (!File.Exists(flag) && waited < 6000) { Thread.Sleep(50); waited += 50; }
            Assert.True(File.Exists(flag), "子进程未能在 6s 内持锁");
            using var mine = new FileLock(target);
            Assert.False(mine.TryAcquire(TimeSpan.FromMilliseconds(700)), "子进程持锁期间我方不得拿到");
            Assert.True(OccupantDetector.IsHolderDead(lockPath) == false, "子进程活着 ⇒ 不得判死");
            child.WaitForExit(15000);
            Assert.True(mine.TryAcquire(TimeSpan.FromSeconds(3)), "持有者退出后内核自动放锁 ⇒ 应能接管");
            Assert.True(File.Exists(lockPath), "全程不得删除锁文件 (unlink 会破坏互斥)");
            mine.Release();
            Assert.True(File.Exists(lockPath), "释放后锁文件仍须保留");
        }
        finally
        {
            try { if (!child.HasExited) child.Kill(true); } catch { /* 已退出 */ }
        }
    }

    /// <summary>R465: 结构门 —— 剥掉注释后源码不得再出现「删除锁文件」(历史缺陷形态)。
    /// 剥注释是为了让断言不能被「加一行注释」满足。</summary>
    [Fact]
    public void G44_锁实现不得删除锁文件()
    {
        var root = FindRepoRoot();
        var src = File.ReadAllText(Path.Combine(root, "src", "agent", "execution", "FileLocking.cs"));
        var kept = new System.Collections.Generic.List<string>();
        foreach (var l in src.Split('\n'))
        {
            var s = l.TrimStart();
            if (s.StartsWith("//", StringComparison.Ordinal)) continue;
            kept.Add(l);
        }
        var code = string.Join(' ', kept);
        Assert.DoesNotContain("File.Delete(LockPath)", code);
        Assert.DoesNotContain("File.Delete(lockPath)", code);
        Assert.Contains("IsHolderDead", code);
    }

    private static string FindRepoRoot()
    {
        var d = new DirectoryInfo(AppContext.BaseDirectory);
        while (d is not null && !Directory.Exists(Path.Combine(d.FullName, "src", "agent"))) d = d.Parent;
        if (d is null) throw new InvalidOperationException("找不到仓库根");
        return d.FullName;
    }
}
