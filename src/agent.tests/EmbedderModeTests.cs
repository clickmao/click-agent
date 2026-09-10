using System;
using System.IO;
using System.Threading.Tasks;
using Xunit;
using agent.llamalocal;
using agent.llmservice;

namespace agentframework.tests;

/// <summary>v0.20.1 P4-a/P4-c (R344): 嵌入后端 opt-in 模式解析 (默认 local 行为不变) + 跨平台内存探测。</summary>
public class EmbedderModeTests
{
    [Theory]
    [InlineData("remote", EmbedderModeKind.Remote)]
    [InlineData("REMOTE", EmbedderModeKind.Remote)]
    [InlineData(" Remote ", EmbedderModeKind.Remote)]
    [InlineData("local", EmbedderModeKind.Local)]
    [InlineData("", EmbedderModeKind.Local)]
    [InlineData(null, EmbedderModeKind.Local)]
    [InlineData("xyz", EmbedderModeKind.Local)]          // 未知值 → 默认 local (不误启)
    [InlineData("remote2", EmbedderModeKind.Local)]      // 严格匹配
    public void Resolve_Matrix(string? envValue, EmbedderModeKind expected)
        => Assert.Equal(expected, EmbedderMode.Resolve(envValue));

    [Fact]
    public void RemoteEmbedder_IsAvailable_WithSpawnableBin()
    {
        // 有可拉起可执行 → IsAvailable=true (lazy 语义: 能拉起即可用, 避免恒退锚词)
        var sock = $"/tmp/af-mode-{Guid.NewGuid():N}.sock";
        var fakeBin = Path.Combine(Path.GetTempPath(), $"af-fake-agenthost-{Guid.NewGuid():N}");
        File.WriteAllText(fakeBin, "#!/bin/sh\nexit 0\n");
        var oldBin = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLM_SERVICE_BIN");
        var oldSock = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLM_SERVICE_SOCK");
        try
        {
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_LLM_SERVICE_BIN", fakeBin);
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_LLM_SERVICE_SOCK", sock);
            using var e = new RemoteEmbedder(sock);
            Assert.True(e.IsAvailable);         // daemon 离线但可拉起
        }
        finally
        {
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_LLM_SERVICE_BIN", oldBin);
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_LLM_SERVICE_SOCK", oldSock);
            try { File.Delete(fakeBin); } catch { }
        }
    }

    [Fact]
    public void RemoteEmbedder_IsAvailable_WithoutBin_False()
    {
        var sock = $"/tmp/af-mode-{Guid.NewGuid():N}.sock";
        var oldBin = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLM_SERVICE_BIN");
        try
        {
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_LLM_SERVICE_BIN", null);
            using var e = new RemoteEmbedder(sock);
            // 当前进程非 agenthost (测试宿主) 且无 env → 不可拉起 → false
            Assert.False(e.IsAvailable);
        }
        finally { Environment.SetEnvironmentVariable("AGENTFRAMEWORK_LLM_SERVICE_BIN", oldBin); }
    }

    [Fact]
    public void MemProbe_CurrentPlatform_Sane()
    {
        var mb = LlmManagerHost.ReadMemAvailableMb();
        if (OperatingSystem.IsWindows() || OperatingSystem.IsLinux())
            Assert.True(mb > 0, $"应有可用内存读数, 实际 {mb}");
        else
            Assert.Equal(-1, mb); // 其他平台保守 -1
    }

    [Fact]
    public void WindowsMemory_NonWindows_ReturnsMinusOne()
    {
        if (!OperatingSystem.IsWindows())
            Assert.Equal(-1, WindowsMemory.GetAvailableMb());
    }
}
