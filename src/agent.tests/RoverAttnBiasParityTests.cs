using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using agent.rover.gguf;
using agent.rover.infer;
using Xunit;

namespace agent.tests;

/// <summary>
/// R407 · qwen2 前向对账第一站: **attn bias 的层归属**。
///
/// 背景 (R406 归因遗留): 同 prompt / 同 GGUF chat template / 同模型, llama.cpp b1-4df29be
/// 输出连贯推理 @17 tok/s, 本引擎输出 `bur'heads …` @0.47 tok/s ⇒ 判定为引擎缺陷 (前向/张量侧)。
/// 定位结论: ForwardPass 旧实现 <c>MaybeLoadBias()</c> 只读 <c>blk.0.&lt;suffix&gt;</c> 并把**同一份**
/// 向量喂给全部 28 层; qwen2 每层 bias 逐字节不同 (实测 max|Δ| q=121.7 / k=407.1 / v=10.6),
/// 形状检查与 all-or-none 检查全都放行 ⇒ 不抛错、只静默算错 (「自洽≠正确」第三例)。
///
/// 预注册判据 (跑之前定死):
///  ① 逐层互异: 每个 suffix 的 28 层 bias 的 sha256 去重数 == NLayer (==1 即回到旧缺陷);
///  ② 内容绑定 (独立读): <c>AttnBias(l,s)</c> 的每个分量必须逐位等于**测试自己**从 GGUF 读出的
///     <c>blk.l.&lt;suffix&gt;</c> F32 字节 —— 不是相信实现, 而是拿文件当第三方 oracle;
///  ③ 形状绑定: bias 维度 == ModelConfig 推出的 QElems/KvElems, 且 == 同层权重张量的输出维
///     (GQA 若被误读成 12 头, KvElems 会变 1536 ⇒ 此断言必红);
///  ④ 缺省路径: 文件里没有 <c>attn_output.bias</c> ⇒ 端口必须返回 null (不许悄悄造一个);
///  ⑤ 契约: 未知 which / 越界 layer 必须抛 (不许返回 blk.0 兜底)。
/// 模型缺失时写 skip 标记并显式返回, 不静默通过。
/// </summary>
public class RoverAttnBiasParityTests
{
    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        if (dir is null) throw new DirectoryNotFoundException("找不到仓库根 (agent.sln)");
        return dir.FullName;
    }

    private static string ModelPath() =>
        Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R1_MODEL")
        ?? "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf";

    private static readonly (string Which, string Suffix)[] Suffixes =
    [
        ("q", "attn_q.bias"),
        ("k", "attn_k.bias"),
        ("v", "attn_v.bias"),
    ];

    [Fact]
    public void Qwen2_AttnBias_IsPerLayer_AndMatchesGgufBytes()
    {
        var path = ModelPath();
        var evidDir = Path.Combine(FindRepoRoot(), "eval", "rover", "r407");
        Directory.CreateDirectory(evidDir);
        var evidPath = Path.Combine(evidDir, "attn-bias-parity.json");
        if (!File.Exists(path))
        {
            File.WriteAllText(evidPath, "{\"skipped\":\"model missing at " + path.Replace("\\", "/") + "\"}");
            return;
        }

        using var g = GgufReader.Open(path);
        var cfg = ModelConfig.From(g);
        var fwd = new ForwardPass(g, cfg, 64, 64L * 1024 * 1024, dropPages: false);

        var evidence = new Dictionary<string, object>
        {
            ["model"] = path,
            ["arch"] = cfg.Arch,
            ["n_layer"] = cfg.NLayer,
            ["hidden"] = cfg.Hidden,
            ["n_head"] = cfg.NHead,
            ["n_head_kv"] = cfg.NHeadKv,
            ["gqa_group"] = cfg.GqaGroup,
            ["q_elems"] = cfg.QElems,
            ["kv_elems"] = cfg.KvElems,
            ["criteria"] = "per-layer distinct sha256 == NLayer; bit-exact vs independent GGUF read; dims bound to weight output dims",
            ["suffixes"] = new Dictionary<string, object>(),
        };
        var sfx = (Dictionary<string, object>)evidence["suffixes"];

        // ③ GQA 形状绑定: 配置推出的 KV 元素数必须等于同层权重张量的**输出维** (从文件读, 不是写死)
        Assert.Equal((int)g.Require("blk.0.attn_k.weight").Dims[1], cfg.KvElems);
        Assert.Equal((int)g.Require("blk.0.attn_q.weight").Dims[1], cfg.QElems);

        foreach (var (which, suffix) in Suffixes)
        {
            int expectDim = which == "q" ? cfg.QElems : cfg.KvElems;
            var layer0 = fwd.AttnBias(0, which);
            Assert.True(layer0.HasValue, $"bias_absent: which={which} (文件有该 bias, 端口却返回 null)");
            var l0 = layer0!.Value.ToArray();

            var hashes = new HashSet<string>(StringComparer.Ordinal);
            float maxAbsDiffVsLayer0 = 0f;

            for (int l = 0; l < cfg.NLayer; l++)
            {
                var info = g.Require($"blk.{l}.{suffix}");
                Assert.Equal("F32", info.Type.ToString());
                Assert.Equal(1, info.Dims.Length);
                Assert.Equal(expectDim, (int)info.Dims[0]);

                var raw = g.TensorWindow(info).ToArray();
                var expected = MemoryMarshal.Cast<byte, float>(raw).ToArray();
                Assert.Equal(expectDim, expected.Length);

                var actual = fwd.AttnBias(l, which);
                Assert.True(actual.HasValue, $"bias_absent: layer={l} which={which}");
                var av = actual!.Value.Span;
                Assert.Equal(expected.Length, av.Length);

                // ② 与文件逐位对账 (独立读; 若实现回退成复用 blk.0, 这里必红)
                for (int i = 0; i < expected.Length; i++)
                    Assert.True(expected[i] == av[i],
                        $"bias_value_mismatch: layer={l} which={which} dim={i} file={expected[i]} port={av[i]}");

                hashes.Add(Convert.ToHexString(SHA256.HashData(raw)));
                if (l > 0)
                    for (int i = 0; i < expected.Length; i++)
                        maxAbsDiffVsLayer0 = Math.Max(maxAbsDiffVsLayer0, Math.Abs(expected[i] - l0[i]));
            }

            // ① 逐层互异 (=1 即旧缺陷: 全层共用 blk.0)
            Assert.True(hashes.Count == cfg.NLayer,
                $"bias_not_per_layer: which={which} distinct={hashes.Count} n_layer={cfg.NLayer}");
            // 反向负控: 层间差异必须**实测非零**, 否则「逐层读取」退化成与复用等价 (空心通过)
            Assert.True(maxAbsDiffVsLayer0 > 1e-6f,
                $"layer_alias_equivalent: which={which} max_abs_diff_vs_layer0={maxAbsDiffVsLayer0}");

            sfx[which] = new Dictionary<string, object>
            {
                ["suffix"] = suffix,
                ["dim"] = expectDim,
                ["distinct_sha256"] = hashes.Count,
                ["max_abs_diff_vs_layer0"] = maxAbsDiffVsLayer0,
                ["raw_read"] = "GgufReader.TensorWindow (测试独立读取)",
            };
        }

        // ④ 缺省路径: 文件里没有的 bias, 端口必须是 null (不许凭空造 [0,...,0])
        bool hasOBias = g.Find("blk.0.attn_output.bias") is not null;
        evidence["has_attn_output_bias"] = hasOBias;
        for (int l = 0; l < cfg.NLayer; l++)
            Assert.Equal(hasOBias, fwd.AttnBias(l, "o").HasValue);

        // ⑤ 契约: 未知 which / 越界 layer 抛 (不许静默兜底)
        Assert.Throws<ArgumentOutOfRangeException>(() => { var _ = fwd.AttnBias(0, "zzz"); });
        Assert.Throws<ArgumentOutOfRangeException>(() => { var _ = fwd.AttnBias(-1, "q"); });
        Assert.Throws<ArgumentOutOfRangeException>(() => { var _ = fwd.AttnBias(cfg.NLayer, "q"); });

        evidence["verdict"] = "PASS: per-layer bias bound to file bytes";
        File.WriteAllText(evidPath, JsonSerializer.Serialize(evidence, new JsonSerializerOptions { WriteIndented = true }));
    }
}
