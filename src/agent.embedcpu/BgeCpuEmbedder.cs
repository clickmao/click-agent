using System.Numerics.Tensors;
using System.Text;

namespace agent.embedcpu;

/// <summary>
/// v0.20.5 R353 (用户钦定): bge 本地 CPU 最小推理 — 纯托管 BERT encoder forward。
/// 架构: bert (bge-small-zh-v1.5, 4 层, 512 dim, 8 头, mean-pool + L2 归一)。
/// 数值: TensorPrimitives SIMD (dot/ scale/ add); 精度 F32 (Q8_0 权重反量化一次, 缓存复用)。
/// 设计: 惰性加载 + 双检锁 (BgeEmbedder 同模式); EmbedAsync 异步入口 — 与召回/压缩主链并行 (R352-b)。
/// </summary>
public sealed class BgeCpuEmbedder : agent.contextgradient.ITextEmbedder, IDisposable
{
    private readonly string _modelPath;
    private readonly object _lock = new();
    private GgufModel? _model;
    private WordPieceTokenizer? _tokenizer;
    private Dictionary<string, float[]>? _weights;
    private bool _initialized;
    private int _dim = 512;
    private int _maxTokens = 510; // +CLS+SEP = 512

    public BgeCpuEmbedder(string modelPath) => _modelPath = modelPath;

    public bool IsAvailable => File.Exists(_modelPath) && new FileInfo(_modelPath).Length > 0;

    private void EnsureInitialized()
    {
        if (_initialized) return;
        lock (_lock)
        {
            if (_initialized) return;
            var model = GgufModel.Load(_modelPath);
            _tokenizer = new WordPieceTokenizer(model.Tokens);
            _dim = (int)model.IntKv.GetValueOrDefault("bert.embedding_length", 512);
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
        if (Trace)
        {
            // 独立重读 cls 行 (绕过缓存) 对照 python ref [-0.1485,0.0568,-0.0262,-0.0437]
            var model = _model!;
            var ti = model.Tensors["token_embd.weight"];
            var rawRow = model.ReadTensor(ti);
            var off = 101 * hidden;
            Console.Error.WriteLine($"cls raw read first4={string.Join(",", rawRow.Skip(off).Take(4).Select(x => x.ToString("F4")))}");
            Console.Error.WriteLine($"row0 raw read first4={string.Join(",", rawRow.Take(4).Select(x => x.ToString("F4")))} (python [PAD] ref: 0.0050,-0.0275,0.0250,0.0350)");
            Console.Error.WriteLine($"cls cache  first4={string.Join(",", tokenEmbd.Skip(off).Take(4).Select(x => x.ToString("F4")))}");
        }
        var posEmbd = _weights["position_embd.weight"];     // [512 pos][512 dim]
        var tokenTypes = _weights["token_types.weight"];    // [512? dim] — type 0
        var h = new float[seq * hidden];
        for (var t = 0; t < seq; t++)
        {
            var tokBase = ids[t] * hidden;
            var posBase = t * hidden;
            var typeBase = 0 * hidden; // 单句 type=0
            for (var d = 0; d < hidden; d++)
                h[t * hidden + d] = tokenEmbd[tokBase + d] + posEmbd[posBase + d] + tokenTypes[typeBase + d];
        }
        // token_embd_norm (R100 旧 gguf 常见; 本文件第一层后归一 — 按张量表 token_embd_norm 存在则先做)
        if (_weights.TryGetValue("token_embd_norm.weight", out var tenW))
        {
            var tenB = _weights["token_embd_norm.bias"];
            LayerNorm(h, tenW, tenB, seq, hidden);
        }

        if (Trace) DebugPool("emb", h, seq, hidden);
        // ② 4 层 transformer
        for (var layer = 0; layer < 4; layer++)
        {
            var blk = $"blk.{layer}.";
            h = TransformerBlock(h, seq, hidden, blk);
            if (Trace) DebugPool($"{blk}", h, seq, hidden);
            if (Trace)
            {
                double mean = 0, sq = 0;
                foreach (var x in h) { mean += x; sq += (double)x * x; }
                Console.Error.WriteLine($"layer{layer}: mean={mean / h.Length:F6} rms={Math.Sqrt(sq / h.Length):F6}");
            }
        }

        // ③ mean pooling (bert.attention.causal=0 → 全 token 平均; GGUF pooling_type=2=MEAN)
        var pooled = new float[hidden];
        for (var t = 0; t < seq; t++)
            TensorPrimitives.Add(pooled, h.AsSpan(t * hidden, hidden), pooled);
        TensorPrimitives.Divide(pooled, (float)seq, pooled);

        // ④ L2 归一
        var norm = TensorPrimitives.Norm(pooled);
        if (norm > 0) TensorPrimitives.Multiply(pooled, 1f / (float)norm, pooled);
        return pooled;
    }

    private static void DebugPool(string tag, float[] h, int seq, int hidden)
    {
        var pooled = new float[hidden];
        for (var t = 0; t < seq; t++)
            TensorPrimitives.Add(pooled, h.AsSpan(t * hidden, hidden), pooled);
        TensorPrimitives.Divide(pooled, seq, pooled);
        var norm = TensorPrimitives.Norm(pooled);
        if (norm > 0) TensorPrimitives.Multiply(pooled, 1f / norm, pooled);
        Console.Error.WriteLine($"[{tag}] pool_norm1 first3={string.Join(",", pooled.Take(3).Select(x => x.ToString("F4")))}");
    }

    private float[] TransformerBlock(float[] h, int seq, int hidden, string blk)
    {
        var heads = 8;
        var headDim = hidden / heads;

        // --- 自注意力 (BERT post-LN: attn → attn_output_norm) ---
        var q = MatMulAdd(h, _weights![$"{blk}attn_q.weight"], _weights[$"{blk}attn_q.bias"], seq, hidden, hidden);
        var k = MatMulAdd(h, _weights[$"{blk}attn_k.weight"], _weights[$"{blk}attn_k.bias"], seq, hidden, hidden);
        var v = MatMulAdd(h, _weights[$"{blk}attn_v.weight"], _weights[$"{blk}attn_v.bias"], seq, hidden, hidden);

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
                for (var j = 0; j < seq; j++)
                {
                    if (row[j] == 0f) continue;
                    var vo = j * hidden + qo;
                    for (var d = 0; d < headDim; d++)
                        attnOut[i * hidden + qo + d] += row[j] * v[vo + d];
                }
            }
        }
        var attnProj = MatMulAdd(attnOut, _weights[$"{blk}attn_output.weight"], _weights[$"{blk}attn_output.bias"], seq, hidden, hidden);
        TensorPrimitives.Add(h, attnProj, h); // residual
        LayerNorm(h, _weights[$"{blk}attn_output_norm.weight"], _weights[$"{blk}attn_output_norm.bias"], seq, hidden);

        // --- FFN (residual → layer_output_norm) ---
        var ffnOut = MatMulAdd(h, _weights[$"{blk}ffn_up.weight"], _weights[$"{blk}ffn_up.bias"], seq, hidden, 2048);
        Gelu(ffnOut);
        var down = MatMulAdd(ffnOut, _weights[$"{blk}ffn_down.weight"], _weights[$"{blk}ffn_down.bias"], seq, 2048, hidden);
        TensorPrimitives.Add(h, down, h); // residual
        LayerNorm(h, _weights[$"{blk}layer_output_norm.weight"], _weights[$"{blk}layer_output_norm.bias"], seq, hidden);
        return h;
    }

    private static float[] MatMulAdd(float[] input, float[] weight, float[] bias, int seq, int inDim, int outDim)
    {
        // GGUF 权重布局 [out, in] 行主序 (llama.cpp 导出惯例): y[o] = Σ_i w[o*inDim+i]*x[i] + b[o]
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
            for (var d = 0; d < hidden; d++)
                row[d] = row[d] * inv * w[d] + b[d];
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
        var max = float.MinValue;
        for (var i = 0; i < row.Length; i++) if (row[i] > max) max = row[i];
        var sum = 0f;
        for (var i = 0; i < row.Length; i++) { row[i] = MathF.Exp(row[i] - max); sum += row[i]; }
        if (sum > 0) TensorPrimitives.Multiply(row, 1f / sum, row);
    }

    private static void Gelu(Span<float> x)
    {
        // tanh 近似 (BERT 标准)
        for (var i = 0; i < x.Length; i++)
        {
            var v = x[i];
            x[i] = 0.5f * v * (1f + MathF.Tanh(0.7978845608f * (v + 0.044715f * v * v * v)));
        }
    }

    public void Dispose() { /* 权重托管内存, GC 回收 */ }
}
