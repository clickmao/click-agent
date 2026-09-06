using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.11.0 R34 (真 bug 24): TendencyAnalyzer 内存字典跨进程丢失 → 落盘持久化。
/// </summary>
public class TendencyPersistenceTests
{
    [Fact]
    public void Update_Persists_To_Disk_And_Reloads()
    {
        var dir = Path.Combine(Path.GetTempPath(), "tend_" + Guid.NewGuid().ToString("N"));
        try
        {
            var a = new agent.tendency.TendencyAnalyzer(dir);
            var d = new agent.tendency.TendencyData
            {
                UserId = "u1",
                Timestamp = DateTime.UtcNow,
            };
            foreach (var kv in agent.tendency.TendencyAnalyzer.ExtractSignals("用 C# 写代码，回答简洁"))
                d.TopicScores[kv.Key] = kv.Value;

            a.UpdateTendencyAsync(d.UserId, d).Wait();

            var file = Directory.Exists(dir) ? Directory.GetFiles(dir) : Array.Empty<string>();
            Assert.NotEmpty(file);

            var b = new agent.tendency.TendencyAnalyzer(dir);
            var prof = b.AnalyzeUserTendencyAsync("u1").GetAwaiter().GetResult();
            Assert.Equal(1, prof.SampleSize);
        }
        finally
        {
            if (Directory.Exists(dir)) Directory.Delete(dir, true);
        }
    }
}
