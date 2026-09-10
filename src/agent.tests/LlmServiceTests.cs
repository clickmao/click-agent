using System;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Xunit;
using agent.llamalocal;
using agent.llmservice;

namespace agentframework.tests;

/// <summary>v0.20.0 P1/P2 (R342): LLM service daemon — 协议往返 / 探测 / 多客户端并发 / 断线重建 /
/// 用户三问: 双 CLI 并发拉起只 spawn 一次 / 崩溃自动恢复 / 反复崩溃熔断 / daemon 双启保护。</summary>
public class LlmServiceTests
{
    private static string TempSock()
        => $"/tmp/af-llmtest-{Guid.NewGuid():N}.sock";

    private static Task<float[]> FakeEmbed(string text, CancellationToken ct)
        => Task.FromResult(text.Select(c => (float)c).Take(16).Concat(new float[16]).Take(16).ToArray());

    private static LlmServiceHost StartHost(string sock, Action<string>? log = null)
    {
        var host = new LlmServiceHost(FakeEmbed, log ?? (_ => { }), sock);
        var deadline = DateTime.UtcNow.AddSeconds(5);
        while (DateTime.UtcNow < deadline)
        {
            if (File.Exists(sock) && RemoteEmbedder.Probe(sock)) return host;
            Thread.Sleep(30);
        }
        throw new TimeoutException($"服务未就绪: {sock}");
    }

    // ---- P1: 协议 ----

    [Fact]
    public async Task Embed_RoundTrip_VectorsMatch()
    {
        var sock = TempSock();
        using var host = StartHost(sock);
        using var client = new RemoteEmbedder(sock);
        var v1 = await client.EmbedAsync("苹果");
        var v2 = await client.EmbedAsync("苹果");
        Assert.Equal(16, v1.Length);
        Assert.Equal(v1, v2);
        Assert.Equal((float)'苹', v1[0]);
        Assert.Equal((float)'果', v1[1]);
        Assert.True(host.RequestCount >= 2, $"请求计数应≥2, 实际 {host.RequestCount}");
    }

    [Fact]
    public void Probe_OnlineThenOffline()
    {
        var sock = TempSock();
        using var host = StartHost(sock);
        Assert.True(RemoteEmbedder.Probe(sock));
        host.Dispose();
        Assert.False(RemoteEmbedder.Probe(sock));
    }

    [Fact]
    public async Task MultipleClients_Concurrent_AllServe()
    {
        var sock = TempSock();
        using var host = StartHost(sock);
        var tasks = Enumerable.Range(0, 5).Select(async i =>
        {
            using var c = new RemoteEmbedder(sock);
            var v = await c.EmbedAsync($"text-{i}-数据");
            return v[0] == (float)'t' ? i : -1;
        });
        var results = await Task.WhenAll(tasks);
        Assert.All(results, r => Assert.True(r >= 0));
    }

    [Fact]
    public async Task Reconnect_AfterServiceRestart()
    {
        var sock = TempSock();
        using (var host1 = StartHost(sock))
        {
            using var client = new RemoteEmbedder(sock);
            var v = await client.EmbedAsync("before-restart");
            Assert.NotEmpty(v);
        }
        // 服务已停 → EmbedAsync 探活失败 → EnsureServiceAsync 自动拉起 (spawnFactory 内起真 host)
        using (var client2 = new RemoteEmbedder(sock, () =>
        {
            _ = StartHost(sock); // 模拟 daemon spawn (同进程真服务)
            return null;
        }))
        {
            var v2 = await client2.EmbedAsync("after-restart");
            Assert.Equal((float)'a', v2[0]);
        }
    }

    // ---- P2: 用户三问 ----

    [Fact]
    public async Task ConcurrentClients_SpawnOnce()
    {
        // 双 CLI 同时 EnsureServiceAsync: pid CreateNew 原子抢占 → 只有一个执行 spawn
        var sock = TempSock();
        var spawnCount = 0;
        Func<string?> fakeSpawn = () =>
        {
            Interlocked.Increment(ref spawnCount);
            _ = StartHost(sock);
            return null;
        };
        var clients = Enumerable.Range(0, 8).Select(_ => new RemoteEmbedder(sock, fakeSpawn)).ToArray();
        try
        {
            await Task.WhenAll(clients.Select(c => c.EnsureServiceAsync()));
            Assert.Equal(1, spawnCount); // 并发 8 个只 spawn 一次
            Assert.True(RemoteEmbedder.Probe(sock));
        }
        finally
        {
            foreach (var c in clients) c.Dispose();
        }
    }

    [Fact]
    public async Task Crash_ThenAutoRecovery()
    {
        // 崩溃场景: daemon 死 (dispose 模拟, 保留 .pid 残留?) — 真崩溃 (kill -9) pid 残留;
        // 这里 dispose 会清 pid/sock → 等价"干净停止", 客户端应能自动拉起
        var sock = TempSock();
        using (var host1 = StartHost(sock))
        {
            using var client = new RemoteEmbedder(sock);
            var v = await client.EmbedAsync("healthy");
            Assert.Equal((float)'h', v[0]);
        } // daemon "崩溃/停止"
        Assert.False(RemoteEmbedder.Probe(sock));

        // 新客户端: 探活失败 → 自动拉起 → 恢复 (无需手动重启 daemon)
        using var client2 = new RemoteEmbedder(sock, () =>
        {
            _ = StartHost(sock);
            return null;
        });
        var v2 = await client2.EmbedAsync("recovered");
        Assert.Equal((float)'r', v2[0]);
    }

    [Fact]
    public async Task RepeatedCrashes_CircuitBreaks()
    {
        // 反复崩溃 (内存/显存不足): 窗口内 ≥3 次 → 熔断不再 spawn, 抛明确错误
        var sock = TempSock();
        // 预置 3 次重启记录 (窗口内)
        File.WriteAllText(sock + ".restarts",
            "{\"ts\":" + DateTimeOffset.UtcNow.ToUnixTimeSeconds() + ",\"count\":3}");
        var spawnCount = 0;
        using var client = new RemoteEmbedder(sock, () => { Interlocked.Increment(ref spawnCount); return null; });
        var ex = await Assert.ThrowsAsync<IOException>(() => client.EnsureServiceAsync());
        Assert.Contains("熔断", ex.Message);
        Assert.Equal(0, spawnCount); // 熔断: 零 spawn
    }

    [Fact]
    public void Daemon_DoubleStart_Rejected()
    {
        // daemon 侧双启保护: 已有实例 (pid 活) → 第二个 LlmServiceHost 构造抛
        var sock = TempSock();
        using var host1 = StartHost(sock);
        var ex = Assert.Throws<InvalidOperationException>(() =>
        {
            using var host2 = new LlmServiceHost(FakeEmbed, _ => { }, sock);
        });
        Assert.Contains("已在运行", ex.Message);
    }

    [Fact]
    public void StalePid_Overwritten()
    {
        // 崩溃残留 (kill -9): pid 文件在但进程死 → 新实例覆盖启动成功
        var sock = TempSock();
        File.WriteAllText(sock + ".pid", "999999"); // 死 pid
        using var host = StartHost(sock);           // 应能覆盖 stale pid 启动
        Assert.True(RemoteEmbedder.Probe(sock));
        Assert.True(LlmServiceHost.TryReadPid(sock + ".pid", out var pid));
        Assert.Equal(Environment.ProcessId, pid);
    }
}
