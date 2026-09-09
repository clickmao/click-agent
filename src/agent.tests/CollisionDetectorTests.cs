using System;
using System.IO;
using System.Threading;
using Xunit;
using agent.execution;

namespace agentframework.tests;

/// <summary>v0.17.3 (R340): 时序撞车检测 — 写者持续改写时 IsSettling=true; 停写后 stable;
/// WaitUntilStable 超时拒绝; 不存在文件不误判。</summary>
public class CollisionDetectorTests
{
    private static string TempFile()
        => Path.Combine(Path.GetTempPath(), "af-ttc-" + Guid.NewGuid().ToString("N") + ".bin");

    [Fact]
    public void Settling_WhileWriterActive_Detected()
    {
        var path = TempFile();
        File.WriteAllBytes(path, new byte[100]);
        var stop = false;
        var writer = new Thread(() =>
        {
            var i = 0;
            while (!stop)
            {
                File.WriteAllBytes(path, new byte[100 + (i++ % 5) * 100]);
                Thread.Sleep(10);
            }
        });
        writer.Start();
        try
        {
            Thread.Sleep(50); // 让写者跑起来
            Assert.True(CollisionDetector.IsSettling(path, minStableMs: 300),
                "写者活跃 (每 10ms 改 mtime/size) → 应判 settling");
        }
        finally { stop = true; writer.Join(1000); }
    }

    [Fact]
    public void Stable_AfterWriterStops()
    {
        var path = TempFile();
        File.WriteAllBytes(path, new byte[100]);
        Thread.Sleep(50); // 无写者
        Assert.False(CollisionDetector.IsSettling(path, minStableMs: 300),
            "无写入 → 应 stable");
    }

    [Fact]
    public void WaitUntilStable_Timeout_ReturnsFalse()
    {
        var path = TempFile();
        var stop = false;
        var writer = new Thread(() =>
        {
            var i = 0;
            while (!stop)
            {
                File.WriteAllBytes(path, new byte[100 + (i++ % 3) * 100]);
                Thread.Sleep(5);
            }
        });
        File.WriteAllBytes(path, new byte[100]);
        writer.Start();
        try
        {
            // 写者持续 → 等待 800ms 超时应 false (拒绝执行)
            Assert.False(CollisionDetector.WaitUntilStable(path, waitMs: 800, minStableMs: 200));
        }
        finally { stop = true; writer.Join(1000); }
    }

    [Fact]
    public void Nonexistent_NotSettling()
    {
        var path = Path.Combine(Path.GetTempPath(), "af-ttc-missing-" + Guid.NewGuid().ToString("N"));
        Assert.False(CollisionDetector.IsSettling(path));
    }
}
