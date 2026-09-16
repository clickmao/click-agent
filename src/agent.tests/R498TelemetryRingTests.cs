using System;
using System.Globalization;
using System.IO;
using System.Linq;
using agent.config;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// R498 候选②: 遥测 pending 环的**满环语义**回归 (真缺陷 88)。
///
/// 缺陷: 旧策略 <c>if (Count &lt; 256) Add(...)</c> 在环满时丢弃的是**最新**一条 ——
/// 而「Configure 紧前发出的那一条」(启动路径探针 / 末位启动事件) 恰好是环里最新的,
/// 于是 R121「不静默丢失」的语义被上限反向破掉: 越接近 Configure 的点越容易被丢。
/// 修复: 满环 ⇒ **FIFO 淘汰最旧**, 并单列 <c>PendingEvictions</c> 让淘汰可见。
///
/// 同网格单变量对照 (证据: eval/rover/r498/telemetry-ring-before-after.log):
///   旧策略 = RED (探针缺席于 flush 后的文件) / 新策略 = GREEN (探针在位)。
/// 无对照的断言 = 无判别力, 故本用例同时断言「上限仍生效」(不得改成无界) 与「淘汰已计数」(不得静默)。
/// </summary>
[Collection(AgentTelemetryStaticCollection.Name)]
public sealed class R498TelemetryRingTests
{
    [Fact]
    public void 满环后紧前探针仍必须可_flush_且淘汰必须可见()
    {
        AgentTelemetry.ResetForTests();
        var dir = Path.Combine(Path.GetTempPath(), "r498_ring_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        try
        {
            // 造现场: 环被**无关写入者**灌满 —— xUnit 并行下 ContextAssembler phase_timing /
            // tendency 打点 / 四个遥测测试类的形状 (它们都在 Configure 之前 Emit)。
            var fillers = AgentTelemetry.PendingCapacity + 64;
            for (var i = 0; i < fillers; i++)
                AgentTelemetry.Emit("ring_filler", "R498", ("i", i.ToString(CultureInfo.InvariantCulture)));

            // 紧前探针 = 「Configure 前最后一发」的形状。
            AgentTelemetry.Emit("ring_probe", "R498", ("k", "v"));

            // ① 上限仍生效 (不许把缺陷改成无界内存增长)
            Assert.Equal(AgentTelemetry.PendingCapacity, AgentTelemetry.PendingCount);
            // ② 淘汰必须可见 (不得静默丢)
            Assert.True(AgentTelemetry.PendingEvictions >= 64,
                $"淘汰数应 ≥64, 实际 {AgentTelemetry.PendingEvictions}");
            // ③ 口径: DroppedTotal 不再把「已缓存」计成「已丢弃」
            Assert.True(AgentTelemetry.PendingBuffered >= fillers + 1,
                $"进环总数应 ≥{fillers + 1}, 实际 {AgentTelemetry.PendingBuffered}");

            AgentTelemetry.Configure("r498ring", dir);

            var path = Path.Combine(dir, "r498ring.jsonl");
            Assert.True(File.Exists(path), "telemetry 文件应存在");
            var lines = File.ReadAllLines(path);
            var fillerLines = lines.Count(l => l.Contains("ring_filler", StringComparison.Ordinal));
            var probeLines = lines.Count(l => l.Contains("ring_probe", StringComparison.Ordinal));
            Assert.True(probeLines == 1,
                $"诊断: lines={lines.Length} filler={fillerLines} probe={probeLines} last={(lines.Length > 0 ? lines[^1].Substring(0, Math.Min(160, lines[^1].Length)) : "<none>")}");
            // ⑤ 反向: 被淘汰的是**最旧**的 filler (i=0..), 不是最新 —— 证明 FIFO 方向。
            //    注意 filler 的 kv 是**字符串**值 ("i":"0"), 不是数字。
            Assert.DoesNotContain(lines, l => l.Contains("\"i\":\"0\"", StringComparison.Ordinal));
            Assert.Contains(lines, l => l.Contains($"\"i\":\"{fillers - 1}\"", StringComparison.Ordinal));
        }
        finally
        {
            AgentTelemetry.ResetForTests();
            try { Directory.Delete(dir, true); } catch (IOException) { /* 清理失败不影响判定 */ }
        }
    }

    [Fact]
    public void 复位接缝_必须把静态态清回未_Configure_初态()
    {
        var dir = Path.Combine(Path.GetTempPath(), "r498_reset_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        try
        {
            AgentTelemetry.Configure("r498pre", dir);
            AgentTelemetry.ResetForTests();
            // 复位后: writer 已清 ⇒ 再 Emit 必须重新进环 (而不是写进旧文件 / 被 WriterNullDrops 吞掉)
            var before = AgentTelemetry.PendingBuffered;
            AgentTelemetry.Emit("after_reset_probe", "R498");
            Assert.True(AgentTelemetry.PendingBuffered > before, "复位后 Emit 必须重新进 pending 环");
            Assert.Equal(0, AgentTelemetry.PendingCount - 1);
        }
        finally
        {
            AgentTelemetry.ResetForTests();
            try { Directory.Delete(dir, true); } catch (IOException) { /* 清理失败不影响判定 */ }
        }
    }
}
