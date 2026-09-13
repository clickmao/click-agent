using System.Runtime.InteropServices;

namespace agent.gpu;

/// <summary>
/// Vulkan 加载器解析 —— 只依赖 BCL 的 <see cref="NativeLibrary"/>, 零第三方绑定、零反射、零 shell。
/// 失败**显式**返回原因码 (绝不静默回退到 CPU 后端): 调用方必须自行决策。
/// </summary>
public static class VulkanLoader
{
    public const string ReasonOk = "ok";
    public const string ReasonNotFound = "not_found";
    public const string ReasonExportMissing = "export_missing";

    /// 解析加载器。forcedName 非空时**只用该名字** (负控注入点: 不给任何兜底)。
    public static bool TryLoad(out nint handle, out string loadedName, out string reason, string? forcedName = null)
    {
        var candidates = string.IsNullOrEmpty(forcedName) ? VulkanNames.Candidates() : new[] { forcedName };
        foreach (var name in candidates)
        {
            if (NativeLibrary.TryLoad(name, out handle))
            {
                loadedName = name;
                reason = ReasonOk;
                return true;
            }
        }
        handle = 0;
        loadedName = forcedName ?? string.Empty;
        reason = $"{ReasonNotFound}({string.Join("|", candidates)})";
        return false;
    }

    /// 取导出符号; 缺失时返回 false (调用方决定是"可选"还是"必需")。
    public static unsafe bool TryExport(nint lib, string symbol, out void* fn)
    {
        fn = null;
        if (!NativeLibrary.TryGetExport(lib, symbol, out var p)) return false;
        fn = (void*)p;
        return true;
    }
}
