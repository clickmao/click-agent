using System.IO;
using agent.config;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 需求4 测试: ConfigWriter 人性化读写 — dot-path 读取/L4 runtime 写/L3 模块覆盖/重置。
/// </summary>
public class ConfigWriterTests : IDisposable
{
    private readonly string _root;

    public ConfigWriterTests()
    {
        _root = Path.Combine(Path.GetTempPath(), "cfgw_tests_" + System.Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(Path.Combine(_root, "base"));
        // 规范: 文件内容顶层 key = 模块名
        File.WriteAllText(Path.Combine(_root, "base", "model_queue.yaml"),
            "model_queue:\n  router:\n    max_failures: 3\n    sticky: true\n");
    }

    public void Dispose()
    {
        try { Directory.Delete(_root, recursive: true); } catch { }
    }

    [Fact]
    public void GetValue_DotPath_Reads_Merged_Snapshot()
    {
        var snapshot = new ConfigSnapshot(_root);
        Assert.Equal(3, ConfigWriter.GetValue(snapshot, "model_queue", "router.max_failures", 0));
        Assert.True(ConfigWriter.GetValue(snapshot, "model_queue", "router.sticky", false));
        Assert.Equal("x", ConfigWriter.GetValue(snapshot, "model_queue", "router.missing", "x"));
    }

    [Fact]
    public void SetRuntime_Writes_L4_And_Snapshot_Sees_It()
    {
        var writer = new ConfigWriter(_root);
        writer.SetRuntime("model_queue", "router.max_failures", 5);

        // L4 覆盖 L1
        var snapshot = new ConfigSnapshot(_root);
        Assert.Equal(5, ConfigWriter.GetValue(snapshot, "model_queue", "router.max_failures", 0));
        // L1 未被动过
        var baseText = File.ReadAllText(Path.Combine(_root, "base", "model_queue.yaml"));
        Assert.Contains("max_failures: 3", baseText);
    }

    [Fact]
    public void UpdateModule_Writes_L3_And_Merges()
    {
        var writer = new ConfigWriter(_root);
        writer.UpdateModule("model_queue", new System.Collections.Generic.Dictionary<string, object?>
        {
            ["router"] = new System.Collections.Generic.Dictionary<string, object?>
            {
                ["sticky"] = false,
                ["extra"] = "new_key",
            },
        });

        var snapshot = new ConfigSnapshot(_root);
        Assert.False(ConfigWriter.GetValue(snapshot, "model_queue", "router.sticky", true));
        Assert.Equal("new_key", ConfigWriter.GetValue(snapshot, "model_queue", "router.extra", ""));
        Assert.Equal(3, ConfigWriter.GetValue(snapshot, "model_queue", "router.max_failures", 0)); // L1 透传
    }

    [Fact]
    public void ResetModule_Falls_Back_To_L1()
    {
        var writer = new ConfigWriter(_root);
        writer.UpdateModule("model_queue", new System.Collections.Generic.Dictionary<string, object?>
        {
            ["router"] = new System.Collections.Generic.Dictionary<string, object?> { ["sticky"] = false },
        });
        Assert.False(ConfigWriter.GetValue(new ConfigSnapshot(_root), "model_queue", "router.sticky", true));

        writer.ResetModule("model_queue");
        Assert.True(ConfigWriter.GetValue(new ConfigSnapshot(_root), "model_queue", "router.sticky", false));
    }
}
