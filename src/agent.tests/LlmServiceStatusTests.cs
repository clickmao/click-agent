using System;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Xunit;
using agent.llamalocal;
using agent.llmservice;
using agent.registry;

namespace agentframework.tests;

/// <summary>v0.20.2 (R345): /llm-service 可观测性 — 指令路由双门 (Known+switch, 历史缺陷防护) + 状态查询。</summary>
public class LlmServiceStatusTests
{
    private static string TempSock() => $"/tmp/af-stat-{Guid.NewGuid():N}.sock";

    private static Task<float[]> FakeEmbed(string text, CancellationToken ct)
        => Task.FromResult(text.Select(c => (float)c).Take(16).Concat(new float[16]).Take(16).ToArray());

    [Fact]
    public void Command_IsKnownAndRouted()
    {
        // 双门校验 (历史缺陷: Known 加了但 switch 臂缺 → 落 NotCommand 走 LLM)
        var r = LocalCommandRouter.TryRoute("/llm-service");
        Assert.True(r.Handled, "/llm-service 应被本地指令拦截");
        Assert.Equal("llm-service", r.Command);
    }

    [Fact]
    public void Query_Offline_NoThrow()
    {
        var sock = TempSock(); // 无 manager
        var st = LlmServiceStatus.Query(sock);
        Assert.False(st.Online);
        var text = st.Render(sock);
        Assert.Contains("未运行", text);
        Assert.Contains("--llm-manager", text); // 提示启动方式
    }

    [Fact]
    public async Task Query_Online_FieldsSane()
    {
        var sock = TempSock();
        using var mgr = new LlmManagerHost(_ => { }, sock, memFloorMb: 512, unloadCheckMs: 3_600_000);
        mgr.Start();
        // 等 manager 就绪
        var deadline = DateTime.UtcNow.AddSeconds(5);
        while (DateTime.UtcNow < deadline && !RemoteEmbedder.Probe(sock)) Thread.Sleep(30);

        var st = LlmServiceStatus.Query(sock);
        Assert.True(st.Online);
        Assert.Equal(Environment.ProcessId, st.ManagerPid);
        Assert.False(st.WorkerRunning);       // lazy: 未使用 → worker 未拉起
        Assert.Equal(0, st.Spawns);
        Assert.Equal(512, st.MemFloorMb);
        var text = st.Render(sock);
        Assert.Contains("llm-manager", text);
        Assert.Contains("lazy", text);
        await Task.CompletedTask;
    }

    [Fact]
    public void Query_AfterWorkerSpawn_ReportsWorker()
    {
        var sock = TempSock();
        using var mgr = new LlmManagerHost(_ => { }, sock, unloadCheckMs: 3_600_000, workerSpawner: () =>
        {
            // 模拟 worker (真服务 sock, 无真进程 — worker_pid 读 pid 文件)
            var h = new LlmServiceHost(FakeEmbed, _ => { }, sock + LlmManagerHost.WorkerSockSuffix);
            var dl = DateTime.UtcNow.AddSeconds(5);
            while (DateTime.UtcNow < dl && !RemoteEmbedder.Probe(sock + LlmManagerHost.WorkerSockSuffix)) Thread.Sleep(30);
            return System.Diagnostics.Process.Start("sleep", "300");
        });
        mgr.Start();
        var deadline = DateTime.UtcNow.AddSeconds(5);
        while (DateTime.UtcNow < deadline && !RemoteEmbedder.Probe(sock)) Thread.Sleep(30);

        Task.Run(() => mgr.EnsureWorkerAsync()).Wait();
        var st = LlmServiceStatus.Query(sock);
        Assert.True(st.Online);
        Assert.True(st.WorkerRunning);
        Assert.True(st.WorkerPid > 0, $"worker_pid 应 > 0, 实际 {st.WorkerPid}");
        var text = st.Render(sock);
        Assert.Contains("运行中", text);
    }
}
