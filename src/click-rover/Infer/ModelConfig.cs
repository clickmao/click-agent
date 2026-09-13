using clickrover.gguf;

namespace clickrover.infer;

/// <summary>
/// 前向推理配置: 全部来自 GGUF metadata (零硬编码)。任何缺失/不自洽都在构造期抛错,
/// 不做"猜一个默认值继续跑"的降级 —— 静默降级会产出看起来合理但错误的数值。
/// </summary>
public sealed class ModelConfig
{
    public required string Arch { get; init; }
    public required string Name { get; init; }
    public required int NLayer { get; init; }
    public required int Hidden { get; init; }
    public required int Ffn { get; init; }
    public required int NHead { get; init; }
    public required int NHeadKv { get; init; }
    /// <summary>Q/K 每头维度 = attention.key_length</summary>
    public required int HeadDim { get; init; }
    /// <summary>V 每头维度 = attention.value_length</summary>
    public required int ValueDim { get; init; }
    /// <summary>参与旋转的维度数 = rope.dimension_count (≤ HeadDim)</summary>
    public required int RopeDim { get; init; }
    public required int Vocab { get; init; }
    public required int Ctx { get; init; }
    public required float RmsEps { get; init; }
    public required float RopeBase { get; init; }
    /// <summary>rope.scaling.type: none | linear (其余在构造期抛错, 不静默按 none 处理)</summary>
    public required string RopeScaling { get; init; }
    public required float RopeFactor { get; init; }
    /// <summary>true = 无 output.weight, 复用 token_embd 作 lm_head</summary>
    public required bool TiedOutput { get; init; }
    /// <summary>有 output.weight 且与 token_embd 形状一致</summary>
    public required bool HasOutputTensor { get; init; }

    public int QElems => NHead * HeadDim;
    public int KvElems => NHeadKv * HeadDim;
    /// <summary>1/sqrt(head_dim)</summary>
    public float AttnScale => 1f / MathF.Sqrt(HeadDim);
    /// <summary>每多少个 query head 共享一个 kv head (GQA 分组; MHA 时为 1)</summary>
    public int GqaGroup => NHead / NHeadKv;

    public string LayerPrefix(int l) => $"blk.{l}.";

    /// <summary>从已解析的 GGUF 头部装配配置, 并与张量目录交叉校验 (形状不符即抛)。</summary>
    public static ModelConfig From(GgufReader r)
    {
        string arch = r.GetString("general.architecture")
            ?? throw new InvalidDataException("cfg_missing: general.architecture");
        string name = r.GetString("general.name") ?? "(unnamed)";

        int L = Req(r, $"{arch}.block_count");
        int hidden = Req(r, $"{arch}.embedding_length");
        int ffn = Req(r, $"{arch}.feed_forward_length");
        int nHead = Req(r, $"{arch}.attention.head_count");
        int nHeadKv = Req(r, $"{arch}.attention.head_count_kv");
        int ctx = Req(r, $"{arch}.context_length");
        float eps = ReqF(r, $"{arch}.attention.layer_norm_rms_epsilon");
        float ropeBase = ReqF(r, $"{arch}.rope.freq_base");

        int headDim = Opt(r, $"{arch}.attention.key_length", hidden / nHead);
        int valDim = Opt(r, $"{arch}.attention.value_length", hidden / nHead);
        int ropeDim = Opt(r, $"{arch}.rope.dimension_count", headDim);
        if (ropeDim > headDim || ropeDim % 2 != 0)
            throw new InvalidDataException($"cfg_bad_rope_dim: rope_dim={ropeDim} head_dim={headDim}");

        string scaling = r.GetString($"{arch}.rope.scaling.type") ?? "none";
        float factor = (float)(r.TryGetFloat($"{arch}.rope.scaling.factor", out var f) ? f : 0.0);
        if (scaling is not ("none" or "linear"))
            throw new NotSupportedException($"rope_scaling_unsupported: {scaling} (只实现 none/linear, 不静默近似)");

        int vocab = Opt(r, $"{arch}.vocab_size", 0);
        var embd = r.Find("token_embd.weight")
            ?? throw new InvalidDataException("cfg_missing_tensor: token_embd.weight");
        if (vocab == 0) vocab = (int)embd.Rows;
        if (embd.Dims.Length != 2 || embd.Dims[0] != hidden || embd.Dims[1] != vocab)
            throw new InvalidDataException(
                $"cfg_shape_mismatch: token_embd dims=[{string.Join(",", embd.Dims)}] expect=[{hidden},{vocab}]");

        var outT = r.Find("output.weight");
        bool tied = outT is null;
        if (outT is { } ot && (ot.Dims.Length != 2 || ot.Dims[0] != hidden || ot.Dims[1] != vocab))
            throw new InvalidDataException(
                $"cfg_shape_mismatch: output dims=[{string.Join(",", ot.Dims)}] expect=[{hidden},{vocab}]");

        var cfg = new ModelConfig
        {
            Arch = arch, Name = name, NLayer = L, Hidden = hidden, Ffn = ffn,
            NHead = nHead, NHeadKv = nHeadKv, HeadDim = headDim, ValueDim = valDim,
            RopeDim = ropeDim, Vocab = vocab, Ctx = ctx, RmsEps = eps, RopeBase = ropeBase,
            RopeScaling = scaling, RopeFactor = factor,
            TiedOutput = tied, HasOutputTensor = outT is not null,
        };
        cfg.Validate(r);
        return cfg;
    }

    /// <summary>逐层张量形状与 cfg 对齐性检查 (第 0 层即代表全部层, 抽样成本低但能抓住布局错)。</summary>
    private void Validate(GgufReader r)
    {
        if (NHead % NHeadKv != 0)
            throw new InvalidDataException($"cfg_gqa_mismatch: n_head={NHead} n_head_kv={NHeadKv}");
        (string, long, long)[] want =
        {
            ("attn_q.weight", Hidden, QElems),
            ("attn_k.weight", Hidden, KvElems),
            ("attn_v.weight", Hidden, KvElems),
            ("attn_output.weight", QElems, Hidden),
            ("ffn_gate.weight", Hidden, Ffn),
            ("ffn_up.weight", Hidden, Ffn),
            ("ffn_down.weight", Ffn, Hidden),
            ("attn_norm.weight", -1, Hidden),
            ("ffn_norm.weight", -1, Hidden),
        };
        foreach (var (suffix, cols, rows) in want)
        {
            var t = r.Find("blk.0." + suffix)
                ?? throw new InvalidDataException($"cfg_missing_tensor: blk.0.{suffix}");
            if (cols >= 0)
            {
                if (t.Dims.Length != 2 || t.Dims[0] != cols || t.Dims[1] != rows)
                    throw new InvalidDataException(
                        $"cfg_shape_mismatch: blk.0.{suffix} dims=[{string.Join(",", t.Dims)}] expect=[{cols},{rows}]");
            }
            else if (t.Dims.Length != 1 || t.Dims[0] != rows)
                throw new InvalidDataException(
                    $"cfg_shape_mismatch: blk.0.{suffix} dims=[{string.Join(",", t.Dims)}] expect=[{rows}]");
        }
        var onorm = r.Find("output_norm.weight")
            ?? throw new InvalidDataException("cfg_missing_tensor: output_norm.weight");
        if (onorm.Dims.Length != 1 || onorm.Dims[0] != Hidden)
            throw new InvalidDataException($"cfg_shape_mismatch: output_norm dims=[{string.Join(",", onorm.Dims)}]");
    }

    private static int Req(GgufReader r, string key) =>
        r.TryGetLong(key, out var v) ? (int)v : throw new InvalidDataException($"cfg_missing: {key}");

    private static int Opt(GgufReader r, string key, int fallback) =>
        r.TryGetLong(key, out var v) ? (int)v : fallback;

    private static float ReqF(GgufReader r, string key) =>
        r.TryGetFloat(key, out var v) ? (float)v : throw new InvalidDataException($"cfg_missing: {key}");

    public IEnumerable<string> Lines()
    {
        yield return $"cfg{{arch={Arch} name={Name} layers={NLayer} hidden={Hidden} ffn={Ffn} " +
                     $"n_head={NHead} n_head_kv={NHeadKv} gqa_group={GqaGroup} head_dim={HeadDim} value_dim={ValueDim}}}";
        yield return $"cfg{{vocab={Vocab} ctx={Ctx} rope_dim={RopeDim} rope_base={RopeBase:R} " +
                     $"rope_scaling={RopeScaling} rope_factor={RopeFactor:R} rms_eps={RmsEps:R} " +
                     $"attn_scale={AttnScale:R} tied_embeddings={TiedOutput}}}";
    }
}
