using Xunit;
namespace agent.tests;

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
            // 词表移除后 (2026-09-19): ExtractSignals 的中文信号表已删 ⇒ 本测试不再依赖它。
            // 持久化层契约 = UpdateTendencyAsync 落盘 ∧ 按 userId 回读 ⇒ 直接喂结构化倾向数据。
            d.TopicScores["csharp"] = 1.0;

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
