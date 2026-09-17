using System.Runtime.InteropServices;

namespace agent.gpu;


[StructLayout(LayoutKind.Sequential)]
internal struct VkInstanceCreateInfo
{
    public uint SType; public nint PNext; public uint Flags; public nint PApplicationInfo;
    public uint EnabledLayerCount; public nint PpEnabledLayerNames;
    public uint EnabledExtensionCount; public nint PpEnabledExtensionNames;
}
