using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using agent.modelqueue;
using Xunit;
namespace agent.tests;

/// <summary>
/// R377 (用户钦定): **prompt 缓存命中率纳入优化 KPI**。
///   R1 解析级: provider usage 里的 prompt_cache_hit_tokens / prompt_cache_miss_tokens 必须被真实解析;
///   R2 语义级: **未上报 ≠ 0 命中** —— 缺字段时哨兵 -1, 不得用 0 冒充 (否则"没测到"读成"命中率 0%");
///   R3 接线级: 三处 data-carrying llm_call 打点都真的带上三元组 (源码扫描, 防"助手写了但没人调用");
///   R4 负向控制: 篡改命中率算法 / 去掉打点字段 → 必须变红。
/// </summary>
public class PromptCacheKpiTests
{
    private const string DsUsageJson = """
    {"id":"x","object":"chat.completion","model":"deepseek-flash","choices":[{"index":0,"message":{"role":"assistant","content":"hi"},"finish_reason":"stop"}],
     "usage":{"prompt_tokens":3000,"completion_tokens":120,"total_tokens":3120,
              "prompt_cache_hit_tokens":2400,"prompt_cache_miss_tokens":600}}
    """;

    private const string NoCacheUsageJson = """
    {"id":"y","object":"chat.completion","model":"gpt-6","choices":[{"index":0,"message":{"role":"assistant","content":"ok"},"finish_reason":"stop"}],
     "usage":{"prompt_tokens":500,"completion_tokens":50,"total_tokens":550}}
    """;

    private static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        return dir?.FullName ?? ".";
    }

    [Fact]
    public void 解析_上报缓存字段时命中与未命中都被读取()
    {
        var parsed = JsonSerializer.Deserialize(DsUsageJson, ModelQueueJsonContext.Default.OpenAIChatResponse);
        Assert.NotNull(parsed?.Usage);
        Assert.Equal(2400, parsed!.Usage!.PromptCacheHitTokens);
        Assert.Equal(600, parsed.Usage.PromptCacheMissTokens);
        Assert.Equal(3000, parsed.Usage.PromptTokens);
    }

    [Fact]
    public void 解析_未上报缓存字段时为null而非0()
    {
        var parsed = JsonSerializer.Deserialize(NoCacheUsageJson, ModelQueueJsonContext.Default.OpenAIChatResponse);
        Assert.NotNull(parsed?.Usage);
        Assert.Null(parsed!.Usage!.PromptCacheHitTokens);
        Assert.Null(parsed.Usage.PromptCacheMissTokens);
    }

    [Theory]
    [InlineData(2400, 600, 0.8)]
    [InlineData(0, 1000, 0.0)]     // 真·0 命中 (有分母) → 0, **不是**哨兵
    [InlineData(1000, 0, 1.0)]     // 全命中
    [InlineData(1, 2, 0.3333)]
    public void 命中率_有分母时按命中占比计算(int hit, int miss, double expected)
    {
        Assert.Equal(expected, PromptCacheKpi.HitRate(hit, miss));
    }

    [Theory]
    [InlineData(null, 500)]
    [InlineData(500, null)]
    [InlineData(null, null)]
    [InlineData(0, 0)]
    public void 命中率_未上报或无分母记哨兵不得冒充0(int? hit, int? miss)
    {
        Assert.Equal(PromptCacheKpi.Unknown, PromptCacheKpi.HitRate(hit, miss));
        Assert.Equal(-1, PromptCacheKpi.Unknown);
    }

    [Fact]
    public void 打点字段_三元组固定且未上报记哨兵()
    {
        var kv = PromptCacheKpi.Fields(2400, 600);
        Assert.Equal(new[] { "cache_hit_tokens", "cache_miss_tokens", "cache_hit_rate" }, kv.Select(x => x.Key).ToArray());
        Assert.Equal(2400, kv[0].Value);
        Assert.Equal(600, kv[1].Value);
        Assert.Equal(0.8, kv[2].Value);

        var unknown = PromptCacheKpi.Fields(null, null);
        Assert.Equal(-1, unknown[0].Value);
        Assert.Equal(-1, unknown[1].Value);
        Assert.Equal(-1.0, unknown[2].Value);
    }

    [Fact]
    public void 接线_三处llm_call打点都带缓存KPI()
    {
        var src = File.ReadAllText(Path.Combine(RepoRoot(), "src", "agent.modelqueue", "ModelQueueRouter.cs"));
        // 按**打点块**配对断言 (R377 负向控制教训: 只数 `PromptCacheKpi.Fields(` 出现次数会漏掉
        // "算了但没铺进去" —— 变异 3 曾以 0 红通过, 即空心断言)。
        var blocks = src.Split("Emit(\"llm_call\"").Skip(1).ToArray();
        var dataBlocks = blocks.Where(b => b.Contains("(\"total_tokens\", ")).ToArray();
        Assert.Equal(3, dataBlocks.Length);                     // 带真实响应对象的三处
        foreach (var b in dataBlocks)
        {
            // R380 加强: 三处都要同时铺 R377 三元组 + R380 二元组 (只铺前三个 → "算了不用"复发)
            // R470 再加强: 还必须铺 R470 通道三元组 (channel/shared_prefix_hit_tokens/shared_prefix_hit_rate)
            Assert.Contains("cacheKv[0], cacheKv[1], cacheKv[2], effKv[0], effKv[1], chanKv[0], chanKv[1], chanKv[2]", b);
            // R476: 还必须在同一条打点里铺**分档判定** 7 字段 (档/档来源/上限/分档目标/余量/实测增量/分档判决)
            Assert.Matches(@"bandKv2?\[0\], bandKv2?\[1\], bandKv2?\[2\], bandKv2?\[3\], bandKv2?\[4\], bandKv2?\[5\], bandKv2?\[6\]\);", b);
        }
        Assert.Equal(3, src.Split("var effKv = PromptCacheKpi.EffectiveFields(").Length - 1);
        Assert.Equal(3, src.Split("var cacheKv = PromptCacheKpi.Fields(").Length - 1);
        Assert.Equal(3, src.Split("var chanKv = PromptCacheKpi.ChannelFields(").Length - 1);   // R470 接线
        Assert.Equal(3, src.Split("PromptCacheRedline.BandFields(").Length - 1);   // R476 接线: 三处同源
        Assert.Equal(3, src.Split("var bandKv").Length - 1);                        // 主调用 bandKv + 两处回退 bandKv2
        Assert.DoesNotContain("(\"cache_hit_rate\", 0)", src);   // 不得硬编码 0 冒充未上报
        Assert.DoesNotContain("(\"cache_ceiling\", 0)", src);    // R476 同上: 上限未知一律 -1
        Assert.Contains("CacheHitTokens = parsed?.Usage?.PromptCacheHitTokens", src);
    }
}
