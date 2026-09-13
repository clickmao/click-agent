using System.Numerics.Tensors;

namespace agent.embedcpu;

/// <summary>
/// BGE 前向的矩阵乘累加端口 (可替换执行面: CPU SIMD / Vulkan 计算管线)。
///
/// 语义 (与 GGUF/llama.cpp 导出的权重布局一致): y[seq,out] = x[seq,in] · Wᵀ + b,
/// 其中 W 为 [out,in] 行主序, b 为 [out]。实现必须是纯函数式的 —— 不得改写入参,
/// 且返回数组长度恰为 seq*outDim。
///
/// 端口存在的理由: 本地 BGE (bge-small-zh-v1.5, 4 层 / hidden 512 / ffn 2048) 的算力热点
/// 是每层 6 次 [seq,in]×[in,out] 乘累加 (q/k/v/attn_output/ffn_up/ffn_down)。把这一层抽成端口,
/// 是为了让"同一份前向语义"既能跑 CPU SIMD, 也能跑 Vulkan 计算管线 ——
/// LayerNorm / 注意力 / 池化保持单一实现, GPU 端口因此不产生第二份前向定义 (避免语义漂移)。
/// </summary>
public interface IMatMulBackend
{
    /// <summary>端口名 (证据用): cpu / vulkan。</summary>
    string Name { get; }

    /// <summary>计算 y[seq,out] = x·Wᵀ + b (行主序权重 [out,in])。</summary>
    float[] MatMulAdd(float[] input, float[] weight, float[] bias, int seq, int inDim, int outDim);
}

/// <summary>
/// CPU 端口 (默认): 逐行 y[o] = ⟨w[o], x⟩ + b[o], 内积走 TensorPrimitives.Dot (SIMD 多累加器)。
/// 与 GPU 端口 (内核内按 k 顺序单精度累加) 的舍入路径不同 ⇒ 对账判据是差异 ≈ f32 eps 且余弦 = 1.0,
/// 不是逐位相同 (把"逐位一致"写成判据会制造假红/假绿, 故显式声明)。
/// </summary>
public sealed class CpuMatMulBackend : IMatMulBackend
{
    /// <summary>无状态单例 (线程安全: 只读入参 + 局部输出)。</summary>
    public static readonly CpuMatMulBackend Instance = new();

    public string Name => "cpu";

    public float[] MatMulAdd(float[] input, float[] weight, float[] bias, int seq, int inDim, int outDim)
    {
        var output = new float[seq * outDim];
        for (var t = 0; t < seq; t++)
        {
            var x = input.AsSpan(t * inDim, inDim);
            var y = output.AsSpan(t * outDim, outDim);
            bias.CopyTo(y);
            for (var o = 0; o < outDim; o++)
                y[o] += TensorPrimitives.Dot(weight.AsSpan(o * inDim, inDim), x);
        }
        return output;
    }
}
