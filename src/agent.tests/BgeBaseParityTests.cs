using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.Json;
using agent.embedcpu;
using agent.rag;
using Xunit;

namespace agent.tests;

/// <summary>
/// R404 (用户钦定): 优化后 bge 的**跨实现对账** —— 本仓纯托管 BERT 前向 (agent.embedcpu)
/// vs Python 侧 llama.cpp 产出的冻结向量。两个独立实现必须落在同一语义空间。
///
/// 预注册判据 (跑之前定死):
///   ① 架构参数必须等于模型元数据 (bge-base-zh-v1.5: 768 维 / 12 层 / 12 头 / FFN 3072)
///      —— 原实现写死 4 层/8 头/2048, 换模型会静默算错;
///   ② 逐向量余弦 cos ≥ 0.99 且维度 = 768;
///   ③ 同文本两次嵌入逐位一致 (确定性);
///   ④ 端口真实派发计数 = 层数×6×文本数×重复数 (防空心判定)。
/// 模型缺失时显式跳过并落盘标记, 不静默通过。
/// </summary>
public class BgeBaseParityTests
{
    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        if (dir == null) throw new DirectoryNotFoundException("找不到仓库根 (agent.sln)");
        return dir.FullName;
    }

    private static readonly string Repo = FindRepoRoot();
    private const int SampleCount = 12;

    [Fact]
    public void BgeBase_Arch_PythonOracleParity_Determinism_PortUsage()
    {
        var modelPath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            ".agentframework", "models", "bge-base-zh-v1.5-q8.gguf");
        var evidDir = Path.Combine(Repo, "eval", "bge", "r404");
        Directory.CreateDirectory(evidDir);
        var evidPath = Path.Combine(evidDir, "csharp-bgebase-parity.json");

        if (!File.Exists(modelPath))
        {
            File.WriteAllText(evidPath, "{\"skipped\":\"model missing at " + modelPath.Replace("\\", "/") + "\"}");
            return;
        }

        var cacheDir = Path.Combine(Repo, "data", "bge", "cache");
        var qvecFile = Directory.GetFiles(cacheDir, "bge-base-zh-v1.5-q8__fuse_queries_*_120_*.f32").FirstOrDefault();
        var queriesPath = Path.Combine(Repo, "eval", "bge", "fixtures", "queries.jsonl");
        if (qvecFile is null || !File.Exists(queriesPath))
        {
            File.WriteAllText(evidPath, "{\"skipped\":\"oracle vectors/fixture missing\"}");
            return;
        }

        var qtexts = new List<string>();
        foreach (var line in File.ReadLines(queriesPath))
            if (!string.IsNullOrWhiteSpace(line))
                using (var d = JsonDocument.Parse(line))
                    qtexts.Add(d.RootElement.GetProperty("query").GetString()!);
        var cached = ReadVecCache(qvecFile);
        Assert.Equal(120, cached.Count);

        using var emb = new BgeCpuEmbedder(modelPath);

        // ① 架构参数 = 模型元数据 (不再是写死值)
        Assert.Equal(768, emb.Dimension);
        Assert.Equal(12, emb.Layers);
        Assert.Equal(12, emb.Heads);
        Assert.Equal(3072, emb.FfnDim);

        var worstCos = 1.0;
        var allBitwise = true;
        var worstIdx = -1;
        var n = Math.Min(SampleCount, qtexts.Count);
        for (var i = 0; i < n; i++)
        {
            var v = emb.Embed(qtexts[i]);
            Assert.Equal(768, v.Length);
            var cos = FusionMath.Cosine(v, cached[i]);
            if (cos < worstCos) { worstCos = cos; worstIdx = i; }

            // ③ 确定性: 同文本再嵌一次必须逐位一致
            var v2 = emb.Embed(qtexts[i]);
            for (var d = 0; d < v.Length; d++)
                if (BitConverter.SingleToUInt32Bits(v[d]) != BitConverter.SingleToUInt32Bits(v2[d])) { allBitwise = false; break; }
        }

        // ② 跨实现语义一致 (独立实现: 本仓托管 BERT vs llama.cpp)
        Assert.True(worstCos >= 0.99,
            $"C# bge-base 与 Python/llama.cpp 向量余弦低于 0.99: worst={worstCos:F6} (q#{worstIdx})");
        Assert.True(allBitwise, "同文本两次嵌入不是逐位一致 (确定性判据失败)");

        // ④ 端口真实派发: 层数×6×文本数×重复数 (每文本嵌 2 次)
        var expected = (long)emb.Layers * 6 * n * 2;
        Assert.Equal(expected, emb.MatMulCalls);

        var evid = new System.Text.StringBuilder();
        evid.Append("{\"kind\":\"csharp_bgebase_parity\",\"ts\":\"")
            .Append(DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture)).Append("\",");
        evid.Append("\"model\":\"").Append(Path.GetFileName(modelPath)).Append("\",");
        evid.Append("\"layers\":").Append(emb.Layers).Append(",\"heads\":").Append(emb.Heads);
        evid.Append(",\"dim\":").Append(emb.Dimension).Append(",\"ffn\":").Append(emb.FfnDim).Append(',');
        evid.Append("\"samples\":").Append(n).Append(',');
        evid.Append("\"worst_cos_vs_llamacpp\":").Append(worstCos.ToString("F6", CultureInfo.InvariantCulture)).Append(',');
        evid.Append("\"worst_index\":").Append(worstIdx).Append(',');
        evid.Append("\"deterministic_bitwise\":").Append(allBitwise ? "true" : "false").Append(',');
        evid.Append("\"matmul_calls\":").Append(emb.MatMulCalls).Append(',');
        evid.Append("\"matmul_expected\":").Append(expected).Append('}');
        File.WriteAllText(evidPath, evid.ToString());
    }

    private static List<float[]> ReadVecCache(string path)
    {
        Assert.True(BitConverter.IsLittleEndian, "缓存为小端 float32; 大端机需转换");
        var bytes = File.ReadAllBytes(path);
        var n = (int)BitConverter.ToInt64(bytes, 0);
        var d = (int)BitConverter.ToInt64(bytes, 8);
        Assert.Equal(16 + (long)n * d * 4, bytes.LongLength);
        var outv = new List<float[]>(n);
        for (var i = 0; i < n; i++)
        {
            var v = new float[d];
            Buffer.BlockCopy(bytes, 16 + i * d * 4, v, 0, d * 4);
            outv.Add(v);
        }
        return outv;
    }
}
