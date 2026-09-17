using System.Runtime.InteropServices;

namespace agent.gpu;


/// <summary>
/// 只声明头部字段 (apiVersion..deviceName); 其余字段不声明但**必须留足空间** ——
/// 驱动按完整结构体写入。Size=1024 覆盖完整 VkPhysicalDeviceProperties (实测 &lt; 900B),
/// 头部字段偏移 (0/4/8/12/16/20) 与规范一致, 已由 vulkaninfo 交叉验证。
/// </summary>
[StructLayout(LayoutKind.Sequential, Size = 1024)]
internal unsafe struct VkPhysicalDeviceProperties
{
    public uint ApiVersion; public uint DriverVersion; public uint VendorId; public uint DeviceId; public uint DeviceType;
    public fixed byte DeviceName[256];

    public readonly string Name()
    {
        fixed (byte* p = DeviceName) return Marshal.PtrToStringUTF8((nint)p) ?? string.Empty;
    }
}
