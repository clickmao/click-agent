using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using agent.config;
using agent.llamacpp;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R430 — **本地服务端总槽位必须显式声明** (决策路径逐位可复现的前提)。
///
/// 机检事实 (R430 传输级, eval/rover/r430/probe-r430-concurrent-v2.json):
///   该 llama.cpp 构建 `-np` 默认 = **4** (启动日志 n_slots = 4) ⇒ 门判与关系判官等**并发在途请求**
///   会进同一批 ⇒ 每序列的批形状/分块随调用序列变化 ⇒ 浮点归约顺序变 ⇒
///   **同一 prompt + 同一请求体 (cache_prompt=false, greedy, temp=0) 仍产出不同文本**。
///   ⇒ 判据: 参数表里 `-np` 必须**无条件**出现且默认 = 1 (真串行), 不得依赖构建默认值。
///
/// 负控: Parallel 取 0/负数不得漏成"不传 -np"(那会退回构建默认 4) ⇒ 必须夹到 1。
/// </summary>
public class LocalServerParallelTests
{
    private static LlamaServerOptions Opts(int parallel = 1, bool embedding = false) => new()
    {
        ModelPath = "/tmp/model.gguf",
        Host = "127.0.0.1",
        ContextSize = 4608,
        Threads = 1,
        Parallel = parallel,
        EmbeddingMode = embedding,
    };

    private static List<string> Args(LlamaServerOptions o, bool embedding = false) =>
        LlamaServerHost.BuildArgumentList(o, 12345, embedding);

    private static string ValueAfter(List<string> args, string flag)
    {
        var i = args.IndexOf(flag);
        Assert.True(i >= 0, $"参数表缺 {flag}: {string.Join(' ', args)}");
        Assert.True(i + 1 < args.Count, $"{flag} 缺取值");
        return args[i + 1];
    }

    // T1: 默认必须显式 -np 1 (不得依赖构建默认 4)
    [Fact]
    public void BuildArgs_Default_DeclaresParallelOne()
    {
        var a = Args(Opts());
        Assert.Equal("1", ValueAfter(a, "-np"));
        Assert.Single(a.Where(x => x == "-np"));
    }

    // T2: 显式值必须被尊重 (配置可调)
    [Fact]
    public void BuildArgs_ParallelFour_DeclaresFour() => Assert.Equal("4", ValueAfter(Args(Opts(4)), "-np"));

    // T3 (负控): 非正值不得漏成"不传 -np" ⇒ 夹到 1
    [Theory]
    [InlineData(0)]
    [InlineData(-3)]
    public void BuildArgs_NonPositiveParallel_ClampedToOne(int p)
    {
        var a = Args(Opts(p));
        Assert.Equal("1", ValueAfter(a, "-np"));
        Assert.Single(a.Where(x => x == "-np"));
    }

    // T4: 数值档不回归 (R407 铁律: f32 KV + flash-attn off)
    [Fact]
    public void BuildArgs_PreservesNumericRegime()
    {
        var a = Args(Opts());
        Assert.Equal("f32", ValueAfter(a, "--cache-type-k"));
        Assert.Equal("f32", ValueAfter(a, "--cache-type-v"));
        Assert.Equal("off", ValueAfter(a, "--flash-attn"));
        Assert.Contains("--jinja", a);
        Assert.DoesNotContain("--embeddings", a);
    }

    [Fact]
    public void BuildArgs_EmbeddingMode_AddsEmbeddingsFlag()
    {
        Assert.Contains("--embeddings", Args(Opts(embedding: true), embedding: true));
        Assert.Contains("--embeddings", Args(Opts(embedding: true), embedding: true));
    }

    // T5: 形态自述必须带 np (台账可核)
    [Fact]
    public void Describe_IncludesParallel() => Assert.Contains("np=1", Opts().Describe());

    // T6: config `local.parallel` 解析 + 缺省 1
    [Fact]
    public void ModelCatalog_ParsesLocalParallel()
    {
        var root = Path.Combine(Path.GetTempPath(), "r430np-" + Guid.NewGuid().ToString("N")[..8]);
        var cfg = Path.Combine(root, "config");
        Directory.CreateDirectory(Path.Combine(cfg, "base"));
        Directory.CreateDirectory(Path.Combine(cfg, "modules"));
        Directory.CreateDirectory(Path.Combine(cfg, "runtime"));
        File.WriteAllText(Path.Combine(cfg, "base", "models.yaml"),
            "models:\n  - name: glm-a\n    price: 0.5\nlocal:\n  model_path: /tmp/model.gguf\n  context_size: 4608\n  parallel: 3\n");
        try
        {
            var withParallel = ModelCatalog.Load(new ConfigSnapshot(cfg));
            Assert.Equal(3, withParallel.LocalChannel.Parallel);

            File.WriteAllText(Path.Combine(cfg, "base", "models.yaml"),
                "models:\n  - name: glm-a\n    price: 0.5\nlocal:\n  model_path: /tmp/model.gguf\n  context_size: 4608\n");
            var withoutParallel = ModelCatalog.Load(new ConfigSnapshot(cfg));
            Assert.Equal(1, withoutParallel.LocalChannel.Parallel);
        }
        finally { try { Directory.Delete(root, true); } catch { } }
    }

    [Fact]
    public void Config_Defaults_AreOne() => Assert.Equal(1, new LocalChannelConfig().Parallel);

    // T7: 生成侧/嵌入侧选项默认 1 (与 host 档位一致, 不靠 build 默认)
    [Fact]
    public void Generator_And_Embedder_Options_DefaultToOne()
    {
        // ModelPath 是 required 成员 (llama.cpp 必须知道模型) ⇒ 显式给定后只断言默认档位
        Assert.Equal(1, new LlamaCppGeneratorOptions { ModelPath = "/tmp/m.gguf" }.Parallel);
        Assert.Equal(1, new LlamaCppEmbedderOptions { ModelPath = "/tmp/m.gguf" }.Parallel);
        Assert.Equal(1, new LlamaServerOptions { ModelPath = "/tmp/m.gguf" }.Parallel);
        Assert.NotEqual(4, new LlamaServerOptions { ModelPath = "/tmp/m.gguf" }.Parallel);
    }

    // T8 (机检不变量): 参数表里 `-np` 必须**无条件**添加 —— 防止有人改成 "只当 >0 才传"
    //      (那会让默认路径漏回构建默认 4, 而单测若只测显式值则全绿 ⇒ 空心)。
    [Fact]
    public void HostSource_DeclaresParallelUnconditionally()
    {
        var src = File.ReadAllText(Path.Combine(FindRepoRoot(), "src", "agent.llamacpp", "LlamaServerHost.cs"));
        Assert.Contains("a.Add(\"-np\")", src);
        Assert.DoesNotContain("if (o.Parallel > 0)", src);
        Assert.DoesNotContain("if (Parallel > 0)", src);
        Assert.Contains("Math.Max(1, o.Parallel)", src);
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        return dir?.FullName ?? ".";
    }
}
