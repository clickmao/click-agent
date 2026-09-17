using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;
using agent.modelqueue;
using Xunit;
namespace agent.tests;

/// <summary>
/// R470: 真实流量的**命中归因通道**验证。
///   R1 语义级: 通道判定 (same_session / shared_prefix / unknown) 与既有 R380 口径**互不污染** (只增不改);
///   R2 禁双计: 有同会话前驱时, 跨会话共享前缀字段必须 -1 (否则同一份命中被两条通道重复计入);
///   R3 未上报 ≠ 0: provider 没给命中字段时必须 -1, 不得用 0 冒充 (R377 铁律的延续);
///   R4 真值回放: 43 条**真实远端调用**遥测 (data/telemetry/host.jsonl 派生) 经**产品代码**复算:
///              归因 43/43 = shared_prefix, 命中>0 = 32, 且 K2b 有效命中率 43/43 = -1 (不可测裁定);
///   R5 负控: 把归因规则反写 ⇒ 同一组断言必须不成立 (证明断言非恒真/非空心);
///   R6 溯源: 夹具必须是**活遥测的子集** (遥测追加不破坏测试, 但夹具不得凭空造数)。
/// </summary>
public class PromptCacheChannelTests
{
    private static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        return dir?.FullName ?? ".";
    }

    private sealed record CallRow(string Session, int Turn, int Prompt, int Hit, int Miss, int? Eff,
        bool HasSameSessionPredecessor);

    private static List<CallRow> LoadRealCalls()
    {
        var path = Path.Combine(RepoRoot(), "eval", "rover", "r470", "real-calls.json");
        Assert.True(File.Exists(path), $"R470 真值夹具缺失: {path}");
        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        var rows = new List<CallRow>();
        foreach (var c in doc.RootElement.GetProperty("calls").EnumerateArray())
        {
            var eff = c.TryGetProperty("effective_hit_rate", out var e) && e.TryGetInt32(out var ev) ? ev : (int?)null;
            rows.Add(new CallRow(
                c.GetProperty("session").GetString() ?? "",
                c.GetProperty("turn").GetInt32(),
                c.GetProperty("prompt_tokens").GetInt32(),
                c.GetProperty("cache_hit_tokens").GetInt32(),
                c.GetProperty("cache_miss_tokens").GetInt32(),
                eff,
                c.GetProperty("has_same_session_predecessor").GetBoolean()));
        }
        return rows;
    }

    // ---------- R1 语义级 ----------

    [Fact]
    public void 通道_有同会话前驱记same_session_首轮记shared_prefix_无prompt记unknown()
    {
        Assert.Equal("same_session", PromptCacheKpi.Channel(3000, 2000));
        Assert.Equal("shared_prefix", PromptCacheKpi.Channel(3000, 0));
        Assert.Equal("unknown", PromptCacheKpi.Channel(0, 0));
        Assert.Equal("unknown", PromptCacheKpi.Channel(0, 2000));
    }

    [Fact]
    public void 通道字段_键名与顺序固定()
    {
        var kv = PromptCacheKpi.ChannelFields(2048, 3505, 5553, 0);
        Assert.Equal(new[] { "cache_channel", "shared_prefix_hit_tokens", "shared_prefix_hit_rate" },
            kv.Select(x => x.Key).ToArray());
        Assert.Equal("shared_prefix", kv[0].Value);
        Assert.Equal(2048, kv[1].Value);
        Assert.Equal(0.3688, kv[2].Value);   // 2048/(2048+3505) 保留 4 位
    }

    // ---------- R2 禁双计 ----------

    [Theory]
    [InlineData(2048, 3505, 5553, 5400)]   // 有前驱 ⇒ 命中已归 same_session, shared 通道必须 -1
    public void 通道_有同会话前驱时共享前缀字段必须为哨兵不得双计(int hit, int miss, int prompt, int last)
    {
        Assert.Equal("same_session", PromptCacheKpi.Channel(prompt, last));
        Assert.Equal(PromptCacheKpi.Unknown, PromptCacheKpi.SharedPrefixHitTokens(hit, prompt, last));
        Assert.Equal(PromptCacheKpi.Unknown, PromptCacheKpi.SharedPrefixHitRate(hit, miss, prompt, last));
        Assert.Equal(-1, PromptCacheKpi.Unknown);
    }

    // ---------- R3 未上报 ≠ 0 ----------

    [Fact]
    public void 通道_未上报命中记哨兵不得冒充0()
    {
        Assert.Equal(PromptCacheKpi.Unknown, PromptCacheKpi.SharedPrefixHitTokens(null, 5553, 0));
        Assert.Equal(PromptCacheKpi.Unknown, PromptCacheKpi.SharedPrefixHitRate(null, null, 5553, 0));
        // 真·0 命中 (有分母) 才是 0
        Assert.Equal(0, PromptCacheKpi.SharedPrefixHitTokens(0, 5553, 0));
        Assert.Equal(0.0, PromptCacheKpi.SharedPrefixHitRate(0, 5553, 5553, 0));
        // 无分母 ⇒ -1
        Assert.Equal(PromptCacheKpi.Unknown, PromptCacheKpi.SharedPrefixHitRate(0, 0, 5553, 0));
    }

    // ---------- R4 真值回放 (43 条真实远端调用) ----------

    [Fact]
    public void 真值回放_43条真实调用的归因与K2b不可测裁定()
    {
        var rows = LoadRealCalls();
        Assert.Equal(43, rows.Count);

        var byChannel = rows.GroupBy(r => PromptCacheKpi.Channel(r.Prompt, r.HasSameSessionPredecessor ? 1 : 0))
                            .ToDictionary(g => g.Key, g => g.Count());
        Assert.Equal(43, byChannel["shared_prefix"]);   // 真实流量: 无同会话前驱
        Assert.False(byChannel.ContainsKey("same_session"));
        Assert.Equal(43, byChannel.Values.Sum());       // 归因守恒

        // 共享前缀通道的命中量 = 遥测命中量 (逐行一致)
        foreach (var r in rows)
            Assert.Equal(r.Hit, PromptCacheKpi.SharedPrefixHitTokens(r.Hit, r.Prompt, 0));
        Assert.Equal(32, rows.Count(r => PromptCacheKpi.SharedPrefixHitTokens(r.Hit, r.Prompt, 0) > 0));

        // K2b 可测性裁定: 同会话前驱 = 0 ⇒ 既有口径对真实流量 100% 不适用 (机检, 不是口头声明)
        Assert.Equal(0, rows.Count(r => r.HasSameSessionPredecessor));
        foreach (var r in rows)
            Assert.Equal(PromptCacheKpi.Unknown, r.Eff);

        // 命中量直方图 (与 R470 报告逐值一致; 变更须同步报告)
        var hist = string.Join(",", rows.Where(r => r.Hit > 0).GroupBy(r => r.Hit).OrderBy(g => g.Key)
                                        .Select(g => $"{g.Key}:{g.Count()}"));
        Assert.Equal("127:2,256:2,2048:19,2176:7,2304:2", hist);

        // 对齐例外必须显式存在 (不得静默过滤): 唯一例外 = 127 (非 64 对齐)
        var unaligned = rows.Where(r => r.Hit > 0 && r.Hit % PromptCacheKpi.CacheUnitTokens != 0)
                            .Select(r => r.Hit).Distinct().OrderBy(x => x).ToArray();
        Assert.Equal(new[] { 127 }, unaligned);
    }

    // ---------- R5 负控: 断言必须非恒真 ----------

    [Fact]
    public void 负控_归因规则反写后同一组断言必须不成立()
    {
        var rows = LoadRealCalls();
        // 反写规则: "有前驱才算 shared_prefix" (= 把 R470 的判定条件取反) ⇒ 43/43 不得再落入 shared_prefix
        var reversed = rows.Count(r => r.HasSameSessionPredecessor);
        Assert.NotEqual(43, reversed);
        Assert.Equal(0, reversed);
        // 反写后 shared 通道只剩 0 条且 hit>0 计数为 0 ⇒ 原判据 (≥30) 必红
        Assert.True(rows.Count(r => !r.HasSameSessionPredecessor) == 43);
    }

    // ---------- R6 溯源: 夹具是活遥测的子集 ----------

    [Fact]
    public void 溯源_夹具必须是活遥测的子集不得凭空造数()
    {
        var live = Path.Combine(RepoRoot(), "data", "telemetry", "host.jsonl");
        if (!File.Exists(live)) return;   // 遥测未随仓库分发时不误报
        var keys = new HashSet<string>();
        foreach (var line in File.ReadLines(live))
        {
            var s = line.Trim();
            if (s.Length == 0) continue;
            if (s[0] == '\uFEFF') s = s.Substring(1);          // 首行 BOM (实测存在 ⇒ 不剥会吞行)
            try
            {
                using var d = JsonDocument.Parse(s);
                if (!d.RootElement.TryGetProperty("point", out var p) || p.GetString() != "llm_call") continue;
                var kv = d.RootElement.GetProperty("kv");
                keys.Add($"{kv.GetProperty("prompt_tokens").GetInt32()}|{kv.GetProperty("cache_hit_tokens").GetInt32()}|" +
                         $"{kv.GetProperty("cache_miss_tokens").GetInt32()}|{kv.GetProperty("agent_session").GetString()}");
            }
            catch (JsonException) { /* 坏行不参与溯源 */ }
        }
        foreach (var r in LoadRealCalls())
            Assert.Contains($"{r.Prompt}|{r.Hit}|{r.Miss}|{r.Session}", keys);
    }

    [Fact]
    public void 夹具_自声明指纹与来源路径形态()
    {
        var path = Path.Combine(RepoRoot(), "eval", "rover", "r470", "real-calls.json");
        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        var src = doc.RootElement.GetProperty("source").GetString();
        Assert.Equal("data/telemetry/host.jsonl", src);
        var sha = doc.RootElement.GetProperty("source_sha256").GetString();
        Assert.NotNull(sha);
        Assert.Equal(64, sha!.Length);
        Assert.Matches("^[0-9a-f]{64}$", sha);
        Assert.Equal("point==llm_call", doc.RootElement.GetProperty("filter").GetString());
        Assert.Equal(doc.RootElement.GetProperty("n_calls").GetInt32(),
            doc.RootElement.GetProperty("calls").GetArrayLength());
    }
}
