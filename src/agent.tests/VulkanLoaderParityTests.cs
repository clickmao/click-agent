using System.Security.Cryptography;
using System.Text.Json;
using agent.gpu;
using Xunit;

namespace agent.tests;

/// <summary>
/// R396 机检 —— 用户令(逐字): "不要引入silk.net; 但用的vulkan.dll文件名与版本请和silk.net库一致"。
///
/// 判据:
///   ① **名字逐字**: 三平台候选名 == 从包内程序集机械提取的 oracle (跨机器可复算);
///   ② **溯源**: 若本机存在被取证的包资产, 其 sha256 必须与 oracle 记录一致 (不一致 ⇒ oracle 过期必须重取);
///   ③ **版本一致**: 我们请求的 API 版本 == 引擎侧 Silk.NET 路径的 `Vk.MakeVersion(1, 1, 0)` (源码级反漂移);
///   ④ **不引入 Silk.NET**: agent.gpu 工程文件零 PackageReference (机检, 非口头承诺);
///   ⑤ **负控**: 不存在的加载器名必须显式 not_found (加载器不能"永远成功");
///   ⑥ **真机**: 加载器/实例/设备可枚举, 且探针结果**池化复用** (同进程不重复建实例)。
/// </summary>
public class VulkanLoaderParityTests
{
    static readonly string RepoRoot = FindRepoRoot();

    static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        return dir?.FullName ?? ".";
    }

    static JsonElement Oracle()
    {
        var path = Path.Combine(RepoRoot, "src", "agent.gpu", "oracle", "silknet-vulkan-loader.json");
        Assert.True(File.Exists(path), $"oracle_missing: {path} (先跑 eval/vulkan/extract_silknet_loader_names.py)");
        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        return doc.RootElement.Clone();
    }

    [Fact]  // ①②
    public void Oracle_Names_Match_Declared_And_Source_Is_Traceable()
    {
        var oracle = Oracle();
        Assert.Equal("Silk.NET.Vulkan", oracle.GetProperty("source_package").GetString());
        Assert.Equal("2.23.0", oracle.GetProperty("source_version").GetString());

        var map = oracle.GetProperty("platform_map");
        foreach (var platform in new[] { "windows", "linux", "macos" })
        {
            var want = map.GetProperty(platform).EnumerateArray().Select(e => e.GetString()!).ToArray();
            var got = VulkanNames.CandidatesFor(platform);
            Assert.True(want.SequenceEqual(got),
                $"加载器名字与 Silk.NET 不一致 platform={platform} oracle=[{string.Join(",", want)}] ours=[{string.Join(",", got)}]");
        }

        // 溯源: 包资产在盘时必须与 oracle 记录的 sha256 一致 (否则 oracle 已过期)
        var dll = ResolveSilkNetVulkanDll();
        if (dll is null)
        {
            Console.WriteLine("[warn] Silk.NET.Vulkan.dll 不在本机 nuget 缓存, 跳过 sha256 溯源复算 (名字断言仍生效)");
        }
        else
        {
            var sha = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(dll))).ToLowerInvariant();
            Assert.Equal(oracle.GetProperty("source_sha256").GetString(), sha);
        }
    }

    static string? ResolveSilkNetVulkanDll()
    {
        var root = Environment.GetEnvironmentVariable("NUGET_PACKAGES");
        if (string.IsNullOrEmpty(root))
            root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".nuget", "packages");
        var p = Path.Combine(root, "silk.net.vulkan", "2.23.0", "lib", "netstandard2.0", "Silk.NET.Vulkan.dll");
        return File.Exists(p) ? p : null;
    }

    [Fact]  // ③
    public void Requested_ApiVersion_Matches_Engine_SilkNet_Path()
    {
        // 我们请求的版本必须与引擎侧 Silk.NET 路径一致 ⇒ 源码级反漂移 (不依赖引用 Silk.NET)
        var engine = Path.Combine(RepoRoot, "src", "agent.rover", "gpu", "VulkanBackend.cs");
        Assert.True(File.Exists(engine), $"engine_source_missing: {engine}");
        var src = File.ReadAllText(engine);
        Assert.Contains("ApiVersion = Vk.MakeVersion(1, 1, 0)", src);

        Assert.Equal(4198400u, VulkanNames.ApiVersion);            // (1<<22)|(1<<12)
        Assert.Equal("1.1.0", VulkanNames.FormatVersion(VulkanNames.ApiVersion));
        Assert.Equal(VulkanNames.ApiVersion, VulkanNames.MakeVersion(1, 1, 0));
    }

    [Fact]  // ④
    public void Product_Side_Project_Has_No_SilkNet_Or_Any_PackageReference()
    {
        var csproj = Path.Combine(RepoRoot, "src", "agent.gpu", "agent.gpu.csproj");
        Assert.True(File.Exists(csproj));
        var xml = File.ReadAllText(csproj);
        // 先剥 XML 注释 —— 注释里引用用户令原文("不要引入silk.net")不算依赖
        var code = System.Text.RegularExpressions.Regex.Replace(xml, "<!--.*?-->", "", System.Text.RegularExpressions.RegexOptions.Singleline);
        Assert.DoesNotContain("PackageReference", code);   // 产品侧 GPU 工程: 零外部包
        Assert.DoesNotContain("<Reference ", code);

        // 依赖声明投影检查: 任何工程的 PackageReference 名单里都不得出现 Silk.NET
        // (oracle 文件名里出现 "silknet" 是**取证来源标注**, 不是依赖, 故只查依赖声明)
        foreach (var rel in new[] { "src/agent.gpu/agent.gpu.csproj", "src/agent/agent.csproj" })
        {
            var p = Path.Combine(RepoRoot, rel);
            var stripped = System.Text.RegularExpressions.Regex.Replace(
                File.ReadAllText(p), "<!--.*?-->", "", System.Text.RegularExpressions.RegexOptions.Singleline);
            var refs = System.Text.RegularExpressions.Regex
                .Matches(stripped, "<PackageReference[^>]*Include=\"([^\"]+)\"")
                .Select(m => m.Groups[1].Value).ToArray();
            Assert.DoesNotContain(refs, r => r.Contains("Silk", StringComparison.OrdinalIgnoreCase));
            var projRefs = System.Text.RegularExpressions.Regex
                .Matches(stripped, "<ProjectReference[^>]*Include=\"([^\"]+)\"")
                .Select(m => m.Groups[1].Value).ToArray();
            Assert.DoesNotContain(projRefs, r => r.Contains("Silk", StringComparison.OrdinalIgnoreCase));
        }
    }

    [Fact]  // ⑤
    public void Negative_Control_Bogus_Loader_Must_Fail_Explicitly()
    {
        bool loaded = VulkanLoader.TryLoad(out _, out _, out var reason, "libvulkan-not-a-real-name-xyz.so.9");
        Assert.False(loaded, "不存在的加载器名被报告为成功 ⇒ 加载器判定无判别力 (空心)");
        Assert.Contains("not_found", reason);
    }

    [Fact]  // ⑥
    public void Real_Probe_Enumerates_Device_And_Is_Pooled()
    {
        var r = VkProbe.Probe(fresh: true);
        Assert.True(r.Ok, $"probe_failed reason={r.Reason}");
        Assert.Equal(VulkanLoader.ReasonOk, r.Reason);
        Assert.NotEmpty(r.Devices);
        Assert.True((r.LoaderInstanceVersion >> 22) >= 1u, $"loader_instance_version={r.LoaderInstanceVersionText}");
        foreach (var d in r.Devices)
        {
            Assert.False(string.IsNullOrWhiteSpace(d.Name), "device name 为空");
            Assert.True((d.ApiVersion >> 22) >= 1u, $"device api={VulkanNames.FormatVersion(d.ApiVersion)}");
        }

        // 池化复用: 默认调用必须返回**同一实例**, 不得每次重建 (R393 纪律: 设备句柄池化)
        Assert.Same(VkProbe.Probe(), VkProbe.Probe());
        Assert.NotSame(r, VkProbe.Probe(fresh: true));
    }
}
