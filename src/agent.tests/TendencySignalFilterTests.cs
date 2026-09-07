using agent.tendency;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.11.0 R133 (K1 断链修复): UserTendency 画像被空信号记录稀释 → 恒 0 召回。
/// 修复: ①空信号不入库 ②画像聚合只基于有信号记录 ③召回链路闭合后可观测。
/// </summary>
public class TendencySignalFilterTests
{
    private static string TempDir(string tag) =>
        Path.Combine(Path.GetTempPath(), $"tend-{tag}-" + Guid.NewGuid().ToString("N"));

    [Fact]
    public async Task UpdateTendencyAsync_NoSignals_NotPersisted()
    {
        var dir = TempDir("signal");
        try
        {
            var analyzer = new TendencyAnalyzer(dir);
            // 无主题无风格信号 (问候/系统消息) → 不入库
            await analyzer.UpdateTendencyAsync("u1", new TendencyData
            {
                UserId = "u1",
                TopicScores = new(),
                StyleScores = new(),
            });

            var file = Path.Combine(dir, "u1.json");
            Assert.False(File.Exists(file), "全空信号记录不应落盘 (无信息量, 只稀释画像)");
        }
        finally
        {
            if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public void Analyze_LegacyEmptyFloodOnDisk_StillYieldsTendency()
    {
        var dir = TempDir("flood");
        try
        {
            Directory.CreateDirectory(dir);
            // 模拟 cli_user.json 真实存量: 老版本写入 20 空 + 6 python 信号 (空记录占多数)
            // 手工构造文件绕过 Update 过滤 — 存量脏数据只能来自旧版本落盘
            var sb = new System.Text.StringBuilder("[");
            for (var i = 0; i < 26; i++)
            {
                if (i > 0) sb.Append(',');
                if (i < 20)
                {
                    sb.Append("{\"UserId\":\"u2\",\"Timestamp\":\"2026-09-07T00:00:00Z\",\"TopicScores\":{},\"StyleScores\":{}}");
                }
                else
                {
                    sb.Append("{\"UserId\":\"u2\",\"Timestamp\":\"2026-09-07T00:01:00Z\",\"TopicScores\":{\"Python\":1,\"python\":1},\"StyleScores\":{}}");
                }
            }
            sb.Append(']');
            File.WriteAllText(Path.Combine(dir, "u2.json"), sb.ToString());

            var analyzer = new TendencyAnalyzer(dir);
            var prof = analyzer.AnalyzeUserTendencyAsync("u2").GetAwaiter().GetResult();
            Assert.True(prof.SampleSize == 6,
                $"画像样本数应只计有信号记录 (6), 实际 {prof.SampleSize}");
            Assert.True(prof.TopicTendencies.TryGetValue("Python", out var score) && score > 0.3,
                $"存量 6/26 有信号且全 python → Python 倾向应 >0.3 入档, 实际 score={score}");

            // 链路闭合: 有画像后 GetContextBias 应给出 >0.3 置信 (此前恒 ≤0.3 被召回端拦截)
            var bias = analyzer.GetContextBiasAsync("u2", "帮我写 python 脚本").GetAwaiter().GetResult();
            Assert.True(bias.OverallConfidence > 0.3,
                $"召回置信应 >0.3, 实际 {bias.OverallConfidence}");
        }
        finally
        {
            if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public void GetContextBias_WithFreshSignals_ConfidenceAboveThreshold()
    {
        var dir = TempDir("bias");
        try
        {
            var analyzer = new TendencyAnalyzer(dir);
            for (var i = 0; i < 15; i++)
            {
                var d = new TendencyData { UserId = "u3", Timestamp = DateTime.UtcNow.AddMinutes(i) };
                d.TopicScores["python"] = 1.0;
                d.TopicScores["api"] = 1.0;
                analyzer.UpdateTendencyAsync("u3", d).Wait();
            }

            var bias = analyzer.GetContextBiasAsync("u3", "帮我写 python api 客户端").GetAwaiter().GetResult();
            Assert.NotNull(bias);
            Assert.True(bias.OverallConfidence > 0.3,
                $"有 15 条 python/api 信号, 召回置信应 >0.3, 实际 {bias.OverallConfidence}");
            Assert.True(bias.BiasScores.Count > 0, "BiasScores 不应为空 (有历史信号注入)");
        }
        finally
        {
            if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true);
        }
    }
}
