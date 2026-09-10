using System;
using System.Runtime.InteropServices;

namespace agent.llmservice;

/// <summary>v0.20.1 P4-c (R344, 跨平台补齐): Windows 可用物理内存探测 — GlobalMemoryStatusEx (DllImport, AOT 兼容)。
/// Linux 走 /proc/meminfo (LlmManagerHost.ReadMemAvailableMb); 其他平台 → -1 (保守不卸载)。</summary>
public static class WindowsMemory
{
    [StructLayout(LayoutKind.Sequential)]
    private struct MEMORYSTATUSEX
    {
        public uint dwLength;
        public uint dwMemoryLoad;
        public ulong ullTotalPhys;
        public ulong ullAvailPhys;
        public ulong ullTotalPageFile;
        public ulong ullAvailPageFile;
        public ulong ullTotalVirtual;
        public ulong ullAvailVirtual;
        public ulong ullAvailExtendedVirtual;
    }

    // DllImport (非 LibraryImport): 避免项目级 AllowUnsafeBlocks (源生成器需 unsafe); blittable struct + bool 返回在 AOT 下无警告
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GlobalMemoryStatusEx(ref MEMORYSTATUSEX lpBuffer);

    /// <summary>可用物理内存 MB; 失败/非 Windows → -1 (调用方保守处理)。</summary>
    public static long GetAvailableMb()
    {
        if (!OperatingSystem.IsWindows()) return -1;
        try
        {
            var st = new MEMORYSTATUSEX { dwLength = (uint)Marshal.SizeOf<MEMORYSTATUSEX>() };
            if (!GlobalMemoryStatusEx(ref st)) return -1;
            return (long)st.ullAvailPhys / (1024 * 1024);
        }
        catch { return -1; }
    }
}
