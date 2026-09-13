using System.Runtime.InteropServices;

namespace agent.gpu;

/// <summary>
/// Vulkan 加载器/实例/物理设备三段探针 —— 零第三方绑定 (NativeLibrary + 函数指针)。
/// 结果**池化复用** (同一进程内加载器/实例只解析一次), 并保留 <c>fresh=true</c> 逃生口供机检对比。
/// 输出与系统 <c>vulkaninfo</c> (独立实现) 交叉验证, 不自证。
/// </summary>
public static unsafe class VkProbe
{
    public sealed record DeviceRow(int Index, string Name, uint ApiVersion, uint DriverVersion,
                                   uint VendorId, uint DeviceId, uint DeviceType, string TypeName);

    public sealed record ProbeResult(bool Ok, string LibraryName, string Reason,
                                     uint LoaderInstanceVersion, IReadOnlyList<DeviceRow> Devices)
    {
        public string LoaderInstanceVersionText => VulkanNames.FormatVersion(LoaderInstanceVersion);
    }

    static readonly object Gate = new();
    static ProbeResult? _cached;

    /// <summary>探针入口。默认返回**缓存的同一实例** (池化复用); fresh=true 强制重新枚举。</summary>
    public static ProbeResult Probe(bool fresh = false)
    {
        lock (Gate)
        {
            if (!fresh && _cached is not null) return _cached;
            var r = ProbeCore();
            _cached = r;
            return r;
        }
    }

    static ProbeResult ProbeCore()
    {
        var forced = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_GPU_LIBRARY");
        if (!VulkanLoader.TryLoad(out var lib, out var soname, out var reason, forced))
            return new ProbeResult(false, soname, reason, 0, Array.Empty<DeviceRow>());

        // ① 加载器实例版本 (1.1+ 才有该导出; 缺失 ⇒ 按 1.0 记, 不臆造)
        uint instanceVersion;
        if (VulkanLoader.TryExport(lib, "vkEnumerateInstanceVersion", out var pEnumVer))
        {
            var fn = (delegate* unmanaged[Cdecl]<uint*, int>)pEnumVer;
            uint v = 0;
            instanceVersion = fn(&v) == VkConst.Success ? v : 0u;
        }
        else instanceVersion = VulkanNames.MakeVersion(1, 0, 0);

        // ② 实例创建 (请求版本与引擎侧 Silk.NET 路径一致)
        var app = new VkApplicationInfo
        {
            SType = VkConst.StructureTypeApplicationInfo,
            ApiVersion = VulkanNames.ApiVersion,
        };
        var ci = new VkInstanceCreateInfo
        {
            SType = VkConst.StructureTypeInstanceCreateInfo,
            PApplicationInfo = (nint)(&app),
        };
        if (!VulkanLoader.TryExport(lib, "vkCreateInstance", out var pCreate))
            return new ProbeResult(false, soname, VulkanLoader.ReasonExportMissing + "(vkCreateInstance)", instanceVersion, Array.Empty<DeviceRow>());
        nint instance = 0;
        var create = (delegate* unmanaged[Cdecl]<VkInstanceCreateInfo*, void*, nint*, int>)pCreate;
        int rc = create(&ci, null, &instance);
        if (rc != VkConst.Success)
            return new ProbeResult(false, soname, $"create_instance_rc={rc}", instanceVersion, Array.Empty<DeviceRow>());

        try
        {
            if (!VulkanLoader.TryExport(lib, "vkEnumeratePhysicalDevices", out var pEnum) ||
                !VulkanLoader.TryExport(lib, "vkGetPhysicalDeviceProperties", out var pProps))
                return new ProbeResult(false, soname, VulkanLoader.ReasonExportMissing + "(device_enum)", instanceVersion, Array.Empty<DeviceRow>());

            var enumDev = (delegate* unmanaged[Cdecl]<nint, uint*, nint*, int>)pEnum;
            var getProps = (delegate* unmanaged[Cdecl]<nint, VkPhysicalDeviceProperties*, void>)pProps;

            uint count = 0;
            rc = enumDev(instance, &count, null);
            if (rc != VkConst.Success && rc != VkConst.Incomplete)
                return new ProbeResult(false, soname, $"enumerate_devices_rc={rc}", instanceVersion, Array.Empty<DeviceRow>());

            var handles = new nint[count];
            fixed (nint* hp = handles)
            {
                uint n2 = count;
                rc = enumDev(instance, &n2, hp);
                if (rc == VkConst.Success || rc == VkConst.Incomplete) count = n2;
            }

            var rows = new List<DeviceRow>((int)count);
            for (int i = 0; i < count; i++)
            {
                VkPhysicalDeviceProperties props = default;
                getProps(handles[i], &props);
                rows.Add(new DeviceRow(i, props.Name(), props.ApiVersion, props.DriverVersion,
                                       props.VendorId, props.DeviceId, props.DeviceType,
                                       VkConst.TypeName(props.DeviceType)));
            }
            return new ProbeResult(true, soname, VulkanLoader.ReasonOk, instanceVersion, rows);
        }
        finally
        {
            if (VulkanLoader.TryExport(lib, "vkDestroyInstance", out var pDestroy))
            {
                var destroy = (delegate* unmanaged[Cdecl]<nint, void*, void>)pDestroy;
                destroy(instance, null);
            }
        }
    }
}
