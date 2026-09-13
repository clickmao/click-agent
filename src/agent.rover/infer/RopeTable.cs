namespace agent.rover.infer;

/// <summary>
/// RoPE 频率/旋转表。配对约定由 <see cref="RopePairing"/> 按 arch 决定 (权威源见 RopePairing.cs):
///   · NormConsecutive: 第 2j 与第 2j+1 维配对 (llama/deepseek2/granite/…)
///   · NeoxHalf:        第 j 与第 j+n_rot/2 维配对 (qwen2/qwen3/gemma/…)
/// 位置 → cos/sin 预计算一次, 避免在每层每头重复 pow();
/// 频率基/缩放参数全部来自 GGUF metadata (见 <see cref="ModelConfig"/>), 无硬编码。
/// </summary>
public sealed class RopeTable
{
    private readonly int _nRot;
    private readonly float[] _cos;   // [maxPos+1][nRot/2]
    private readonly float[] _sin;
    private readonly int _half;
    private readonly int _maxPos;
    private readonly RopePairing _pairing;

    public int RopeDim => _nRot;
    public int MaxPositions => _maxPos;
    public RopePairing Pairing => _pairing;

    public RopeTable(int nRot, float freqBase, string scaling, float factor, int maxPos, RopePairing pairing)
    {
        if (nRot <= 0 || nRot % 2 != 0) throw new ArgumentException($"rope_dim_invalid: {nRot}");
        if (maxPos <= 0) throw new ArgumentException($"rope_max_pos_invalid: {maxPos}");
        _nRot = nRot;
        _half = nRot / 2;
        _maxPos = maxPos;
        _pairing = pairing;
        _cos = new float[(long)(maxPos + 1) * _half <= int.MaxValue ? (maxPos + 1) * _half : throw new ArgumentException("rope_table_too_large")];
        _sin = new float[_cos.Length];

        bool linear = scaling == "linear" && factor > 0f;
        var invFreq = new float[_half];
        for (int i = 0; i < _half; i++)
        {
            double f = 1.0 / Math.Pow(freqBase, 2.0 * i / nRot);
            if (linear) f /= factor;                 // rope.scaling.type=linear: inv_freq /= factor
            invFreq[i] = (float)f;
        }

        for (int p = 0; p <= maxPos; p++)
        {
            int off = p * _half;
            for (int i = 0; i < _half; i++)
            {
                double theta = (double)p * invFreq[i];
                _cos[off + i] = (float)Math.Cos(theta);
                _sin[off + i] = (float)Math.Sin(theta);
            }
        }
    }

    /// <summary>就地旋转: vec 为 nHeads 个连续 headDim 长的头; 每个头只旋转前 nRot 维。</summary>
    public void Apply(Span<float> vec, int nHeads, int headDim, int pos)
    {
        if (pos < 0 || pos > _maxPos) throw new ArgumentOutOfRangeException(nameof(pos), $"rope_pos_out_of_range: {pos} > {_maxPos}");
        if (vec.Length < nHeads * headDim) throw new ArgumentException($"rope_vec_too_short: {vec.Length} < {nHeads * headDim}");
        int off = pos * _half;
        bool neox = _pairing == RopePairing.NeoxHalf;
        for (int h = 0; h < nHeads; h++)
        {
            var v = vec.Slice(h * headDim, headDim);
            for (int i = 0; i < _half; i++)
            {
                float c = _cos[off + i], s = _sin[off + i];
                // 频次下标恒为 i; 只有取数下标随配对约定变:
                //   NEOX: (i, i+n_rot/2)   NORM: (2i, 2i+1)
                int a = neox ? i : 2 * i;
                int b = neox ? i + _half : 2 * i + 1;
                float x0 = v[a], x1 = v[b];
                v[a] = x0 * c - x1 * s;
                v[b] = x0 * s + x1 * c;
            }
        }
    }

    /// <summary>交叉验证用: 取某个位置第 i 对的 (cos, sin)。</summary>
    public (float Cos, float Sin) At(int pos, int i) => (_cos[pos * _half + i], _sin[pos * _half + i]);

    public int PairCount => _half;
}
