using agent.tendency;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.11.0 R123 (真缺陷 52): 空 userId 不入库不落盘 (原持久化到 ".json" 空文件名, 召回链永不读取)。
/// </summary>
public class TendencyEmptyUserTests
{
    [Fact]
    public async Task UpdateTendencyAsync_EmptyUserId_NoFileWritten()
    {
        var dir = Path.Combine(Path.GetTempPath(), "tend-empty-" + Guid.NewGuid().ToString("N"));
        try
        {
            var analyzer = new TendencyAnalyzer(dir);
            await analyzer.UpdateTendencyAsync("", new TendencyData { TopicScores = new() { ["python"] = 1 } });
            await analyzer.UpdateTendencyAsync("  ", new TendencyData());

            Assert.False(File.Exists(Path.Combine(dir, ".json")), "空 userId 不应产生 .json 文件");
            Assert.False(Directory.Exists(dir) && Directory.GetFiles(dir).Length > 0, "目录应保持空");
        }
        finally
        {
            if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public async Task UpdateTendencyAsync_ValidUserId_WritesFile()
    {
        var dir = Path.Combine(Path.GetTempPath(), "tend-ok-" + Guid.NewGuid().ToString("N"));
        try
        {
            var analyzer = new TendencyAnalyzer(dir);
            await analyzer.UpdateTendencyAsync("cli-user", new TendencyData { TopicScores = new() { ["python"] = 1 } });

            Assert.True(File.Exists(Path.Combine(dir, "cli_user.json")), "正常 userId 应落盘");
        }
        finally
        {
            if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true);
        }
    }
}
