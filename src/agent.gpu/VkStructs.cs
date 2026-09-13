using System.Runtime.InteropServices;

namespace agent.gpu;

/// <summary>
/// 本端口用到的 Vulkan 常量 —— 值必须与 Vulkan 头文件一致, 且**必须**与 Silk.NET 生成的枚举
/// 逐位相同 (机检: <c>src/agent.tests/VulkanLoaderParityTests.cs</c> 用 Silk.NET 作为独立 oracle 对账)。
/// 自写常量表三件套自证不算证据, 故此处只留最小集并对账。
/// </summary>
public static class VkConst
{
    public const uint StructureTypeApplicationInfo = 0;
    public const uint StructureTypeInstanceCreateInfo = 1;
    public const int Success = 0;
    public const int Incomplete = 5;
    public const uint PhysicalDeviceTypeOther = 0, PhysicalDeviceTypeIntegrated = 1,
                      PhysicalDeviceTypeDiscrete = 2, PhysicalDeviceTypeVirtual = 3, PhysicalDeviceTypeCpu = 4;

    public static string TypeName(uint t) => t switch
    {
        PhysicalDeviceTypeIntegrated => "integrated",
        PhysicalDeviceTypeDiscrete => "discrete",
        PhysicalDeviceTypeVirtual => "virtual",
        PhysicalDeviceTypeCpu => "cpu",
        _ => "other",
    };
}

[StructLayout(LayoutKind.Sequential)]
internal struct VkApplicationInfo
{
    public uint SType; public nint PNext; public nint PApplicationName;
    public uint ApplicationVersion; public nint PEngineName; public uint EngineVersion; public uint ApiVersion;
}

[StructLayout(LayoutKind.Sequential)]
internal struct VkInstanceCreateInfo
{
    public uint SType; public nint PNext; public uint Flags; public nint PApplicationInfo;
    public uint EnabledLayerCount; public nint PpEnabledLayerNames;
    public uint EnabledExtensionCount; public nint PpEnabledExtensionNames;
}

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
