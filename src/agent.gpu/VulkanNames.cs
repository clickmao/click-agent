namespace agent.gpu;

/// <summary>
/// Vulkan 加载器名字与版本口径 —— **必须与 Silk.NET 2.23.0 逐字一致** (R396 用户令:
/// "不要引入silk.net; 但用的vulkan.dll文件名与版本请和silk.net库一致")。
///
/// 权威来源 (非文档、非猜测): 从包内受管程序集 `Silk.NET.Vulkan.dll` 的元数据里
/// 机械提取的 UTF-16 字符串常量 —— 这正是 Silk.NET 运行时交给动态加载器的名字。
///   取证脚本: `eval/vulkan/extract_silknet_loader_names.py`
///   取证结果: `src/agent.gpu/oracle/silknet-vulkan-loader.json` (含源资产 sha256)
///   机检    : `src/agent.tests/VulkanLoaderParityTests.cs` (逐字比对 + 溯源复算 + 负控)
///
/// "版本"的两层含义都在此锁死:
///   ① **加载器 ABI 主版本** 由 soname 承载 (`libvulkan.so.1`), 与 Silk.NET 的候选名一致;
///   ② **请求的 Vulkan API 版本** = 引擎侧 Silk.NET 路径的 `Vk.MakeVersion(1, 1, 0)`
///      (见 `src/agent.rover/gpu/VulkanBackend.cs`), 机检与 `Silk.NET.Vulkan.Vk.MakeVersion` 对账。
///     加载器**实际**报告的实例版本另行打印 (本机 1.3.275), 不做硬编码断言。
/// </summary>
public static class VulkanNames
{
    /// 对齐的 Silk.NET 包与版本 (oracle 的 provenance)
    public const string SilkNetPackage = "Silk.NET.Vulkan";
    public const string SilkNetVersion = "2.23.0";

    /// Windows
    public const string Windows = "vulkan-1.dll";
    /// Linux soname (ABI 主版本 1) —— 优先
    public const string LinuxSoname = "libvulkan.so.1";
    /// Linux 无版本名 —— 兜底 (与 Silk.NET 候选顺序一致)
    public const string LinuxFallback = "libvulkan.so";
    /// macOS
    public const string MacOs = "libvulkan.dylib";

    /// 引擎侧 Silk.NET 路径请求的 API 版本 = MakeVersion(1,1,0) = 4198400
    public const uint ApiVersion = (1u << 22) | (1u << 12) | 0u;

    /// 当前平台的解析候选 (顺序 = 优先级)
    public static string[] Candidates()
    {
        if (OperatingSystem.IsWindows()) return new[] { Windows };
        if (OperatingSystem.IsMacOS()) return new[] { MacOs };
        return new[] { LinuxSoname, LinuxFallback };
    }

    /// 平台 → 候选名 (供 oracle 机检逐字对账, 不依赖运行平台)
    public static string[] CandidatesFor(string platform) => platform switch
    {
        "windows" => new[] { Windows },
        "linux" => new[] { LinuxSoname, LinuxFallback },
        "macos" => new[] { MacOs },
        _ => throw new ArgumentOutOfRangeException(nameof(platform), platform, "unknown_platform"),
    };

    /// VK_MAKE_VERSION 语义 (与 Silk.NET 同式)
    public static uint MakeVersion(uint major, uint minor, uint patch) => (major << 22) | (minor << 12) | patch;

    /// 版本号格式化 (major.minor.patch)
    public static string FormatVersion(uint v) => $"{v >> 22}.{(v >> 12) & 0x3FFu}.{v & 0xFFFu}";
}
