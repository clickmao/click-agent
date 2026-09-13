using System.Numerics.Tensors;

namespace agent.rover.infer;

/// <summary>采样参数 (R400 支持子集: temperature/top-k/top-p/argmax; 惩罚项为后续轮次排除项)。</summary>
public sealed record SamplerOptions(float Temperature = 0.7f, int TopK = 40, float TopP = 0.95f, ulong Seed = 12345);

/// <summary>
/// 确定性采样器: SplitMix64 随机源 (跨平台逐位确定, 不依赖 System.Random 实现细节)。
/// 语义: temperature&lt;=0 ⇒ 贪心 (并列取最小 id); 否则 softmax → top-k → top-p → 归一化 → 逆变换采样。
/// 参考向量 ReferenceVector 由独立 Python 实现给出 (跨实现对账), 见 SamplerTests。
/// </summary>
public sealed class Sampler
{
    /// <summary>SplitMix64 参考输出 (seed=12345, 前 6 个 64 位输出; 独立 Python 实现计算)。</summary>
    public static readonly ulong[] ReferenceVector =
    [
        0x22118258A9D111A0UL,
        0x346EDCE5F713F8EDUL,
        0x1E9A57BC80E6721DUL,
        0x2D160E7E5C3F42CAUL,
        0x81C2E6DC980D78EBUL,
        0x5647E55AD933F62EUL,
    ];

    private const ulong Gamma = 0x9E3779B97F4A7C15UL;

    private readonly SamplerOptions _opt;
    private ulong _state;
    private int[] _idx = [];
    private float[] _probs = [];
    private float[] _scaled = [];

    public Sampler(SamplerOptions options)
    {
        _opt = options;
        _state = options.Seed;
    }

    /// <summary>已消耗的随机数步数 (KPI/证据用)。</summary>
    public long Draws { get; private set; }

    public SamplerOptions Options => _opt;

    /// <summary>SplitMix64 原始输出 (自检/对账用; 不改对象状态)。</summary>
    public static ulong[] SplitMix64Vector(ulong seed, int count)
    {
        ulong s = seed;
        ulong[] outp = new ulong[count];
        for (int i = 0; i < count; i++)
        {
            outp[i] = SplitMix64(ref s);
        }

        return outp;
    }

    /// <summary>取下一个 token id。logits 长度即词表大小。</summary>
    public int Next(ReadOnlySpan<float> logits)
    {
        if (logits.Length == 0)
        {
            throw new ArgumentException("logits 为空", nameof(logits));
        }

        if (_opt.Temperature <= 0f)
        {
            return ArgMax(logits);
        }

        int vocab = logits.Length;
        if (_idx.Length != vocab)
        {
            _idx = new int[vocab];
            _probs = new float[vocab];
            _scaled = new float[vocab];
        }

        float[] scaled = _scaled;
        float invT = 1f / _opt.Temperature;
        for (int i = 0; i < vocab; i++)
        {
            scaled[i] = logits[i] * invT;
        }

        int topK = _opt.TopK <= 0 || _opt.TopK > vocab ? vocab : _opt.TopK;
        int[] idx = _idx;
        for (int i = 0; i < vocab; i++)
        {
            idx[i] = i;
        }

        // 排序: logit 降序, 并列按 id 升序 (全序 ⇒ 结果与排序稳定性无关, 跨平台确定)
        Array.Sort(idx, (a, b) =>
        {
            int c = scaled[b].CompareTo(scaled[a]);
            return c != 0 ? c : a.CompareTo(b);
        });

        int keep = topK;

        // softmax (仅保留集)
        float max = scaled[idx[0]];
        float[] probs = _probs;
        double sum = 0;
        for (int i = 0; i < keep; i++)
        {
            double e = Math.Exp(scaled[idx[i]] - max);
            probs[i] = (float)e;
            sum += e;
        }

        for (int i = 0; i < keep; i++)
        {
            probs[i] = (float)(probs[i] / sum);
        }

        // top-p: 保留累计概率达到 p 的最小前缀
        int keepP = keep;
        if (_opt.TopP > 0f && _opt.TopP < 1f)
        {
            double cum = 0;
            for (int i = 0; i < keep; i++)
            {
                cum += probs[i];
                if (cum >= _opt.TopP)
                {
                    keepP = i + 1;
                    break;
                }
            }
        }

        // 归一化 + 逆变换采样
        double total = 0;
        for (int i = 0; i < keepP; i++)
        {
            total += probs[i];
        }

        double r = NextDouble() * total;
        double acc = 0;
        for (int i = 0; i < keepP; i++)
        {
            acc += probs[i];
            if (acc > r)
            {
                return idx[i];
            }
        }

        return idx[keepP - 1];
    }

    /// <summary>贪心: 最大 logit, 并列取最小 id (TensorPrimitives 提供 SIMD 路径)。</summary>
    public static int ArgMax(ReadOnlySpan<float> logits) => TensorPrimitives.IndexOfMax(logits);

    private double NextDouble() => (NextU64() >> 11) * (1.0 / 9007199254740992.0);

    private ulong NextU64()
    {
        Draws++;
        return SplitMix64(ref _state);
    }

    private static ulong SplitMix64(ref ulong state)
    {
        state += Gamma;
        ulong z = state;
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9UL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBUL;
        return z ^ (z >> 31);
    }
}
