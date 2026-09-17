using System;
using System.IO;
using System.Linq;
using agent.modelqueue;
using Xunit;
namespace agent.tests;

/// <summary>
/// R475 (本侧): R474 真端点暴露的两处缺陷的判据。
///   A. **复述回放取实质答复**: 纯复述轮 (「再讲一遍。」) 的本地消化 = 回放上一条答复原文,
///      但上一条可能是空/模板/空正文徽标 ⇒ 回放会把失败当答复端给用户 (R474 实测 3 轮用户可见徽标被回放)
///      ⇒ 必须撤销 Skip 降级远端, 不得以模板冒充。
///   B. **命中率口径禁 &gt;1**: hit 不可能超过同会话可复用上界 min(prompt, 上一轮 prompt);
///      超出 ⇒ 该轮不适用 K2b (归 shared_prefix 通道), 禁把 &gt;1 灌进红线统计。
///   C. **recover 记账补齐**: `llm_call_recover` 行必须与 `llm_call` 同源落 prompt/缓存字段
///      (R474: recover 行缺字段 ⇒ 产品自记账漏 15,458 prompt tokens = Arole 的 21.8%)。
/// </summary>
[Collection(AgentTelemetryStaticCollection.Name)]
public class R475AccountingTests
{
    private static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln"))) dir = dir.Parent;
        return dir?.FullName ?? ".";
    }

    private static string Src(params string[] parts)
        => SourcePin.TextParts(parts);

    // ---------- A. 回放守卫 ----------

    [Fact]
    public void A1_空_模板_空正文徽标一律不可回放()
    {
        Assert.False(ModelQueueRouter.IsReplayableReply(null));
        Assert.False(ModelQueueRouter.IsReplayableReply(""));
        Assert.False(ModelQueueRouter.IsReplayableReply("   \n\t "));
        Assert.False(ModelQueueRouter.IsReplayableReply(ModelQueueRouter.LocalSkipFallback));            // 模板
        Assert.False(ModelQueueRouter.IsReplayableReply("  " + ModelQueueRouter.LocalSkipFallback + " ")); // 带空白
        Assert.False(ModelQueueRouter.IsReplayableReply(ModelQueueRouter.EmptyBodyBannerPrefix + ", 且自动重试失败 — 请重试或切换模型。"));
        // R478: 徽标文案由定因单源生成 (带真实 finish_reason) —— 不可回放的性质不变, 两个成因各钉一例
        Assert.False(ModelQueueRouter.IsReplayableReply(ModelQueueRouter.EmptyBodyBannerPrefix + EmptyBodyDiagnosis.Banner(EmptyBodyCause.LengthExhausted, "length")));
        Assert.False(ModelQueueRouter.IsReplayableReply(ModelQueueRouter.EmptyBodyBannerPrefix + EmptyBodyDiagnosis.Banner(EmptyBodyCause.ToolCall, "tool_calls")));
    }

    [Fact]
    public void A2_实质答复必须可回放_成对正控()
    {
        Assert.True(ModelQueueRouter.IsReplayableReply("3 加 5 等于 8。"));
        Assert.True(ModelQueueRouter.IsReplayableReply("  ## 结论\n构建命令: dotnet build  "));
        // 徽标**不在开头**的正文 (用户/模型引用了徽标文本) 仍算实质答复 —— 守卫只看首部
        Assert.True(ModelQueueRouter.IsReplayableReply("你刚才看到的提示是「" + ModelQueueRouter.EmptyBodyBannerPrefix + "」, 那是故障。"));
    }

    [Fact]
    public void A3_降级路必须存在且先于打点_R444同族位置纪律()
    {
        var src = Src("src", "agent", "IndustrialAgentV2.cs");
        Assert.Contains("if (!agent.modelqueue.ModelQueueRouter.IsReplayableReply(h0.Content)) continue;", src.Replace("\r", ""));
        Assert.Contains("gate:repeat_no_replayable_prev", src);
        Assert.Contains("RecordRepeatDegrade();", src);
        // 门判打点必须能看到最终 basis (R433/R444 位置纪律): 复述判定块的**结束**须早于 local_turn_gate 打点
        var iRepeat = src.IndexOf("repeatTurnFlag = gateOutcome.Decided", StringComparison.Ordinal);
        var iEmitGate = src.IndexOf("agent.config.AgentTelemetry.Emit(\"local_turn_gate\"", StringComparison.Ordinal);
        var iEmitDegrade = src.IndexOf("\"repeat_degrade_remote\"", StringComparison.Ordinal);
        Assert.True(iRepeat > 0 && iEmitGate > iRepeat && iEmitDegrade > iRepeat && iEmitDegrade < iEmitGate,
            $"位置错误: iRepeat={iRepeat} iDegrade={iEmitDegrade} iGateEmit={iEmitGate}");
        // 撤销 Skip 的判决串必须与 r1 原始 skip 判决不同 (否则 basis 与真实走向相反)
        Assert.DoesNotContain("TurnGateVerdict.Skip, \"gate:repeat_no_replayable_prev\"", src);
    }

    [Fact]
    public void A4_回放候选与执行支同源_禁两处各取历史()
    {
        var src = Src("src", "agent", "IndustrialAgentV2.cs").Replace("\r", "");
        Assert.Equal(2, src.Split("GetConversationHistoryAsync(message.SessionId, ct)").Length - 1);
        // R466 单源教训: 跳过**执行支**内不得再取一次历史 (候选由门控块定好后传出)
        var iSkip = src.LastIndexOf("if (gateOutcome.Decided && gateOutcome.Verdict == agent.modelqueue.TurnGateVerdict.Skip)", StringComparison.Ordinal);
        var iReply = src.IndexOf("\"local_gate_skip_reply\"", StringComparison.Ordinal);
        Assert.True(iSkip > 0 && iReply > iSkip, $"iSkip={iSkip} iReply={iReply}");
        var body = src.Substring(iSkip, iReply - iSkip);
        Assert.DoesNotContain("await GetConversationHistoryAsync(", body);   // 注释提及不算
        Assert.Contains("var localReply = repeatPrevReply ?? await _modelRouter!.ComposeLocalSkipReplyAsync(", body);
    }

    // ---------- B. 命中率口径 ----------

    [Fact]
    public void B1_命中超出同会话上界时有效命中率不适用_禁大于一()
    {
        // R474 实测行: prompt 3,140, 上一轮 2,900, hit 2,944 (= 共享前缀 2,688 + 同会话 256)
        Assert.Equal(2900, PromptCacheKpi.CacheableTokens(3140, 2900));
        Assert.Equal(-1d, PromptCacheKpi.EffectiveHitRate(2944, 2900));      // 旧口径会给出 1.0152
        Assert.True(PromptCacheKpi.ExceedsSameSession(2944, 3140, 2900));
    }

    [Fact]
    public void B2_通道归因与有效命中率同判据_禁各写一份()
    {
        Assert.Equal("shared_prefix", PromptCacheKpi.Channel(3140, 2900, 2944));
        Assert.Equal("same_session", PromptCacheKpi.Channel(3140, 2900, 2880));
        Assert.Equal("same_session", PromptCacheKpi.Channel(3140, 2900));      // 无 hit 上报 ⇒ 保持 R470 行为
        Assert.Equal("shared_prefix", PromptCacheKpi.Channel(3140, 0, 2688));
        Assert.Equal("unknown", PromptCacheKpi.Channel(0, 0, 0));
        // 通道字段: 超上界行 ⇒ 共享前缀通道有值, 同会话通道不适用 (禁双计)
        var kv = PromptCacheKpi.ChannelFields(2944, 196, 3140, 2900).ToDictionary(t => t.Key, t => t.Value);
        Assert.Equal("shared_prefix", kv["cache_channel"]);
        Assert.Equal(2944, kv["shared_prefix_hit_tokens"]);
        var kv2 = PromptCacheKpi.ChannelFields(2880, 260, 3140, 2900).ToDictionary(t => t.Key, t => t.Value);
        Assert.Equal("same_session", kv2["cache_channel"]);
        Assert.Equal(-1, kv2["shared_prefix_hit_tokens"]);
    }

    [Fact]
    public void B3_未上报仍为不适用_不得冒充零()
    {
        Assert.Equal(-1d, PromptCacheKpi.EffectiveHitRate(null, 2900));
        Assert.Equal(-1d, PromptCacheKpi.EffectiveHitRate(-1, 2900));
        Assert.Equal(-1d, PromptCacheKpi.EffectiveHitRate(2944, 0));
        Assert.Equal(0.9931d, PromptCacheKpi.EffectiveHitRate(2880, 2900));  // 未超出 ⇒ 照旧计算
    }

    // ---------- C. recover 记账 ----------

    [Fact]
    public void C1_recover两条路径都必须落prompt与缓存字段()
    {
        var src = Src("src", "agent.modelqueue", "ModelQueueRouter.cs");
        var blocks = src.Split("Emit(\"llm_call_recover\"").Skip(1).ToArray();
        Assert.Equal(2, blocks.Length);                                     // 成功路径 + 异常路径
        foreach (var b in blocks)
        {
            var seg = b.Substring(0, Math.Min(b.Length, 1600));
            Assert.Contains("(\"prompt_tokens\", ", seg);
            Assert.Contains("\"cache_hit_tokens\"", seg);
            Assert.Contains("\"cache_miss_tokens\"", seg);
            Assert.Contains("\"cache_hit_rate\"", seg);
        }
        Assert.DoesNotContain("(\"cache_hit_tokens\", 0)", src);
        Assert.Contains("(\"retry_prompt_tokens\", retried.PromptTokens)", src);   // 成功路径: 重试调用的 prompt 也入账
    }
}
