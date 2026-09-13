using agent.gpu;

namespace agent.gpu.cli;

/// <summary>
/// agent.gpu CLI —— 机器可读行 (无人读文案), 输出走注入的 TextWriter (零 Console.WriteLine)。
/// </summary>
public static class GpuCli
{
    public const string UsageLine = "  probe [--fresh] [--negctl]           Vulkan 加载器/实例/设备探针 (自载, 零第三方绑定)";

    public static int Run(string[] args, TextWriter o, TextWriter err)
    {
        if (args.Length == 0) { Usage(o); return 2; }
        try
        {
            return args[0] switch
            {
                "probe" => Probe(args, o),
                "--help" or "-h" or "help" => Usage(o),
                _ => Unknown(args[0], err),
            };
        }
        catch (Exception ex)
        {
            err.WriteLine($"error{{kind={ex.GetType().Name} message={ex.Message}}}");
            return 1;
        }
    }

    static int Usage(TextWriter o)
    {
        o.WriteLine("agent.gpu — 产品侧 GPU 执行面 (Vulkan 加载器名字/版本与 Silk.NET 2.23.0 一致, 零第三方绑定)");
        o.WriteLine(UsageLine);
        return 0;
    }

    static int Unknown(string cmd, TextWriter err)
    {
        err.WriteLine($"error{{kind=unknown_command command={cmd}}}");
        return 2;
    }

    static int Probe(string[] a, TextWriter o)
    {
        bool fresh = a.Contains("--fresh");
        bool negctl = a.Contains("--negctl");

        o.WriteLine($"vknames{{package={VulkanNames.SilkNetPackage} version={VulkanNames.SilkNetVersion} " +
                    $"windows={VulkanNames.Windows} linux={VulkanNames.LinuxSoname} linux_fallback={VulkanNames.LinuxFallback} " +
                    $"macos={VulkanNames.MacOs} requested_api={VulkanNames.FormatVersion(VulkanNames.ApiVersion)}}}");

        if (negctl)
        {
            // 负控: 强制一个不存在的加载器名 ⇒ 必须**显式** not_found 且 ok=false (不得静默回退)
            bool loaded = VulkanLoader.TryLoad(out _, out _, out var nreason, "libvulkan-not-a-real-name-xyz.so.9");
            o.WriteLine($"vknegctl{{loaded={loaded.ToString().ToLowerInvariant()} reason={nreason} " +
                        $"verdict={(loaded ? "FAIL" : "ok")}}}");
            return loaded ? 1 : 0;
        }

        var r = VkProbe.Probe(fresh);
        o.WriteLine($"vkloader{{soname={r.LibraryName} reason={r.Reason} ok={r.Ok.ToString().ToLowerInvariant()} " +
                    $"instance_version={r.LoaderInstanceVersionText} raw={r.LoaderInstanceVersion} cached={(!fresh).ToString().ToLowerInvariant()}}}");
        foreach (var d in r.Devices)
            o.WriteLine($"vkdevice{{index={d.Index} name=\"{d.Name}\" api={VulkanNames.FormatVersion(d.ApiVersion)} " +
                        $"driver={d.DriverVersion} vendor=0x{d.VendorId:X} device=0x{d.DeviceId:X} type={d.TypeName}}}");
        o.WriteLine($"done{{command=probe ok={r.Ok.ToString().ToLowerInvariant()} devices={r.Devices.Count}}}");
        return r.Ok ? 0 : 1;
    }
}
