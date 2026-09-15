using System;
using System.IO;
using agent.llamacpp;
using Xunit;

namespace agent.tests;

/// <summary>
/// R464 机检: **本地通道接线 fail-closed** —— 「配置错配」不得被静默当成「未配置」。
///
/// 反例纪律（承 R446/R463）: 每个断言都必须能把「按配置拒绝」与「静默替换」区分开 ⇒
/// 承重断言 = 错配时 `ModelPath == 配置路径 ∧ != fallback`（只断言“不可用”是不够的:
/// 静默回退默认权重时同样可能不可用，读数却完全不同）。
/// </summary>
public sealed class LocalChannelWiringTests
{
    private static readonly string RepoRoot = FindRepoRoot();

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        return dir?.FullName ?? ".";
    }

    // ---------- C1: 纯函数三态 ----------

    [Fact]
    public void Unconfigured_UsesFallback_NoWarning()
    {
        var r = LocalChannelWiring.Resolve(new LocalChannelWiringInput(
            Declared: false, ConfiguredPath: null, FallbackPath: "/host/default.gguf",
            ConfiguredFileExists: false, FallbackFileExists: true));

        Assert.Equal(LocalModelPathSource.Unconfigured, r.Source);
        Assert.Equal("/host/default.gguf", r.ModelPath);
        Assert.Null(r.Warning);
        Assert.False(r.ConfigMismatch);
    }

    [Fact]
    public void Unconfigured_FallbackMissing_WarnsButNotMismatch()
    {
        var r = LocalChannelWiring.Resolve(new LocalChannelWiringInput(
            Declared: false, ConfiguredPath: null, FallbackPath: "/host/missing.gguf",
            ConfiguredFileExists: false, FallbackFileExists: false));

        Assert.Equal(LocalModelPathSource.Unconfigured, r.Source);
        Assert.Contains(LocalChannelWiring.DefaultMissingMarker, r.Warning);
        Assert.False(r.ConfigMismatch); // 未声明 ≠ 错配（但同样必须留痕）
    }

    [Fact]
    public void Configured_Existing_UsesConfiguredPath_NoWarning()
    {
        var r = LocalChannelWiring.Resolve(new LocalChannelWiringInput(
            Declared: true, ConfiguredPath: "/cfg/3b.gguf", FallbackPath: "/host/default.gguf",
            ConfiguredFileExists: true, FallbackFileExists: true));

        Assert.Equal(LocalModelPathSource.Configured, r.Source);
        Assert.Equal("/cfg/3b.gguf", r.ModelPath);
        Assert.Null(r.Warning);
        Assert.True(r.UseConfiguredWidths);
    }

    [Fact]
    public void ConfiguredMissing_DoesNotSubstituteFallback()
    {
        // 承重: 错配 ⇒ 生效路径必须是**配置路径本身**（不可用），绝不是 fallback。
        var r = LocalChannelWiring.Resolve(new LocalChannelWiringInput(
            Declared: true, ConfiguredPath: "/cfg/nope.gguf", FallbackPath: "/host/default.gguf",
            ConfiguredFileExists: false, FallbackFileExists: true));

        Assert.Equal(LocalModelPathSource.ConfiguredMissing, r.Source);
        Assert.Equal("/cfg/nope.gguf", r.ModelPath);
        Assert.NotEqual("/host/default.gguf", r.ModelPath);
        Assert.True(r.ConfigMismatch);
        Assert.False(r.UseConfiguredWidths);
        Assert.Contains(LocalChannelWiring.MismatchMarker, r.Warning);
        Assert.Contains("/cfg/nope.gguf", r.Warning);
        Assert.Contains("/host/default.gguf", r.Warning); // 告警须点名「没回退谁」
    }

    [Fact]
    public void DeclaredButEmptyPath_Unavailable_NotFallback()
    {
        var r = LocalChannelWiring.Resolve(new LocalChannelWiringInput(
            Declared: true, ConfiguredPath: "  ", FallbackPath: "/host/default.gguf",
            ConfiguredFileExists: false, FallbackFileExists: true));

        Assert.Equal(LocalModelPathSource.ConfiguredMissing, r.Source);
        Assert.Equal(string.Empty, r.ModelPath);
        Assert.NotEqual("/host/default.gguf", r.ModelPath);
        Assert.Contains(LocalChannelWiring.MismatchMarker, r.Warning);
    }

    // ---------- 薄壳: 真文件系统探测 ----------

    [Fact]
    public void ResolveForHost_ProbesRealFilesystem()
    {
        var tmp = Path.Combine(Path.GetTempPath(), "r464-wiring-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(tmp);
        try
        {
            var present = Path.Combine(tmp, "present.gguf");
            File.WriteAllText(present, "x");
            var fallback = Path.Combine(tmp, "fallback.gguf");

            var ok = LocalChannelWiring.ResolveForHost(declared: true, configuredPath: present, fallbackPath: fallback);
            Assert.Equal(LocalModelPathSource.Configured, ok.Source);
            Assert.Equal(present, ok.ModelPath);

            var bad = LocalChannelWiring.ResolveForHost(declared: true,
                configuredPath: Path.Combine(tmp, "absent.gguf"), fallbackPath: fallback);
            Assert.Equal(LocalModelPathSource.ConfiguredMissing, bad.Source);
            Assert.Equal(Path.Combine(tmp, "absent.gguf"), bad.ModelPath);

            var nodecl = LocalChannelWiring.ResolveForHost(declared: false, configuredPath: null, fallbackPath: present);
            Assert.Equal(LocalModelPathSource.Unconfigured, nodecl.Source);
            Assert.Equal(present, nodecl.ModelPath);
        }
        finally
        {
            try { Directory.Delete(tmp, recursive: true); } catch (Exception) { /* 清理失败不影响判据 */ }
        }
    }

    // ---------- C2: 源级闸（防静默替换被重新引入） ----------

    [Fact]
    public void HostWiring_Source_ContainsNoSilentSubstitutionTernary()
    {
        var path = Path.Combine(RepoRoot, "src", "agent", "extensions", "ServiceCollectionExtensions.cs");
        Assert.True(File.Exists(path), $"接线源文件缺失: {path}");
        var src = File.ReadAllText(path);
        // 断言必须打在**代码**上（注释里引用旧写法是允许的、也是可读性所需）⇒ 先剥注释再断言。
        var code = StripLineComments(src);

        //   旧代码 = `ModelPath = lc.IsReady ? lc.ModelPath : baseOpts.ModelPath`
        //           `ContextSize = lc.IsReady && …` / `Parallel = lc.IsReady && …`
        Assert.DoesNotContain("ModelPath = lc.IsReady", code);
        Assert.DoesNotContain("ContextSize = lc.IsReady", code);
        Assert.DoesNotContain("Parallel = lc.IsReady", code);
        Assert.Contains("LocalChannelWiring.ResolveForHost", code);
        // 告警面必须留在接线里（否则错配又变成静默；用 wiring.Warning 的**使用点**判定, 不靠字符串拼接自证）
        Assert.Contains("if (wiring.Warning is not null)", code);
        Assert.Contains("Console.Error.WriteLine", code);
    }

    /// <summary>剥掉 C# 行注释（`//` 但排除 `://` 形态的 URL），只保留可执行代码形态供源级闸断言。</summary>
    private static string StripLineComments(string src)
    {
        var sb = new System.Text.StringBuilder(src.Length);
        foreach (var raw in src.Split('\n'))
        {
            var line = raw;
            var idx = line.IndexOf("//", StringComparison.Ordinal);
            while (idx >= 0)
            {
                var isUrl = idx > 0 && line[idx - 1] == ':';
                if (isUrl)
                    idx = line.IndexOf("//", idx + 2, StringComparison.Ordinal);
                else
                {
                    line = line.Substring(0, idx);
                    break;
                }
            }
            sb.Append(line).Append('\n');
        }
        return sb.ToString();
    }

    [Fact]
    public void LocalChannelConfig_Declared_SeparatedFromReadiness()
    {
        // Declared 是「配置意图」，IsReady 是「此刻可用」——两者不得由同一表达式决定。
        var cfg = new agent.modelqueue.LocalChannelConfig { ModelPath = "/definitely/absent/r464.gguf", Declared = true };
        Assert.True(cfg.Declared);
        Assert.False(cfg.IsReady);

        var undeclared = new agent.modelqueue.LocalChannelConfig();
        Assert.False(undeclared.Declared);
        Assert.False(undeclared.IsReady);
    }
}
