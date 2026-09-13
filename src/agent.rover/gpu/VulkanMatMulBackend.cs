using agent.embedcpu;
using agent.rover.gpu.spirv;

namespace agent.rover.gpu;

/// <summary>
/// BGE 矩阵乘端口的 Vulkan 实现 (R393) —— 把本地 BGE 的 6 个投影矩阵乘 (q/k/v/attn_output/ffn_up/ffn_down)
/// 派发到 Vulkan 计算管线, 前向其余部分 (LayerNorm / 注意力 / GELU / 池化) 仍在 CPU 上执行,
/// 因此 GPU 端口不产生第二份前向语义。
///
/// 与 <see cref="VulkanBackend"/> 的关系: 本类只做"端口适配 + 形状特化内核缓存 + 入参校验",
/// 设备/管线/内存生命周期仍由 VulkanBackend 负责 (零 shell / 零反射)。
/// 数值契约: 内核按 k 顺序单精度累加, CPU 端口用 SIMD 多累加器 ⇒ 两者不逐位相同, 差异量级
/// 为 f32 eps (实测 max|Δ| = 2.5e-7 / 余弦 = 1.000000000), 证据见 agent.rover embed --compare。
/// </summary>
public sealed class VulkanMatMulBackend : IMatMulBackend, IDisposable
{
    readonly VulkanBackend _vk;
    readonly Dictionary<(int In, int Out), Kernels.Kernel> _kernels = new();

    VulkanMatMulBackend(VulkanBackend vk) => _vk = vk;

    /// <summary>端口名 (证据用): 恒为 vulkan。</summary>
    public string Name => "vulkan";

    /// <summary>真机设备信息 (证据用)。</summary>
    public VkDeviceInfo Device => _vk.Info;

    /// <summary>
    /// 打开 Vulkan 端口。<paramref name="o"/> 非空时输出设备枚举/失败原因 (机器可读行)。
    /// 设备不可用时返回 null —— 由调用方显式处置 (绝不静默退回 CPU 冒充 GPU)。
    /// </summary>
    public static VulkanMatMulBackend? TryOpen(TextWriter? o, int deviceIndex = 0)
    {
        var vk = VulkanBackend.TryOpen(o ?? TextWriter.Null, deviceIndex);
        return vk is null ? null : new VulkanMatMulBackend(vk);
    }

    /// <summary>形状特化内核 (inDim×outDim 决定编译期常量, 因而内核内无维度反推)。</summary>
    public Kernels.Kernel KernelFor(int inDim, int outDim)
    {
        var key = (inDim, outDim);
        if (_kernels.TryGetValue(key, out var k)) return k;
        k = Kernels.MatMulBias(inDim, outDim);
        _kernels[key] = k;
        return k;
    }

    /// <summary>y[seq,out] = x·Wᵀ + b, 在 Vulkan 计算管线上执行 (Y 就地写回)。</summary>
    public float[] MatMulAdd(float[] input, float[] weight, float[] bias, int seq, int inDim, int outDim)
    {
        if (weight.Length != outDim * inDim)
            throw new ArgumentException($"vulkan_matmul_weight_shape: got {weight.Length} expect {outDim * inDim}");
        if (input.Length < seq * inDim)
            throw new ArgumentException($"vulkan_matmul_input_shape: got {input.Length} expect {seq * inDim}");
        if (bias.Length != outDim)
            throw new ArgumentException($"vulkan_matmul_bias_shape: got {bias.Length} expect {outDim}");

        var y = new float[seq * outDim];
        var r = _vk.Dispatch(KernelFor(inDim, outDim), new[] { weight, input, bias, y }, seq * outDim);
        LastDispatchMs = r.DispatchMs;
        Dispatches++;
        return y;
    }

    /// <summary>最近一次派发耗时 (ms) —— 证据用。</summary>
    public double LastDispatchMs { get; private set; }

    /// <summary>累计派发次数 —— 证据用。</summary>
    public int Dispatches { get; private set; }

    /// <summary>缓冲池读数 (证据用): 档位数 / 槽位总数 / 租借次数 / 复用次数。槽位恒定 ⇒ 我方无逐次分配。</summary>
    public (int Classes, int Slots, long Leases, int Reuses) PoolStats =>
        (_vk.SlotClasses, _vk.SlotCount, _vk.SlotLeases, _vk.SlotReuses);

    public void Dispose() => _vk.Dispose();
}
