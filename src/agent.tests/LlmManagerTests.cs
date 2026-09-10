using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Xunit;
using agent.llamalocal;
using agent.llmservice;

namespace agentframework.tests;

/// <summary>v0.20.0 P3 (R343, 用户钦定策略): llm-manager — 轻量编排进程 (0 模型)。
/// 覆盖: 转发 / lazy spawn / 崩溃重拉 / 卸载判定 (纯函数矩阵) / 卸载=kill worker 真进程 / 双启保护。</summary>
public class LlmManagerTests
{
    private static string TempSock() => $"/tmp/af-mgrtest-{Guid.NewGuid():N}.sock";

    private static Task<float[]> FakeEmbed(string text, CancellationToken ct)
        => Task.FromResult(text.Select(c => (float)c).Take(16).Concat(new float[16]).Take(16).ToArray());

    private static LlmServiceHost StartFakeWorker(string workerSock)
    {
        var h = new LlmServiceHost(FakeEmbed, _ => { }, workerSock);
        var deadline = DateTime.UtcNow.AddSeconds(5);
        while (DateTime.UtcNow < deadline)
        {
            if (File.Exists(workerSock) && RemoteEmbedder.Probe(workerSock)) return h;
            Thread.Sleep(30);
        }
        throw new TimeoutException("fake worker 未就绪");
    }

    private static Process StartSleepProc() => Process.Start("sleep", "300");

    private static LlmManagerHost StartManager(string sock, Func<Process?>? spawner = null,
        Func<long>? mem = null, Func<int>? cli = null, long floor = 512)
    {
        var m = new LlmManagerHost(_ => { }, sock, memAvailableMb: mem, activeCliCount: cli,
            memFloorMb: floor, unloadCheckMs: 3_600_000, workerSpawner: spawner);
        m.Start();
        var deadline = DateTime.UtcNow.AddSeconds(5);
        while (DateTime.UtcNow < deadline)
        {
            if (File.Exists(sock) && RemoteEmbedder.Probe(sock)) return m;
            Thread.Sleep(30);
        }
        throw new TimeoutException("manager 未就绪");
    }

    // ---- 卸载判定 (纯函数, 无 socket 依赖) ----

    [Fact]
    public void ShouldUnload_Matrix()
    {
        // 资源紧张 + 无 CLI + 无进行中请求 + worker 在 → 卸载
        Assert.True(LlmManagerHost.ShouldUnload(100, 512, 0, 0, true));
        // 内存充足 → 常驻
        Assert.False(LlmManagerHost.ShouldUnload(4096, 512, 0, 0, true));
        // 仍有 CLI 实例 → 不卸
        Assert.False(LlmManagerHost.ShouldUnload(100, 512, 2, 0, true));
        // 有请求进行中 → 不卸
        Assert.False(LlmManagerHost.ShouldUnload(100, 512, 0, 1, true));
        // worker 不在 → 无事可做
        Assert.False(LlmManagerHost.ShouldUnload(100, 512, 0, 0, false));
        // 读不到内存 (<=0) → 保守不卸
        Assert.False(LlmManagerHost.ShouldUnload(-1, 512, 0, 0, true));
        // 边界: 恰好等于 floor → 常驻 (严格小于才卸)
        Assert.False(LlmManagerHost.ShouldUnload(512, 512, 0, 0, true));
    }

    [Fact]
    public void MaybeUnload_KillsWorker_RealProcess()
    {
        var sock = TempSock();
        long memAvail = 4096; int cliCount = 5;
        using var mgr = StartManager(sock, spawner: () =>
        {
            StartFakeWorker(sock + LlmManagerHost.WorkerSockSuffix);
            return StartSleepProc();
        }, mem: () => memAvail, cli: () => cliCount);
        using var c = new RemoteEmbedder(sock);
        c.EmbedAsync("唤醒 worker").GetAwaiter().GetResult();
        Assert.True(mgr.WorkerRunning, $"DIAG spawns={mgr.WorkerSpawnCount} probeWorker={RemoteEmbedder.Probe(mgr.WorkerSockPath)} sockExists={File.Exists(mgr.WorkerSockPath)}");

        // 内存充足 → 不卸载
        Assert.False(mgr.MaybeUnload());
        Assert.True(mgr.WorkerRunning);
        // 资源紧张 + 有 CLI 实例 → 不卸载
        memAvail = 100;
        Assert.False(mgr.MaybeUnload());
        Assert.True(mgr.WorkerRunning);
        // 资源紧张 + 无 CLI 实例 → 卸载 (kill worker 进程)
        cliCount = 0;
        Assert.True(mgr.MaybeUnload());
        Assert.False(mgr.WorkerRunning);
        Assert.True(mgr.WorkerUnloadCount >= 1);
        Assert.False(LlmManagerHost.ShouldUnload(100, 512, 0, 0, mgr.WorkerRunning || RemoteEmbedder.Probe(mgr.WorkerSockPath)));
    }

    // ---- lazy / 崩溃重拉 / 转发 ----

    [Fact]
    public async Task Forward_ToExistingWorker()
    {
        var sock = TempSock();
        using var mgr = StartManager(sock);
        using var worker = StartFakeWorker(mgr.WorkerSockPath);
        using var c = new RemoteEmbedder(sock);
        var v = await c.EmbedAsync("转发测试");
        Assert.Equal(16, v.Length);
        Assert.Equal((float)'转', v[0]);
        Assert.True(mgr.RequestCount >= 1);
    }

    [Fact]
    public async Task LazySpawn_OnFirstUse_ThenReuse()
    {
        var sock = TempSock();
        var spawnCount = 0;
        using var mgr = StartManager(sock, spawner: () =>
        {
            Interlocked.Increment(ref spawnCount);
            StartFakeWorker(sock + LlmManagerHost.WorkerSockSuffix);
            return StartSleepProc();
        });
        Assert.Equal(0, spawnCount);        // manager 启动 0 模型占用
        Assert.False(mgr.WorkerRunning);
        using var c = new RemoteEmbedder(sock);
        var v1 = await c.EmbedAsync("首次使用");
        Assert.Equal(1, spawnCount);        // lazy: 首请求才 spawn
        Assert.True(mgr.WorkerRunning);
        var v2 = await c.EmbedAsync("复用");
        Assert.Equal(1, spawnCount);        // 复用现有 worker
        Assert.Equal((float)'首', v1[0]);
        Assert.Equal((float)'复', v2[0]);
    }

    [Fact]
    public async Task WorkerCrash_NextRequest_Respawns()
    {
        var sock = TempSock();
        var spawnCount = 0;
        using var mgr = StartManager(sock, spawner: () =>
        {
            Interlocked.Increment(ref spawnCount);
            StartFakeWorker(sock + LlmManagerHost.WorkerSockSuffix);
            return StartSleepProc();
        });
        using var c = new RemoteEmbedder(sock);
        await c.EmbedAsync("崩溃前");
        Assert.Equal(1, spawnCount);
        mgr.KillWorker("测试: 模拟 worker 崩溃/被杀");   // 用户策略: 卸载=杀 worker
        Assert.False(mgr.WorkerRunning);
        var v2 = await c.EmbedAsync("崩溃后");          // 下次请求自动重拉
        Assert.Equal(2, spawnCount);
        Assert.Equal((float)'崩', v2[0]);
    }

    [Fact]
    public void Manager_DoubleStart_Rejected()
    {
        var sock = TempSock();
        using var m1 = StartManager(sock);
        var ex = Assert.Throws<InvalidOperationException>(() =>
        {
            using var m2 = new LlmManagerHost(_ => { }, sock);
            m2.Start();
        });
        Assert.Contains("已在运行", ex.Message);
    }

    [Fact]
    public void MemAvailable_Reader_Sane()
    {
        Assert.True(LlmManagerHost.ReadMemAvailableMb() > 0);
    }
}
