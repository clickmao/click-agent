using System.Numerics.Tensors;
using System.Text;

namespace agent.embedcpu;

/// <summary>
/// v0.20.5 R353 (用户钦定): bge 本地 CPU 最小推理 — 纯托管 BERT encoder forward。
/// 架构: bert (bge-small-zh-v1.5, 4 层, 512 dim, 8 头, CLS-pool + L2 归一 — 官方 1_Pooling cls_token=true)。
/// 数值: TensorPrimitives SIMD (dot/ scale/ add); 精度 F32 (Q8_0 权重反量化一次, 缓存复用)。
/// 设计: 惰性加载 + 双检锁 (BgeEmbedder 同模式); EmbedAsync 异步入口 — 与召回/压缩主链并行 (R352-b)。
/// </summary>
public sealed class BgeCpuEmbedder : agent.contextgradient.ITextEmbedder, IDisposable
{
    private readonly string _modelPath;
    private readonly IMatMulBackend _mm;
    private readonly object _lock = new();
    private GgufModel? _model;
    private WordPieceTokenizer? _tokenizer;
    private Dictionary<string, float[]>? _weights;
    private bool _initialized;
    private int _dim = 512;
    private int _layers = 4;
    private int _heads = 8;
    private int _ffn = 2048;
    private int _maxTokens = 510; // +CLS+SEP = 512
    private long _matMulCalls;

    /// <summary>R404: 真实矩阵乘派发次数 (端口确实被使用 —— 对账防空心)。
    /// 期望值 = 层数 × 6 (q/k/v/attn_output/ffn_up/ffn_down) × 文本数 × 重复数；
    /// 若层数被写死错 (如 12 层模型只跑 4 层), 该计数会与期望不符 ⇒ 缺陷当场暴露。</summary>
    public long MatMulCalls => Interlocked.Read(ref _matMulCalls);

    private float[] Mm(float[] input, float[] weight, float[] bias, int seq, int inDim, int outDim)
    {
        Interlocked.Increment(ref _matMulCalls);
        return _mm.MatMulAdd(input, weight, bias, seq, inDim, outDim);
    }

    /// <summary>R404: 架构参数只读出口 (证据/对账用) — 全部来自 GGUF 元数据, 不再硬编码。
    /// 读取即触发初始化: 否则在 Embed 之前打印会拿到字段默认值 (假证据)。</summary>
    public int Dimension { get { EnsureInitialized(); return _dim; } }
    public int Layers { get { EnsureInitialized(); return _layers; } }
    public int Heads { get { EnsureInitialized(); return _heads; } }
    public int FfnDim { get { EnsureInitialized(); return _ffn; } }
    public int MaxTokens { get { EnsureInitialized(); return _maxTokens; } }

    public BgeCpuEmbedder(string modelPath)
        : this(modelPath, null)
    {
    }

    /// <summary>构造: <paramref name="matmul"/> 为矩阵乘执行端口 (null ⇒ CPU/TensorPrimitives)。</summary>
    public BgeCpuEmbedder(string modelPath, IMatMulBackend? matmul)
    {
        _modelPath = modelPath;
        _mm = matmul ?? CpuMatMulBackend.Instance;
    }

    public bool IsAvailable => File.Exists(_modelPath) && new FileInfo(_modelPath).Length > 0;

    /// <summary>当前矩阵乘端口名 (cpu/vulkan) —— 证据用, 不参与计算。</summary>
    public string MatMulBackendName => _mm.Name;

    private void EnsureInitialized()
    {
        if (_initialized) return;
        lock (_lock)
        {
            if (_initialized) return;
            var model = GgufModel.Load(_modelPath);
            _tokenizer = new WordPieceTokenizer(model.Tokens);
            // R404 (真缺陷修复): 原实现把 bge-small 的 (4 层/8 头/FFN 2048) 写死在代码里 ——
            // 换成 bge-base (12 层/12 头/FFN 3072) 会**静默**只算 4 层、按 8 头切 head_dim、
            // 并按 2048 读 FFN 权重 ⇒ 向量错但无报错。架构参数一律以 GGUF 元数据为权威源。
            _dim = (int)model.IntKv.GetValueOrDefault("bert.embedding_length", 512);
            _layers = (int)model.IntKv.GetValueOrDefault("bert.block_count", 4);
            _heads = Math.Max(1, (int)model.IntKv.GetValueOrDefault("bert.attention.head_count", 8));
            _ffn = (int)model.IntKv.GetValueOrDefault("bert.feed_forward_length", 2048);
            _maxTokens = Math.Min((int)model.IntKv.GetValueOrDefault("bert.context_length", 512) - 2, 510);
            // 预加载全部张量 (Q8_0 反量化; ~30MB F32 常驻 — 与原 BgeEmbedder 同级)
            _weights = new Dictionary<string, float[]>(model.Tensors.Count);
            foreach (var (name, ti) in model.Tensors)
                _weights[name] = model.ReadTensor(ti);
            _model = model;
            _initialized = true;
        }
    }

    /// <summary>嵌入 (异步入口 — 调用方在召回/压缩主链中以 Task 并行, 不阻塞主链)。</summary>
    public Task<float[]> EmbedAsync(string text, CancellationToken ct = default)
        => Task.Run(() => Embed(text), ct);

    public static bool Trace;

    public float[] Embed(string text)
    {
        EnsureInitialized();
        var ids = _tokenizer!.Encode(text);
        if (Trace) Console.Error.WriteLine($"ids[{ids.Length}]={string.Join(",", ids.Take(12))}...");
        var seq = ids.Length;
        var hidden = _dim;

        // ① embedding 查表 + 位置嵌入 + token_type
        var tokenEmbd = _weights!["token_embd.weight"];     // [512 vocab] 行主序: token*512+d
        var posEmbd = _weights["position_embd.weight"];     // [512 pos][512 dim]
        var tokenTypes = _weights["token_types.weight"];    // [512? dim] — type 0
        var h = new float[seq * hidden];
        for (var t = 0; t < seq; t++)
        {
            var dst = h.AsSpan(t * hidden, hidden);
            tokenEmbd.AsSpan(ids[t] * hidden, hidden).CopyTo(dst);        // token 段
            TensorPrimitives.Add(dst, posEmbd.AsSpan(t * hidden, hidden), dst);   // + position
            TensorPrimitives.Add(dst, tokenTypes.AsSpan(0, hidden), dst);         // + token_type 0
        }
        // token_embd_norm (R100 旧 gguf 常见; 本文件第一层后归一 — 按张量表 token_embd_norm 存在则先做)
        if (_weights.TryGetValue("token_embd_norm.weight", out var tenW))
        {
            var tenB = _weights["token_embd_norm.bias"];
            LayerNorm(h, tenW, tenB, seq, hidden);
        }

        // ② transformer 层 (层数来自 GGUF bert.block_count — R404 去硬编码)
        for (var layer = 0; layer < _layers; layer++)
        {
            var blk = $"blk.{layer}.";
            h = TransformerBlock(h, seq, hidden, blk);
            if (Trace)
            {
                double mean = 0, sq = 0;
                foreach (var x in h) { mean += x; sq += (double)x * x; }
                Console.Error.WriteLine($"layer{layer}: mean={mean / h.Length:F6} rms={Math.Sqrt(sq / h.Length):F6}");
            }
        }

        // ③ pooling — R356 审计修正: BGE 官方 1_Pooling/config.json = pooling_mode_cls_token:true
        // (HF BAAI/bge-small-zh-v1.5 模型卡实证; mean=false)。旧实现误用 mean (GGUF 元数据
        // pooling_type=2 系转换器默认值, 非 HF 语义) → 无关对 cos 虚高 0.86 的根因。
        // BGE 语义: [CLS] 位置的最后隐藏态 = 句表示。
        var pooled = new float[hidden];
        h.AsSpan(0, hidden).CopyTo(pooled);

        // ④ L2 归一
        var norm = TensorPrimitives.Norm(pooled);
        if (norm > 0) TensorPrimitives.Multiply(pooled, 1f / (float)norm, pooled);
        return pooled;
    }

    private float[] TransformerBlock(float[] h, int seq, int hidden, string blk)
    {
        var heads = _heads;                 // R404: 头数来自 GGUF (原写死 8 = 只对 bge-small 成立)
        var headDim = hidden / heads;

        // --- 自注意力 (BERT post-LN: attn → attn_output_norm) ---
        var q = Mm(h, _weights![$"{blk}attn_q.weight"], _weights[$"{blk}attn_q.bias"], seq, hidden, hidden);
        var k = Mm(h, _weights[$"{blk}attn_k.weight"], _weights[$"{blk}attn_k.bias"], seq, hidden, hidden);
        var v = Mm(h, _weights[$"{blk}attn_v.weight"], _weights[$"{blk}attn_v.bias"], seq, hidden, hidden);

        var attnOut = new float[seq * hidden];
        var scale = 1f / MathF.Sqrt(headDim);
        for (var hd = 0; hd < heads; hd++)
        {
            var qo = hd * headDim;
            var scores = new float[seq * seq];
            for (var i = 0; i < seq; i++)
                for (var j = 0; j < seq; j++)
                {
                    var qi = i * hidden + qo;
                    var kj = j * hidden + qo;
                    scores[i * seq + j] = scale * TensorPrimitives.Dot(
                        q.AsSpan(qi, headDim), k.AsSpan(kj, headDim));
                }
            for (var i = 0; i < seq; i++)
            {
                var row = scores.AsSpan(i * seq, seq);
                SoftMax(row);
                var dst = attnOut.AsSpan(i * hidden + qo, headDim);
                var tmp = headDim <= 128 ? stackalloc float[headDim] : new float[headDim];
                for (var j = 0; j < seq; j++)
                {
                    var w = row[j];
                    if (w == 0f) continue;
                    // SIMD: tmp = w * v[vo..]; dst += tmp
                    TensorPrimitives.Multiply(v.AsSpan(j * hidden + qo, headDim), w, tmp);
                    TensorPrimitives.Add(dst, tmp, dst);
                }
            }
        }
        var attnProj = Mm(attnOut, _weights[$"{blk}attn_output.weight"], _weights[$"{blk}attn_output.bias"], seq, hidden, hidden);
        TensorPrimitives.Add(h, attnProj, h); // residual
        LayerNorm(h, _weights[$"{blk}attn_output_norm.weight"], _weights[$"{blk}attn_output_norm.bias"], seq, hidden);

        // --- FFN (residual → layer_output_norm) ---
        var ffnOut = Mm(h, _weights![$"{blk}ffn_up.weight"], _weights[$"{blk}ffn_up.bias"], seq, hidden, _ffn);
        Gelu(ffnOut);
        var down = Mm(ffnOut, _weights[$"{blk}ffn_down.weight"], _weights[$"{blk}ffn_down.bias"], seq, _ffn, hidden);
        TensorPrimitives.Add(h, down, h); // residual
        LayerNorm(h, _weights[$"{blk}layer_output_norm.weight"], _weights[$"{blk}layer_output_norm.bias"], seq, hidden);
        return h;
    }

    private static void LayerNorm(float[] h, float[] w, float[] b, int seq, int hidden)
    {
        var eps = 1e-12f;
        for (var t = 0; t < seq; t++)
        {
            var row = h.AsSpan(t * hidden, hidden);
            var mean = TensorPrimitives.Average(row);
            TensorPrimitives.Subtract(row, mean, row);
            var varr = TensorPrimitives.SumOfSquares(row) / hidden;
            var inv = 1f / MathF.Sqrt(varr + eps);
            TensorPrimitives.Multiply(row, inv, row);
            TensorPrimitives.Multiply(row, w, row);   // 逐元素 ∘ w (SIMD)
            TensorPrimitives.Add(row, b, row);
        }
    }

    private static float[] LayerNormCopy(float[] h, float[] w, float[] b, int seq, int hidden)
    {
        var output = new float[h.Length];
        Array.Copy(h, output, h.Length);
        LayerNorm(output, w, b, seq, hidden);
        return output;
    }

    private static void SoftMax(Span<float> row)
    {
        var max = TensorPrimitives.Max(row);
        TensorPrimitives.Subtract(row, max, row);
        TensorPrimitives.Exp(row, row);
        var sum = TensorPrimitives.Sum(row);
        if (sum > 0) TensorPrimitives.Multiply(row, 1f / sum, row);
    }

    private static void Gelu(Span<float> x)
    {
        // tanh 近似 (BERT 标准) — 全 SIMD: t = tanh(0.7979*(v + 0.044715v³)); x = 0.5v(1+t) = 0.5v + 0.5v*t
        var n = x.Length;
        Span<float> t = n <= 4096 ? stackalloc float[n] : new float[n];
        // t = v²
        TensorPrimitives.Multiply(x, x, t);
        // t = 0.044715 v³ = 0.044715 v² * v
        TensorPrimitives.Multiply(t, 0.044715f, t);
        TensorPrimitives.Multiply(t, x, t);
        // t = v + t → 乘 c → tanh
        TensorPrimitives.Add(t, x, t);
        TensorPrimitives.Multiply(t, 0.7978845608f, t);
        TensorPrimitives.Tanh(t, t);
        // t = 0.5 * v * t ; x = 0.5v + t
        TensorPrimitives.Multiply(x, 0.5f, x);
        TensorPrimitives.Multiply(t, x, t);   // t = 0.5v * t
        TensorPrimitives.Add(x, t, x);
    }


    public void Dispose() { /* 权重托管内存, GC 回收 */ }
}
