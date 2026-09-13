namespace clickrover.infer;

/// <summary>
/// RoPE 频率/旋转表 (LLaMA NORM 配对: 第 i 维与第 i+n_rot/2 维配对, 非 GPT-NeoX 的交错配对)。
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

    public int RopeDim => _nRot;
    public int MaxPositions => _maxPos;

    public RopeTable(int nRot, float freqBase, string scaling, float factor, int maxPos)
    {
        if (nRot <= 0 || nRot % 2 != 0) throw new ArgumentException($"rope_dim_invalid: {nRot}");
        if (maxPos <= 0) throw new ArgumentException($"rope_max_pos_invalid: {maxPos}");
        _nRot = nRot;
        _half = nRot / 2;
        _maxPos = maxPos;
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
        for (int h = 0; h < nHeads; h++)
        {
            var v = vec.Slice(h * headDim, headDim);
            for (int i = 0; i < _half; i++)
            {
                float c = _cos[off + i], s = _sin[off + i];
                float x0 = v[i], x1 = v[i + _half];
                v[i] = x0 * c - x1 * s;
                v[i + _half] = x0 * s + x1 * c;
            }
        }
    }

    /// <summary>交叉验证用: 取某个位置第 i 对的 (cos, sin)。</summary>
    public (float Cos, float Sin) At(int pos, int i) => (_cos[pos * _half + i], _sin[pos * _half + i]);

    public int PairCount => _half;
}
