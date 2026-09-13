using System.Text;
using clickrover.gpu.spirv;
using Silk.NET.Vulkan;

namespace clickrover.gpu;

/// <summary>真枚举得到的物理设备事实 (CLI 直接输出, 不加工)。</summary>
public sealed record VkDeviceInfo(
    int Index, string Name, uint ApiVersion, uint DriverVersion, uint VendorId,
    PhysicalDeviceType Type, int QueueFamilies, uint ComputeFamily, ulong MemoryBytes);

/// <summary>
/// Vulkan 计算后端 —— 运行库 = Silk.NET.Vulkan (与 Silk.NET 同款)。
/// 设计取舍 (可核对):
///   · 缓冲一律 HOST_VISIBLE|HOST_COHERENT|STORAGE_BUFFER → 免 staging 拷贝, 单提交 + QueueWaitIdle;
///   · 提交两侧各插一条 VkBufferMemoryBarrier (Host→Compute / Compute→Host), 不依赖隐式同步;
///   · 设备/ICD 不可用时返回 null 并给机器可读原因 —— 绝不静默退回 CPU 冒充 GPU。
/// 本机实测 ICD = lavapipe (llvmpipe, 软件 Vulkan), 因此 GPU 路径可**真跑**并对账, 而非只编译。
/// </summary>
public sealed unsafe class VulkanBackend : IDisposable
{
    readonly Vk _vk;
    readonly Instance _inst;
    readonly Device _dev;
    readonly Queue _queue;
    readonly CommandPool _pool;
    readonly PhysicalDeviceMemoryProperties _memProps;
    bool _disposed;

    public VkDeviceInfo Info { get; }
    public string LoaderVersion { get; }
    public int DeviceCount { get; }

    VulkanBackend(Vk vk, Instance inst, Device dev, Queue queue, CommandPool pool,
        PhysicalDeviceMemoryProperties memProps, VkDeviceInfo info, string loaderVersion, int deviceCount)
    {
        _vk = vk; _inst = inst; _dev = dev; _queue = queue; _pool = pool;
        _memProps = memProps; Info = info; LoaderVersion = loaderVersion; DeviceCount = deviceCount;
    }

    static string FixedName(in PhysicalDeviceProperties p)
    {
        var copy = p;
        byte* bp = copy.DeviceName;
        int len = 0;
        while (len < 256 && bp[len] != 0) len++;
        return Encoding.ASCII.GetString(bp, len);
    }

    static ulong DeviceLocalBytes(in PhysicalDeviceMemoryProperties mp)
    {
        ulong total = 0;
        for (uint i = 0; i < mp.MemoryHeapCount; i++)
        {
            var h = mp.MemoryHeaps[(int)i];
            if ((h.Flags & MemoryHeapFlags.DeviceLocalBit) != 0) total += h.Size;
        }
        return total;
    }

    /// <summary>创建实例并枚举设备 (不挑设备), 供 --list 用。失败返回 null 并已写出原因。</summary>
    public static IReadOnlyList<VkDeviceInfo> Enumerate(TextWriter o, out string loader, out int deviceCount)
    {
        loader = "n/a"; deviceCount = 0;
        var list = new List<VkDeviceInfo>();
        Vk vk;
        try { vk = Vk.GetApi(); }
        catch (Exception ex) { o.WriteLine($"vkerr{{stage=loader kind={ex.GetType().Name} message={ex.Message}}}"); return list; }

        Instance inst;
        var r = CreateInstance(vk, out inst);
        if (r != Result.Success) { o.WriteLine($"vkerr{{stage=instance result={r} note=vulkan_loader_or_icd_unavailable}}"); return list; }

        uint n = 0;
        vk.EnumeratePhysicalDevices(inst, &n, null);
        if (n == 0) { o.WriteLine("vkerr{stage=enumerate devices=0 note=no_icd_exposed_device}"); vk.DestroyInstance(inst, null); return list; }

        var devs = new PhysicalDevice[n];
        fixed (PhysicalDevice* dp = devs) vk.EnumeratePhysicalDevices(inst, &n, dp);
        deviceCount = (int)n;
        for (int i = 0; i < devs.Length; i++)
        {
            PhysicalDeviceProperties props;
            vk.GetPhysicalDeviceProperties(devs[i], &props);
            var mp = default(PhysicalDeviceMemoryProperties);
            vk.GetPhysicalDeviceMemoryProperties(devs[i], &mp);
            uint qn = 0;
            vk.GetPhysicalDeviceQueueFamilyProperties(devs[i], &qn, null);
            var qs = new QueueFamilyProperties[qn];
            fixed (QueueFamilyProperties* qp = qs) vk.GetPhysicalDeviceQueueFamilyProperties(devs[i], &qn, qp);
            uint compute = uint.MaxValue;
            for (int q = 0; q < qs.Length; q++)
                if ((qs[q].QueueFlags & QueueFlags.ComputeBit) != 0) { compute = (uint)q; break; }
            list.Add(new VkDeviceInfo(i, FixedName(props), props.ApiVersion, props.DriverVersion, props.VendorID,
                props.DeviceType, qs.Length, compute, DeviceLocalBytes(mp)));
        }
        vk.DestroyInstance(inst, null);
        return list;
    }

    static Result CreateInstance(Vk vk, out Instance inst)
    {
        byte[] app = Encoding.ASCII.GetBytes("click-rover");
        byte[] eng = Encoding.ASCII.GetBytes("click-rover");
        fixed (byte* pa = app)
        fixed (byte* pe = eng)
        {
            var ai = new ApplicationInfo
            {
                SType = StructureType.ApplicationInfo,
                PApplicationName = pa, ApplicationVersion = Vk.MakeVersion(0, 23, 0),
                PEngineName = pe, EngineVersion = Vk.MakeVersion(0, 23, 0),
                ApiVersion = Vk.MakeVersion(1, 1, 0),
            };
            var ci = new InstanceCreateInfo { SType = StructureType.InstanceCreateInfo, PApplicationInfo = &ai };
            return vk.CreateInstance(&ci, null, out inst);
        }
    }

    /// <summary>打开第 <paramref name="index"/> 个物理设备 (需有计算队列族)。不可用 → null + 原因。</summary>
    public static VulkanBackend? TryOpen(TextWriter o, int index)
    {
        Vk vk;
        try { vk = Vk.GetApi(); }
        catch (Exception ex) { o.WriteLine($"vkerr{{stage=loader kind={ex.GetType().Name} message={ex.Message}}}"); return null; }

        Instance inst;
        var r = CreateInstance(vk, out inst);
        if (r != Result.Success) { o.WriteLine($"vkerr{{stage=instance result={r} note=vulkan_loader_or_icd_unavailable}}"); return null; }

        uint n = 0;
        vk.EnumeratePhysicalDevices(inst, &n, null);
        if (n == 0) { o.WriteLine("vkerr{stage=enumerate devices=0 note=no_icd_exposed_device}"); vk.DestroyInstance(inst, null); return null; }
        if (index < 0 || index >= n)
        {
            o.WriteLine($"vkerr{{stage=select index={index} devices={n} note=device_index_out_of_range}}");
            vk.DestroyInstance(inst, null);
            return null;
        }

        var devs = new PhysicalDevice[n];
        fixed (PhysicalDevice* dp = devs) vk.EnumeratePhysicalDevices(inst, &n, dp);
        var pd = devs[index];

        PhysicalDeviceProperties props;
        vk.GetPhysicalDeviceProperties(pd, &props);
        var mp = default(PhysicalDeviceMemoryProperties);
        vk.GetPhysicalDeviceMemoryProperties(pd, &mp);
        uint qn = 0;
        vk.GetPhysicalDeviceQueueFamilyProperties(pd, &qn, null);
        var qs = new QueueFamilyProperties[qn];
        fixed (QueueFamilyProperties* qp = qs) vk.GetPhysicalDeviceQueueFamilyProperties(pd, &qn, qp);
        uint family = uint.MaxValue;
        for (int q = 0; q < qs.Length; q++)
            if ((qs[q].QueueFlags & QueueFlags.ComputeBit) != 0) { family = (uint)q; break; }
        if (family == uint.MaxValue)
        {
            o.WriteLine($"vkerr{{stage=queue_families device={index} families={qn} note=no_compute_queue}}");
            vk.DestroyInstance(inst, null);
            return null;
        }

        float prio = 1.0f;
        var qci = new DeviceQueueCreateInfo
        {
            SType = StructureType.DeviceQueueCreateInfo,
            QueueFamilyIndex = family, QueueCount = 1, PQueuePriorities = &prio,
        };
        var dci = new DeviceCreateInfo
        {
            SType = StructureType.DeviceCreateInfo,
            QueueCreateInfoCount = 1, PQueueCreateInfos = &qci,
        };
        r = vk.CreateDevice(pd, &dci, null, out var dev);
        if (r != Result.Success) { o.WriteLine($"vkerr{{stage=device result={r} family={family}}}"); vk.DestroyInstance(inst, null); return null; }

        vk.GetDeviceQueue(dev, family, 0, out var queue);
        var pci = new CommandPoolCreateInfo
        {
            SType = StructureType.CommandPoolCreateInfo,
            Flags = CommandPoolCreateFlags.ResetCommandBufferBit, QueueFamilyIndex = family,
        };
        r = vk.CreateCommandPool(dev, &pci, null, out var pool);
        if (r != Result.Success) { o.WriteLine($"vkerr{{stage=command_pool result={r}}}"); vk.DestroyDevice(dev, null); vk.DestroyInstance(inst, null); return null; }

        var info = new VkDeviceInfo(index, FixedName(props), props.ApiVersion, props.DriverVersion, props.VendorID,
            props.DeviceType, qs.Length, family, DeviceLocalBytes(mp));
        return new VulkanBackend(vk, inst, dev, queue, pool, mp, info, props.DriverVersion.ToString(), (int)n);
    }

    uint FindMemoryType(uint typeBits)
    {
        const MemoryPropertyFlags want = MemoryPropertyFlags.HostVisibleBit | MemoryPropertyFlags.HostCoherentBit;
        for (uint i = 0; i < _memProps.MemoryTypeCount; i++)
        {
            if ((typeBits & (1u << (int)i)) == 0) continue;
            if ((_memProps.MemoryTypes[(int)i].PropertyFlags & want) == want) return i;
        }
        throw new InvalidOperationException("vulkan_no_host_visible_coherent_memory_type");
    }

    /// <summary>单个内核的派发结果 (真机读数)。</summary>
    public sealed record DispatchResult(string Kernel, int Elements, uint Groups, double DispatchMs, double ElementsPerMs);

    /// <summary>
    /// 派发一个计算内核: <paramref name="buffers"/> 为各绑定的 f32 数据 (长度可不同, 如标量缓冲)。
    /// 就地写回计算结果 —— 对账在调用方进行。
    /// </summary>
    public DispatchResult Dispatch(Kernels.Kernel kernel, float[][] buffers, int count)
    {
        if (buffers.Length != kernel.BufferCount)
            throw new ArgumentException($"vk_buffer_count_mismatch: got {buffers.Length} expect {kernel.BufferCount}");

        var issues = SpirvValidator.Validate(kernel.Words, (int)kernel.LocalSizeX, kernel.BufferCount);
        if (issues.Count > 0)
            throw new InvalidOperationException($"vk_spirv_invalid: {string.Join(",", System.Linq.Enumerable.Select(issues, x => x.Code))}");

        int nb = buffers.Length;
        var bufs = new Silk.NET.Vulkan.Buffer[nb];
        var mems = new DeviceMemory[nb];
        var sizes = new ulong[nb];
        var maps = new void*[nb];
        var infos = new DescriptorBufferInfo[nb];

        try
        {
            for (int i = 0; i < nb; i++)
            {
                sizes[i] = (ulong)buffers[i].Length * 4;
                var bci = new BufferCreateInfo
                {
                    SType = StructureType.BufferCreateInfo, Size = sizes[i],
                    Usage = BufferUsageFlags.StorageBufferBit | BufferUsageFlags.TransferSrcBit | BufferUsageFlags.TransferDstBit,
                    SharingMode = SharingMode.Exclusive,
                };
                var r = _vk.CreateBuffer(_dev, &bci, null, out bufs[i]);
                if (r != Result.Success) throw new InvalidOperationException($"vk_create_buffer_failed: {r}");
                var req = default(MemoryRequirements);
                _vk.GetBufferMemoryRequirements(_dev, bufs[i], &req);
                var mai = new MemoryAllocateInfo
                {
                    SType = StructureType.MemoryAllocateInfo,
                    AllocationSize = req.Size, MemoryTypeIndex = FindMemoryType(req.MemoryTypeBits),
                };
                r = _vk.AllocateMemory(_dev, &mai, null, out mems[i]);
                if (r != Result.Success) throw new InvalidOperationException($"vk_allocate_memory_failed: {r}");
                _vk.BindBufferMemory(_dev, bufs[i], mems[i], 0);
                void* p;
                r = _vk.MapMemory(_dev, mems[i], 0, sizes[i], MemoryMapFlags.None, &p);
                if (r != Result.Success) throw new InvalidOperationException($"vk_map_memory_failed: {r}");
                maps[i] = p;
                fixed (float* src = buffers[i]) System.Buffer.MemoryCopy(src, p, (long)sizes[i], (long)sizes[i]);
                infos[i] = new DescriptorBufferInfo { Buffer = bufs[i], Offset = 0, Range = sizes[i] };
            }

            // 描述符布局 + 池 + 集合
            var bindings = new DescriptorSetLayoutBinding[nb];
            for (int i = 0; i < nb; i++)
                bindings[i] = new DescriptorSetLayoutBinding
                {
                    Binding = (uint)i, DescriptorType = DescriptorType.StorageBuffer,
                    DescriptorCount = 1, StageFlags = ShaderStageFlags.ComputeBit,
                };
            DescriptorSetLayout layout;
            fixed (DescriptorSetLayoutBinding* bp = bindings)
            {
                var dslci = new DescriptorSetLayoutCreateInfo
                { SType = StructureType.DescriptorSetLayoutCreateInfo, BindingCount = (uint)nb, PBindings = bp };
                var r = _vk.CreateDescriptorSetLayout(_dev, &dslci, null, out layout);
                if (r != Result.Success) throw new InvalidOperationException($"vk_descriptor_layout_failed: {r}");
            }

            var poolSizes = new DescriptorPoolSize[nb];
            for (int i = 0; i < nb; i++) poolSizes[i] = new DescriptorPoolSize { Type = DescriptorType.StorageBuffer, DescriptorCount = 1 };
            DescriptorPool dpool;
            fixed (DescriptorPoolSize* ps = poolSizes)
            {
                var dpci = new DescriptorPoolCreateInfo
                { SType = StructureType.DescriptorPoolCreateInfo, MaxSets = 1, PoolSizeCount = (uint)nb, PPoolSizes = ps };
                var r = _vk.CreateDescriptorPool(_dev, &dpci, null, out dpool);
                if (r != Result.Success) throw new InvalidOperationException($"vk_descriptor_pool_failed: {r}");
            }

            DescriptorSet set;
            {
                var dsl = layout;
                var dsai = new DescriptorSetAllocateInfo
                { SType = StructureType.DescriptorSetAllocateInfo, DescriptorPool = dpool, DescriptorSetCount = 1, PSetLayouts = &dsl };
                var r = _vk.AllocateDescriptorSets(_dev, &dsai, out set);
                if (r != Result.Success) throw new InvalidOperationException($"vk_descriptor_set_failed: {r}");
            }
            fixed (DescriptorBufferInfo* ip = infos)
            {
                var writes = new WriteDescriptorSet[nb];
                for (int i = 0; i < nb; i++)
                    writes[i] = new WriteDescriptorSet
                    {
                        SType = StructureType.WriteDescriptorSet, DstSet = set, DstBinding = (uint)i,
                        DescriptorCount = 1, DescriptorType = DescriptorType.StorageBuffer, PBufferInfo = &ip[i],
                    };
                fixed (WriteDescriptorSet* wp = writes) _vk.UpdateDescriptorSets(_dev, (uint)nb, wp, 0, null);
            }

            // 着色器模块 + 管线
            ShaderModule module;
            fixed (uint* code = kernel.Words)
            {
                var smci = new ShaderModuleCreateInfo
                {
                    SType = StructureType.ShaderModuleCreateInfo,
                    CodeSize = (nuint)(kernel.Words.Length * 4), PCode = code,
                };
                var r = _vk.CreateShaderModule(_dev, &smci, null, out module);
                if (r != Result.Success) throw new InvalidOperationException($"vk_shader_module_failed: {r}");
            }
            PipelineLayout playout;
            {
                var dsl = layout;
                var plci = new PipelineLayoutCreateInfo
                { SType = StructureType.PipelineLayoutCreateInfo, SetLayoutCount = 1, PSetLayouts = &dsl };
                var r = _vk.CreatePipelineLayout(_dev, &plci, null, out playout);
                if (r != Result.Success) throw new InvalidOperationException($"vk_pipeline_layout_failed: {r}");
            }
            Pipeline pipeline;
            byte[] mainName = { (byte)'m', (byte)'a', (byte)'i', (byte)'n', 0 };
            fixed (byte* mn = mainName)
            {
                var stage = new PipelineShaderStageCreateInfo
                {
                    SType = StructureType.PipelineShaderStageCreateInfo,
                    Stage = ShaderStageFlags.ComputeBit, Module = module, PName = mn,
                };
                var cpci = new ComputePipelineCreateInfo
                { SType = StructureType.ComputePipelineCreateInfo, Stage = stage, Layout = playout, BasePipelineIndex = -1 };
                var r = _vk.CreateComputePipelines(_dev, default, 1u, &cpci, null, out pipeline);
                if (r != Result.Success) throw new InvalidOperationException($"vk_compute_pipeline_failed: {r}");
            }

            // 命令缓冲: barrier(Host→Compute) → bind → dispatch → barrier(Compute→Host)
            CommandBuffer cb;
            {
                var cbai = new CommandBufferAllocateInfo
                { SType = StructureType.CommandBufferAllocateInfo, CommandPool = _pool, Level = CommandBufferLevel.Primary, CommandBufferCount = 1 };
                var r = _vk.AllocateCommandBuffers(_dev, &cbai, out cb);
                if (r != Result.Success) throw new InvalidOperationException($"vk_alloc_command_buffer_failed: {r}");
            }
            {
                var bi = new CommandBufferBeginInfo
                { SType = StructureType.CommandBufferBeginInfo, Flags = CommandBufferUsageFlags.OneTimeSubmitBit };
                var r = _vk.BeginCommandBuffer(cb, &bi);
                if (r != Result.Success) throw new InvalidOperationException($"vk_begin_command_buffer_failed: {r}");
            }
            _vk.CmdBindPipeline(cb, PipelineBindPoint.Compute, pipeline);
            _vk.CmdBindDescriptorSets(cb, PipelineBindPoint.Compute, playout, 0, 1, &set, 0, null);

            var barriers = new BufferMemoryBarrier[nb];
            for (int i = 0; i < nb; i++)
                barriers[i] = new BufferMemoryBarrier
                {
                    SType = StructureType.BufferMemoryBarrier, SrcAccessMask = AccessFlags.HostWriteBit,
                    DstAccessMask = AccessFlags.ShaderReadBit, SrcQueueFamilyIndex = uint.MaxValue,
                    DstQueueFamilyIndex = uint.MaxValue, Buffer = bufs[i], Offset = 0, Size = sizes[i],
                };
            fixed (BufferMemoryBarrier* bp = barriers)
                _vk.CmdPipelineBarrier(cb, PipelineStageFlags.HostBit, PipelineStageFlags.ComputeShaderBit, 0, 0, null, (uint)nb, bp, 0, null);

            uint groups = (uint)((count + kernel.LocalSizeX - 1) / kernel.LocalSizeX);
            _vk.CmdDispatch(cb, groups, 1, 1);

            for (int i = 0; i < nb; i++)
                barriers[i] = new BufferMemoryBarrier
                {
                    SType = StructureType.BufferMemoryBarrier, SrcAccessMask = AccessFlags.ShaderWriteBit,
                    DstAccessMask = AccessFlags.HostReadBit, SrcQueueFamilyIndex = uint.MaxValue,
                    DstQueueFamilyIndex = uint.MaxValue, Buffer = bufs[i], Offset = 0, Size = sizes[i],
                };
            fixed (BufferMemoryBarrier* bp = barriers)
                _vk.CmdPipelineBarrier(cb, PipelineStageFlags.ComputeShaderBit, PipelineStageFlags.HostBit, 0, 0, null, (uint)nb, bp, 0, null);

            _vk.EndCommandBuffer(cb);
            var sw = System.Diagnostics.Stopwatch.StartNew();
            {
                var si = new SubmitInfo { SType = StructureType.SubmitInfo, CommandBufferCount = 1, PCommandBuffers = &cb };
                var r = _vk.QueueSubmit(_queue, 1, &si, default);
                if (r != Result.Success) throw new InvalidOperationException($"vk_queue_submit_failed: {r}");
                r = _vk.QueueWaitIdle(_queue);
                if (r != Result.Success) throw new InvalidOperationException($"vk_queue_wait_idle_failed: {r}");
            }
            sw.Stop();

            for (int i = 0; i < nb; i++)
                fixed (float* dst = buffers[i]) System.Buffer.MemoryCopy(maps[i], dst, (long)sizes[i], (long)sizes[i]);

            _vk.FreeCommandBuffers(_dev, _pool, 1, &cb);
            return new DispatchResult(kernel.Name, count, groups, sw.Elapsed.TotalMilliseconds, count / Math.Max(0.001, sw.Elapsed.TotalMilliseconds));
        }
        finally
        {
            for (int i = 0; i < nb; i++)
            {
                if (maps[i] != null) _vk.UnmapMemory(_dev, mems[i]);
                if (bufs[i].Handle != 0) _vk.DestroyBuffer(_dev, bufs[i], null);
                if (mems[i].Handle != 0) _vk.FreeMemory(_dev, mems[i], null);
            }
        }
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        _vk.DeviceWaitIdle(_dev);
        _vk.DestroyCommandPool(_dev, _pool, null);
        _vk.DestroyDevice(_dev, null);
        _vk.DestroyInstance(_inst, null);
    }
}
