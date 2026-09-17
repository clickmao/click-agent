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
