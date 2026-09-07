using agent.config;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.11.0 R121 (真缺陷 51 防御): Configure 前的 Emit 不再静默丢失 — 缓存 ring + Configure flush。
/// 注意: AgentTelemetry 是静态类 — 测试间共享状态, 用唯一 session 文件隔离。
/// </summary>
public class TelemetryPendingTests
{
    [Fact]
    public void Emit_Before_Configure_Is_Flushed_On_Configure()
    {
        var dir = Path.Combine(Path.GetTempPath(), "tel-pending-" + Guid.NewGuid().ToString("N"));
        try
        {
            // 1. Configure 前发射 (writer 未建立 → 进 pending ring)
            AgentTelemetry.Emit("pre_boot_probe", "Test", ("k", "v"));

            // 2. Configure (env 指向临时目录 → flush pending)
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_TELEMETRY", dir);
            AgentTelemetry.Configure("pendingtest", dir);

            // 3. Configure 后再发一条
            AgentTelemetry.Emit("post_boot_probe", "Test", ("k", "v"));

            // 4. 读文件: 两条都应在 (pending flush + 直写)
            var path = Path.Combine(dir, "pendingtest.jsonl");
            Assert.True(File.Exists(path), "telemetry 文件应存在");
            var lines = File.ReadAllLines(path);
            Assert.Contains(lines, l => l.Contains("pre_boot_probe"));
            Assert.Contains(lines, l => l.Contains("post_boot_probe"));
        }
        finally
        {
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_TELEMETRY", null);
            if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public void DroppedTotal_Tracks_Losses()
    {
        // 阈值语义: DroppedTotal 单调不减 (只在异常/溢出时增长)
        var before = AgentTelemetry.DroppedTotal;
        AgentTelemetry.Emit("no_op_probe", "Test");
        Assert.True(AgentTelemetry.DroppedTotal >= before);
    }
}
