using System.Runtime.InteropServices;

namespace agent.gpu;


[StructLayout(LayoutKind.Sequential)]
internal struct VkApplicationInfo
{
    public uint SType; public nint PNext; public nint PApplicationName;
    public uint ApplicationVersion; public nint PEngineName; public uint EngineVersion; public uint ApiVersion;
}
