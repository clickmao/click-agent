using System.Runtime.InteropServices;
using LLama;
using LLama.Native;
using Microsoft.Extensions.Logging;

namespace agent.llamalocal;

/// <summary>LLamaSharp 原生后端模式</summary>
public enum LlamaBackendMode
{
    /// <summary>自动: 有 vulkan loader + ggml-vulkan 产物 → Vulkan; 否则 CPU</summary>
    Auto,

    /// <summary>强制 CPU (ggml-cpu)</summary>
    Cpu,

    /// <summary>强制 Vulkan (ggml-vulkan; loader 缺失时报错不回落)</summary>
    Vulkan,
}

/// <summary>
/// Vulkan 载入支持 (v7.13): 用户钦定 — 内置 LLamaSharp 的 vulkan 模式, 且
/// vulkan loader 必须复用 Silk.NET.Vulkan 约定的同一个动态库, 不再带第二份副本。
///
/// 事实链 (readelf 实证):
///   • LLamaSharp.Backend.Vulkan 的 libggml-vulkan.so DT_NEEDED = libvulkan.so.1
///   • Silk.NET.Vulkan 是纯托管绑定, P/Invoke 目标同为 libvulkan.so.1 (Linux) / vulkan-1.dll (Win)
///   • 因此 loader 全局唯一: 系统安装的 vulkan loader — LLamaSharp vulkan 后端与
///     Silk.NET.Vulkan 绑定共享同一份, 满足"复用 Silk.NET 的 vulkan dll"。
///
/// 加载顺序 (LocalLlamaCaller 初始化前调用 Configure):
///   ① NativeLibraryConfig.LLama.WithVulkan(true) → LLamaSharp 走 native/vulkan/ 目录的 ggml-vulkan
///   ② WithSearchDirectory 指向运行目录 (包产物已复制到输出目录)
///   ③ VulkanLoaderPath 探测: 系统存在 libvulkan.so.1 / vulkan-1.dll 才启用, 否则按模式回落或报错
/// </summary>
public static class VulkanSupport
{
    /// <summary>vulkan loader (与 Silk.NET.Vulkan P/Invoke 同一个) 的系统路径候选</summary>
    private static readonly string[] LinuxLoaderCandidates =
    [
        "libvulkan.so.1",
        "libvulkan.so",
        "/usr/lib/x86_64-linux-gnu/libvulkan.so.1",
        "/usr/lib/x86_64-linux-gnu/libvulkan.so",
    ];

    /// <summary>
    /// 系统是否装了 vulkan loader (dlopen 试探 — 与 Silk.NET.Vulkan 绑定加载的是同一个库)。
    /// </summary>
    public static bool IsLoaderAvailable()
    {
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            return TryOpen("vulkan-1.dll");
        return LinuxLoaderCandidates.Any(TryOpen);
    }

    /// <summary>已解析的 loader 说明 (诊断用, CLI /status 展示)</summary>
    public static string DescribeLoader() =>
        RuntimeInformation.IsOSPlatform(OSPlatform.Windows)
            ? "vulkan-1.dll (系统, Silk.NET.Vulkan 同款)"
            : LinuxLoaderCandidates.FirstOrDefault(TryOpen) is { } found
                ? $"{found} (系统, Silk.NET.Vulkan 同款)"
                : "未找到 libvulkan loader";

    /// <summary>
    /// 按 backendMode 配置 LLamaSharp 原生库加载。
    /// 必须在任何 LLamaWeights.LoadFromFile 之前调用 (LibraryHasLoaded 后配置无效)。
    /// 返回实际生效的模式 (Auto 探测后可能降为 Cpu)。
    /// </summary>
    public static LlamaBackendMode Configure(LlamaBackendMode mode, ILogger logger)
    {
        if (NativeLibraryConfig.LLama.LibraryHasLoaded)
        {
            logger.LogWarning("LLamaSharp 原生库已加载, NativeLibraryConfig 配置无效 (保持首次配置)");
            return mode;
        }

        switch (mode)
        {
            case LlamaBackendMode.Vulkan:
                if (!IsLoaderAvailable())
                    throw new InvalidOperationException(
                        $"Vulkan 模式要求系统安装 vulkan loader ({DescribeLoader()})。安装 vulkan 驱动或改用 CPU 模式。");
                // ggml-vulkan 默认过滤 CPU 类型实现 (lavapipe/llvmpipe): 全软设备时自动放开,
                // 否则 ggml_vulkan 报 "No devices found" 直接回退 CPU 分配 (v7.13 真机验证发现的坑)。
                // 用户显式设置过 GGML_VK_VISIBLE_DEVICES 时不覆盖。
                EnsureGgmlVulkanDeviceVisible();
                NativeLibraryConfig.LLama
                    .WithVulkan(true)
                    .WithAutoFallback(false)   // 强制 vulkan — 失败就报错, 不静默滑回 CPU
                    .SkipCheck(false);
                logger.LogInformation("LLamaSharp 后端: Vulkan (loader={Loader})", DescribeLoader());
                return LlamaBackendMode.Vulkan;

            case LlamaBackendMode.Cpu:
                NativeLibraryConfig.LLama
                    .WithVulkan(false)
                    .WithAutoFallback(false);
                logger.LogInformation("LLamaSharp 后端: CPU");
                return LlamaBackendMode.Cpu;

            case LlamaBackendMode.Auto:
            default:
                // Auto 探测 (v7.13 真机验证后修正): 只看 loader 存在是不够的 —
                // LLamaSharp 内部还要求 vulkaninfo 探测到设备 (SystemInfo.VulkanVersion),
                // 且 ggml-vulkan 默认过滤 CPU 类型实现 (lavapipe 场景需 GGML_VK_VISIBLE_DEVICES=0)。
                // 判据: loader dlopen OK && vulkaninfo --summary 能枚举出设备 → Vulkan, 否则 CPU。
                var useVulkan = IsLoaderAvailable() && HasVulkanDevice();
                if (useVulkan)
                    EnsureGgmlVulkanDeviceVisible();
                NativeLibraryConfig.LLama
                    .WithVulkan(useVulkan)
                    .WithAutoFallback(true);   // Auto: ggml-vulkan 产物缺失时允许回落 CPU
                logger.LogInformation("LLamaSharp 后端: {Mode} (loader={Loader}, device={Device})",
                    useVulkan ? "Vulkan" : "CPU", DescribeLoader(),
                    useVulkan ? "已枚举" : "未枚举到");
                return useVulkan ? LlamaBackendMode.Vulkan : LlamaBackendMode.Cpu;
        }
    }

    /// <summary>
    /// 是否存在可枚举的 vulkan 设备 (vulkaninfo --summary 探测 — 与 LLamaSharp SystemInfo 同一判据)。
    /// Windows 上不做此探测 (loader 存在即认为有设备, WDDM 体系无此歧义)。
    /// </summary>
    public static bool HasVulkanDevice()
    {
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            return true;
        if (!IsVulkanInfoAvailable())
            return false;
        var output = RunVulkanInfoSummary();
        // GPU0: 段落出现 = 至少枚举到一个物理设备
        return output != null && output.Contains("GPU", StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>
    /// ggml-vulkan 只认非 CPU 类型 vulkan 设备。系统只有软件实现 (lavapipe/llvmpipe) 时,
    /// 自动设置 GGML_VK_VISIBLE_DEVICES=0 让它可见 (用户显式设置过则尊重用户)。
    /// </summary>
    private static void EnsureGgmlVulkanDeviceVisible()
    {
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            return; // Windows 无此过滤问题
        if (!string.IsNullOrEmpty(Environment.GetEnvironmentVariable("GGML_VK_VISIBLE_DEVICES")))
            return; // 用户显式控制, 不覆盖
        var summary = RunVulkanInfoSummary();
        if (summary == null)
            return;
        // 有 PHYSICAL_DEVICE_TYPE_CPU 之外的设备 (INTEGRATED_GPU/DISCRETE_GPU/VIRTUAL) → 真硬件在, 无需干预
        var hasRealGpu = summary.Contains("PHYSICAL_DEVICE_TYPE_GPU", StringComparison.Ordinal) ||
                         summary.Contains("PHYSICAL_DEVICE_TYPE_INTEGRATED", StringComparison.Ordinal) ||
                         summary.Contains("PHYSICAL_DEVICE_TYPE_DISCRETE", StringComparison.Ordinal) ||
                         summary.Contains("PHYSICAL_DEVICE_TYPE_VIRTUAL", StringComparison.Ordinal);
        if (hasRealGpu)
            return;
        // 只有 CPU 型设备 (或枚举不到类型) → 放开第一个设备给 ggml
        // ⚠️ 必须走 libc setenv: ggml-vulkan 是 native 层用 getenv 读,
        // .NET Environment.SetEnvironmentVariable 只写托管 env block, native 读不到 (真机判决实验证实)。
        NativeEnv.Set("GGML_VK_VISIBLE_DEVICES", "0");
    }

    /// <summary>
    /// native 可见的环境变量写入 (v7.14): libc setenv + 托管双写。
    /// </summary>
    private static class NativeEnv
    {
        [System.Runtime.InteropServices.DllImport("libc", SetLastError = true, CharSet = System.Runtime.InteropServices.CharSet.Ansi)]
        [return: System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPStr)]
        private static extern string? setenv(string name, string value, int overwrite);

        /// <summary>写入进程级 env (native getenv 与 .NET GetEnvironmentVariable 都可见)</summary>
        public static void Set(string name, string value)
        {
            try
            {
                setenv(name, value, 1);
            }
            catch
            {
                // libc 不可用 (非 Unix) → 退回托管写
            }
            Environment.SetEnvironmentVariable(name, value);
        }
    }

    private static string? RunVulkanInfoSummary()
    {
        if (!IsVulkanInfoAvailable())
            return null;
        try
        {
            using var p = System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = "vulkaninfo",
                Arguments = "--summary",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
            });
            if (p == null)
                return null;
            var output = p.StandardOutput.ReadToEnd();
            p.WaitForExit(8000);
            return p.ExitCode == 0 ? output : null;
        }
        catch
        {
            return null;
        }
    }

    private static bool? _vkInfoAvailable;

    private static bool IsVulkanInfoAvailable()
    {
        if (_vkInfoAvailable.HasValue)
            return _vkInfoAvailable.Value;
        _vkInfoAvailable = TryOpenExecutable("vulkaninfo");
        return _vkInfoAvailable.Value;
    }

    private static bool TryOpenExecutable(string name)
    {
        foreach (var dir in (Environment.GetEnvironmentVariable("PATH") ?? string.Empty).Split(':'))
        {
            if (string.IsNullOrWhiteSpace(dir))
                continue;
            try
            {
                if (File.Exists(Path.Combine(dir.Trim(), name)))
                    return true;
            }
            catch { /* 路径异常忽略 */ }
        }
        return false;
    }

    private static bool TryOpen(string name)
    {
        // dlopen/LoadLibrary 试探 — 句柄立即释放; 失败 = 系统无此 loader
        try
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                var h = LoadLibrary(name);
                if (h != IntPtr.Zero) { FreeLibrary(h); return true; }
                return false;
            }
            var handle = dlopen(name, RTLD_NOW | RTLD_LOCAL);
            if (handle != IntPtr.Zero) { dlclose(handle); return true; }
            return false;
        }
        catch
        {
            return false;
        }
    }

    private const int RTLD_NOW = 0x2;
    private const int RTLD_LOCAL = 0x0;

    [DllImport("libdl.so.2", EntryPoint = "dlopen", SetLastError = true)]
    private static extern IntPtr dlopen(string filename, int flags);

    [DllImport("libdl.so.2", EntryPoint = "dlclose")]
    private static extern int dlclose(IntPtr handle);

    [DllImport("kernel32", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern IntPtr LoadLibrary(string lpFileName);

    [DllImport("kernel32", SetLastError = true)]
    private static extern int FreeLibrary(IntPtr hLibModule);
}
