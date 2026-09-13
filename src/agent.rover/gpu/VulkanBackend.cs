using System.Text;
using agent.rover.gpu.spirv;
using Silk.NET.Vulkan;

namespace agent.rover.gpu;

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
        byte[] app = Encoding.ASCII.GetBytes("agent.rover");
        byte[] eng = Encoding.ASCII.GetBytes("agent.rover");
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

    /// <summary>按 (内核名, 绑定数) 缓存的管线类资源 —— 生命周期与 backend 一致, Dispose 时统一销毁。</summary>
    sealed class PipeSet
    {
        public DescriptorSetLayout Layout;
        public DescriptorPool Dpool;
        public DescriptorSet Set;
        public ShaderModule Module;
        public PipelineLayout Playout;
        public Pipeline Pipeline;

        public void Dispose(Vk vk, Device dev)
        {
            if (Pipeline.Handle != 0) vk.DestroyPipeline(dev, Pipeline, null);
            if (Playout.Handle != 0) vk.DestroyPipelineLayout(dev, Playout, null);
            if (Module.Handle != 0) vk.DestroyShaderModule(dev, Module, null);
            if (Dpool.Handle != 0) vk.DestroyDescriptorPool(dev, Dpool, null);   // 池销毁即回收其集合
            if (Layout.Handle != 0) vk.DestroyDescriptorSetLayout(dev, Layout, null);
        }
    }

    // ── R393 内存观测 (A/B 三次, 本机 llvmpipe/lavapipe · LLVM 20.1.2, 证据 /tmp/r393/embed_vk_pool.log) ──
    //   改前: 每次派发新建且从不销毁 管线/描述符布局/池/集合/着色器模块/管线布局 (6 个 VkHandle) —— 句柄泄漏
    //   改造① 管线类资源按 (内核名, 绑定数) 缓存            ⇒ RSS 斜率不变 (仍 ≈ 76 KB/次派发)
    //   改造② 设备缓冲按 64 KiB 档位池化 (864 次派发 7 个缓冲, 复用率 99.8%) ⇒ 斜率不变
    //   改造③ 命令缓冲常驻 + ResetCommandPool              ⇒ 斜率不变
    //   ⇒ 我方三类资源均已池化/销毁 (池读数可证), 剩余斜率归属驱动内部实现;
    //     结论: 真 GPU 上必须重测该斜率, 在此之前既不记为我方泄漏, 也不声称已解决。
    readonly Dictionary<(string Kernel, int Buffers), PipeSet> _pipes = new();
    CommandBuffer _cb;
    bool _cbReady;

    /// <summary>池化设备缓冲槽 (Buf + Memory + 持久映射 + 容量档位)。</summary>
    sealed class BufferSlot
    {
        public Silk.NET.Vulkan.Buffer Buf;
        public DeviceMemory Mem;
        public void* Map;
        public ulong Capacity;
        public ulong Class;
    }

    /// <summary>档位大小 = 64 KiB 向上取整 (BGE 形状下档位数 ≤ 约 20 个 ⇒ 池内存有界)。</summary>
    const ulong SlotGranularity = 64 * 1024;

    readonly Dictionary<ulong, List<BufferSlot>> _slots = new();
    readonly List<BufferSlot> _slotAll = new();

    /// <summary>池占用读数 (证据用): 档位数 / 槽位总数 / 租借次数。</summary>
    public int SlotClasses => _slots.Count;
    public int SlotCount => _slotAll.Count;
    public long SlotLeases { get; private set; }
    public int SlotReuses { get; private set; }

    static ulong SlotClass(ulong bytes) => (bytes + SlotGranularity - 1) / SlotGranularity * SlotGranularity;

    BufferSlot AcquireSlot(ulong bytes)
    {
        var cls = SlotClass(bytes);
        if (_slots.TryGetValue(cls, out var free) && free.Count > 0)
        {
            var s = free[^1];
            free.RemoveAt(free.Count - 1);
            SlotLeases++; SlotReuses++;
            return s;
        }

        var slot = new BufferSlot { Capacity = cls, Class = cls };
        var bci = new BufferCreateInfo
        {
            SType = StructureType.BufferCreateInfo, Size = cls,
            Usage = BufferUsageFlags.StorageBufferBit | BufferUsageFlags.TransferSrcBit | BufferUsageFlags.TransferDstBit,
            SharingMode = SharingMode.Exclusive,
        };
        var r = _vk.CreateBuffer(_dev, &bci, null, out slot.Buf);
        if (r != Result.Success) throw new InvalidOperationException($"vk_create_buffer_failed: {r}");
        var req = default(MemoryRequirements);
        _vk.GetBufferMemoryRequirements(_dev, slot.Buf, &req);
        var mai = new MemoryAllocateInfo
        {
            SType = StructureType.MemoryAllocateInfo,
            AllocationSize = req.Size, MemoryTypeIndex = FindMemoryType(req.MemoryTypeBits),
        };
        r = _vk.AllocateMemory(_dev, &mai, null, out slot.Mem);
        if (r != Result.Success) throw new InvalidOperationException($"vk_allocate_memory_failed: {r}");
        _vk.BindBufferMemory(_dev, slot.Buf, slot.Mem, 0);
        void* p;
        r = _vk.MapMemory(_dev, slot.Mem, 0, cls, MemoryMapFlags.None, &p);
        if (r != Result.Success) throw new InvalidOperationException($"vk_map_memory_failed: {r}");
        slot.Map = p;
        _slotAll.Add(slot);
        SlotLeases++;
        return slot;
    }

    void ReleaseSlot(BufferSlot slot)
    {
        if (!_slots.TryGetValue(slot.Class, out var free)) _slots[slot.Class] = free = new List<BufferSlot>();
        free.Add(slot);
    }


    /// <summary>
    /// 按 (内核名, 绑定数) 建/取管线类资源缓存 (R393)。
    /// 原实现每次派发都新建描述符布局/池/集合/着色器模块/管线布局/管线且从不销毁 ——
    /// 这是 6 个 VkHandle/次 的真句柄泄漏 (代码事实), 且每次派发都要重新编译一次 SPIR-V。
    /// 缓存后同形状内核只编译/建一次。
    /// 注意 (R393 实测): 该修复并未改变进程 RSS 随派发次数增长的斜率 ⇒ 斜率不归因于此,
    /// 见下方内存观测块 —— 不把未证明的因果关系写进注释。
    /// </summary>
    PipeSet PipeFor(Kernels.Kernel kernel, int nb)
    {
        var key = (kernel.Name, nb);
        if (_pipes.TryGetValue(key, out var cached)) return cached;

        var p = new PipeSet();
            // 描述符布局 + 池 + 集合
            var bindings = new DescriptorSetLayoutBinding[nb];
            for (int i = 0; i < nb; i++)
                bindings[i] = new DescriptorSetLayoutBinding
                {
                    Binding = (uint)i, DescriptorType = DescriptorType.StorageBuffer,
                    DescriptorCount = 1, StageFlags = ShaderStageFlags.ComputeBit,
                };
            fixed (DescriptorSetLayoutBinding* bp = bindings)
            {
                var dslci = new DescriptorSetLayoutCreateInfo
                { SType = StructureType.DescriptorSetLayoutCreateInfo, BindingCount = (uint)nb, PBindings = bp };
                var r = _vk.CreateDescriptorSetLayout(_dev, &dslci, null, out p.Layout);
                if (r != Result.Success) throw new InvalidOperationException($"vk_descriptor_layout_failed: {r}");
            }

            var poolSizes = new DescriptorPoolSize[nb];
            for (int i = 0; i < nb; i++) poolSizes[i] = new DescriptorPoolSize { Type = DescriptorType.StorageBuffer, DescriptorCount = 1 };
            fixed (DescriptorPoolSize* ps = poolSizes)
            {
                var dpci = new DescriptorPoolCreateInfo
                { SType = StructureType.DescriptorPoolCreateInfo, MaxSets = 1, PoolSizeCount = (uint)nb, PPoolSizes = ps };
                var r = _vk.CreateDescriptorPool(_dev, &dpci, null, out p.Dpool);
                if (r != Result.Success) throw new InvalidOperationException($"vk_descriptor_pool_failed: {r}");
            }

            {
                var dsl = p.Layout;
                var dsai = new DescriptorSetAllocateInfo
                { SType = StructureType.DescriptorSetAllocateInfo, DescriptorPool = p.Dpool, DescriptorSetCount = 1, PSetLayouts = &dsl };
                var r = _vk.AllocateDescriptorSets(_dev, &dsai, out p.Set);
                if (r != Result.Success) throw new InvalidOperationException($"vk_descriptor_set_failed: {r}");
            }
            // 着色器模块 + 管线
            fixed (uint* code = kernel.Words)
            {
                var smci = new ShaderModuleCreateInfo
                {
                    SType = StructureType.ShaderModuleCreateInfo,
                    CodeSize = (nuint)(kernel.Words.Length * 4), PCode = code,
                };
                var r = _vk.CreateShaderModule(_dev, &smci, null, out p.Module);
                if (r != Result.Success) throw new InvalidOperationException($"vk_shader_module_failed: {r}");
            }
            {
                var dsl = p.Layout;
                var plci = new PipelineLayoutCreateInfo
                { SType = StructureType.PipelineLayoutCreateInfo, SetLayoutCount = 1, PSetLayouts = &dsl };
                var r = _vk.CreatePipelineLayout(_dev, &plci, null, out p.Playout);
                if (r != Result.Success) throw new InvalidOperationException($"vk_pipeline_layout_failed: {r}");
            }
            byte[] mainName = { (byte)'m', (byte)'a', (byte)'i', (byte)'n', 0 };
            fixed (byte* mn = mainName)
            {
                var stage = new PipelineShaderStageCreateInfo
                {
                    SType = StructureType.PipelineShaderStageCreateInfo,
                    Stage = ShaderStageFlags.ComputeBit, Module = p.Module, PName = mn,
                };
                var cpci = new ComputePipelineCreateInfo
                { SType = StructureType.ComputePipelineCreateInfo, Stage = stage, Layout = p.Playout, BasePipelineIndex = -1 };
                var r = _vk.CreateComputePipelines(_dev, default, 1u, &cpci, null, out p.Pipeline);
                if (r != Result.Success) throw new InvalidOperationException($"vk_compute_pipeline_failed: {r}");
            }
        _pipes[key] = p;
        return p;
    }

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
        var leased = new BufferSlot[nb];

        // R393: 管线类资源按 (内核名, 绑定数) 缓存 (见 PipeFor); 每次派发只重建 buffer/memory/命令缓冲。
        var pipe = PipeFor(kernel, nb);

        try
        {
            for (int i = 0; i < nb; i++)
            {
                sizes[i] = (ulong)buffers[i].Length * 4;
                // 设备缓冲来自池 (按 64 KiB 档位复用): 消除逐次 CreateBuffer/AllocateMemory/FreeMemory
                // 的分配 churn, 并保证我方不存在逐次句柄累积 (池读数可证: 864 次派发只用 7 个缓冲)。
                // 描述符 Range 仍写精确字节数 ⇒ 内核 ArrayLength 语义不变。
                var slot = AcquireSlot(sizes[i]);
                leased[i] = slot;
                bufs[i] = slot.Buf; mems[i] = slot.Mem; maps[i] = slot.Map;
                fixed (float* src = buffers[i]) System.Buffer.MemoryCopy(src, slot.Map, (long)sizes[i], (long)sizes[i]);
                infos[i] = new DescriptorBufferInfo { Buffer = bufs[i], Offset = 0, Range = sizes[i] };
            }


            // 每次派发重写描述符绑定 (缓冲对象逐次新建); 描述符集合本身来自 PipeFor 缓存。
            fixed (DescriptorBufferInfo* ip = infos)
            {
                var writes = new WriteDescriptorSet[nb];
                for (int i = 0; i < nb; i++)
                    writes[i] = new WriteDescriptorSet
                    {
                        SType = StructureType.WriteDescriptorSet, DstSet = pipe.Set, DstBinding = (uint)i,
                        DescriptorCount = 1, DescriptorType = DescriptorType.StorageBuffer, PBufferInfo = &ip[i],
                    };
                fixed (WriteDescriptorSet* wp = writes) _vk.UpdateDescriptorSets(_dev, (uint)nb, wp, 0, null);
            }

            // 命令缓冲: barrier(Host→Compute) → bind → dispatch → barrier(Compute→Host)
            // 命令缓冲常驻复用 (R393): 消除逐次 Allocate/FreeCommandBuffers 的分配 churn。
            // 池已带 ResetCommandBufferBit, 故 ResetCommandPool 即可安全重录
            // (派发前后都 QueueWaitIdle, 无在飞工作)。
            if (!_cbReady)
            {
                var cbai = new CommandBufferAllocateInfo
                { SType = StructureType.CommandBufferAllocateInfo, CommandPool = _pool, Level = CommandBufferLevel.Primary, CommandBufferCount = 1 };
                var rc = _vk.AllocateCommandBuffers(_dev, &cbai, out _cb);
                if (rc != Result.Success) throw new InvalidOperationException($"vk_alloc_command_buffer_failed: {rc}");
                _cbReady = true;
            }
            else
            {
                var rr = _vk.ResetCommandPool(_dev, _pool, 0);
                if (rr != Result.Success) throw new InvalidOperationException($"vk_reset_command_pool_failed: {rr}");
            }
            var cb = _cb;
            {
                var bi = new CommandBufferBeginInfo
                { SType = StructureType.CommandBufferBeginInfo, Flags = CommandBufferUsageFlags.OneTimeSubmitBit };
                var r = _vk.BeginCommandBuffer(cb, &bi);
                if (r != Result.Success) throw new InvalidOperationException($"vk_begin_command_buffer_failed: {r}");
            }
            _vk.CmdBindPipeline(cb, PipelineBindPoint.Compute, pipe.Pipeline);
            var pset = pipe.Set;
            _vk.CmdBindDescriptorSets(cb, PipelineBindPoint.Compute, pipe.Playout, 0, 1, &pset, 0, null);

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

            return new DispatchResult(kernel.Name, count, groups, sw.Elapsed.TotalMilliseconds, count / Math.Max(0.001, sw.Elapsed.TotalMilliseconds));
        }
        finally
        {
            for (int i = 0; i < nb; i++) if (leased[i] is not null) ReleaseSlot(leased[i]);
        }
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        _vk.DeviceWaitIdle(_dev);
        foreach (var p in _pipes.Values) p.Dispose(_vk, _dev);
        _pipes.Clear();
        foreach (var s in _slotAll)
        {
            if (s.Map != null) _vk.UnmapMemory(_dev, s.Mem);
            if (s.Buf.Handle != 0) _vk.DestroyBuffer(_dev, s.Buf, null);
            if (s.Mem.Handle != 0) _vk.FreeMemory(_dev, s.Mem, null);
        }
        _slotAll.Clear(); _slots.Clear();
        _vk.DestroyCommandPool(_dev, _pool, null);
        _vk.DestroyDevice(_dev, null);
        _vk.DestroyInstance(_inst, null);
    }
}
