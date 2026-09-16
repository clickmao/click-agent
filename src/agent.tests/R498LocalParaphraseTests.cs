using System;
using System.Linq;
using agent.context;
using agent.modelqueue;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// R498 候选③ (R413 主线补口): **内容承载的本地生成通道** —— 判据 / 守卫 / 闸 / 结算类的机检。
///
/// R497 遗留缺口: 本地消化通道只有「模板 ack」与「原样回放」两条, 都是**零生成**的;
/// 「同义改写族」(换个说法) 因无内容承载的生成能力而无法吸收 (吸收即退化成回放/模板 = R488 退化)。
/// 本轮补上: 以 r1 对**上一条实质答复**做改写, 并用结构不变量守卫 (标识符守恒/禁增、动作声明禁增、
/// 长度带、无问号、无思考链泄漏) fail-closed 兜住 —— 破一条即拒 ⇒ 调用方降级远端。
///
/// 诚实边界 (写进报告, 不冒充「语义等价已证明」): 守卫检的是**结构不变量**, 不是语义等价;
/// 语义正确性只由同网格人工质量细读取证 (本轮未做真机同窗 ⇒ 见下轮候选)。
/// </summary>
public sealed class R498LocalParaphraseTests
{
    private const string Src = "本地通道 r1 已接入链管道: 命中率 = 1−新/前缀, 配置文件 agent.host.csproj 未改动。";

    // ── ① 族判据 ────────────────────────────────────────────────────────────
    [Theory]
    [InlineData("换个说法")]
    [InlineData("换一种说法")]
    [InlineData("换种说法。")]
    [InlineData("换个说法吧")]
    [InlineData("用别的方式说一遍")]
    [InlineData("重新表述一下")]
    [InlineData("换种表述")]
    [InlineData("换个方式说")]
    public void 改写族_吸收(string msg) => Assert.True(LocalParaphraseChannel.IsPureParaphrase(msg), msg);

    [Theory]
    [InlineData("换个说法说下部署进度")]                 // 含内容字 (部/署/进/度) ⇒ 新诉求 ⇒ 不吸收
    [InlineData("换个说法总结 512 行")]                  // 含数字 ⇒ 不吸收
    [InlineData("换个说法，为什么？")]                   // 问号 ⇒ 不吸收
    [InlineData("换个说法 abc")]                         // ASCII ⇒ 不吸收
    [InlineData("换个说法的具体实现路径与取舍是什么")]   // 超长 ⇒ 不吸收
    [InlineData("")]
    [InlineData("   ")]
    [InlineData(null)]
    public void 改写族_不吸收(string? msg) => Assert.False(LocalParaphraseChannel.IsPureParaphrase(msg), msg);

    [Fact]
    public void 两族不得有交集_且复述族优先()
    {
        // else-if 链里复述族在前 ⇒ 必须保证不存在「两族都真」的输入, 否则改写族会被静默吞掉。
        string?[] probes =
        {
            "再讲一遍", "重说一次", "说一遍", "嗯", "收到", "换个说法", "换一种说法",
            "用别的方式说一遍", "重新表述", "再讲一遍吧", "换个说法吧",
        };
        foreach (var p in probes)
            Assert.False(TurnGateJudge.IsPureRepeat(p) && LocalParaphraseChannel.IsPureParaphrase(p),
                $"两族同时判真: {p}");
        // 显式: 改写族的合法输入不得被判为复述族 (否则走回放, 不是改写)
        Assert.False(TurnGateJudge.IsPureRepeat("换个说法"));
        Assert.False(TurnGateJudge.IsPureRepeat("用别的方式说一遍"));
    }

    // ── ② 闸 (单源组合 ShouldAbsorb) ────────────────────────────────────────
    [Fact]
    public void 闸口径_只有字面_1_算开()
    {
        Assert.True(LocalParaphraseChannel.IsEnabledValue("1"));
        Assert.False(LocalParaphraseChannel.IsEnabledValue(null));
        Assert.False(LocalParaphraseChannel.IsEnabledValue(""));
        Assert.False(LocalParaphraseChannel.IsEnabledValue("0"));
        Assert.False(LocalParaphraseChannel.IsEnabledValue("true"));
        Assert.False(LocalParaphraseChannel.IsEnabledValue("1 "));
        Assert.Equal("AGENTFRAMEWORK_LOCAL_PARAPHRASE", LocalParaphraseChannel.EnvName);
    }

    [Fact]
    public void 闸关_必须零吸收_零改写()
    {
        // 默认关的**机检**形态: 接线处与测试读同一个 ShouldAbsorb, 故这里绿 ⇒ 「闸关 ⇒ 全链逐位不变」不是口头承诺。
        Assert.False(LocalParaphraseChannel.ShouldAbsorb("换个说法", enabled: false));
        Assert.False(LocalParaphraseChannel.ShouldAbsorb("换个说法", enabled: false));
        Assert.False(LocalParaphraseChannel.ShouldAbsorb(null, enabled: true));
        Assert.True(LocalParaphraseChannel.ShouldAbsorb("换个说法", enabled: true));
        Assert.False(LocalParaphraseChannel.ShouldAbsorb("换个说法说下部署进度", enabled: true));
    }

    // ── ③ 机检守卫 ──────────────────────────────────────────────────────────
    [Fact]
    public void 守卫_合法改写必须通过()
    {
        var outText = "链管道这边接的是本地通道 r1, 命中率按「1 减 新比前缀」算, agent.host.csproj 这个配置文件没有动。";
        var v = LocalParaphraseChannel.Guard(Src, outText);
        Assert.True(v.Ok, v.Reason);
        Assert.Equal("ok", v.Reason);
    }

    [Fact]
    public void 守卫_标识符丢失必拒()
    {
        var v = LocalParaphraseChannel.Guard(Src, "链管道这边接的是本地通道, 命中率按公式算, agent.host.csproj 这个配置文件没有动。");
        Assert.False(v.Ok);
        Assert.StartsWith("identifier_lost:", v.Reason, StringComparison.Ordinal);
        Assert.Contains("r1", v.Reason, StringComparison.Ordinal);
    }

    [Fact]
    public void 守卫_标识符凭空新增必拒()
    {
        var v = LocalParaphraseChannel.Guard(Src, Src + " 详见 r499.md。");
        Assert.False(v.Ok);
        Assert.StartsWith("identifier_added:", v.Reason, StringComparison.Ordinal);
        Assert.Contains("r499", v.Reason, StringComparison.Ordinal);
    }

    [Fact]
    public void 守卫_动作声明禁增()
    {
        var v = LocalParaphraseChannel.Guard(Src, "本地通道 r1 已接入链管道, 命中率统计已完成, agent.host.csproj 未改动。");
        Assert.False(v.Ok);
        Assert.StartsWith("claim_added:", v.Reason, StringComparison.Ordinal);
        // 反向: 原文本来就有的声明不受影响 (不得把合法改写误杀)
        var ok = LocalParaphraseChannel.Guard("部署已完成。", "这次部署已完成。");
        Assert.True(ok.Ok, ok.Reason);
    }

    [Theory]
    [InlineData("本地通道 r1 已接入链管道: 命中率 = 1−新/前缀, 配置文件 agent.host.csproj 未改动？", "question_mark")]
    [InlineData("本地通道 r1 已接入链管道, 命中率 1−新/前缀, agent.host.csproj 未改动。思考一下怎么改写。", "think_leak")]
    [InlineData("本地通道 r1 ``` 已接入链管道, agent.host.csproj 未改动。", "think_leak")]
    public void 守卫_反问与思考链泄漏必拒(string outText, string expect)
    {
        var v = LocalParaphraseChannel.Guard(Src, outText);
        Assert.False(v.Ok);
        Assert.Equal(expect, v.Reason);
    }

    [Fact]
    public void 守卫_归因必须穷举_破几条报几条()
    {
        // R503 回归 (R501 t8 实证形状): 原文 612 字, 本地输出 5 字且为反问 ⇒ 同时破 ②(问号) 与 ⑦(长度带),
        // 且 ④(标识符守恒) 必然同破。旧版先破先报只留 `question_mark`, 把「引擎根本没改写」误读成
        // 「守卫禁止问号过于严格」⇒ 归因不全 = 归因错。
        var sb = new System.Text.StringBuilder();
        while (sb.Length < 612) sb.Append("本地通道 r1 已接入链管道, agent.host.csproj 未改动。");
        var v = LocalParaphraseChannel.Guard(sb.ToString(), "要继续吗？");
        Assert.False(v.Ok);
        Assert.Contains("question_mark", v.Reason, StringComparison.Ordinal);
        Assert.Contains("identifier_lost:", v.Reason, StringComparison.Ordinal);
        Assert.Contains("length_band:", v.Reason, StringComparison.Ordinal);

        // 反方向负控: **单条违规必须仍单条报** (不得无脑拼接成「谁都在破」)
        var one = LocalParaphraseChannel.Guard(Src, "链管道这边接的是本地通道 r1, 命中率按「1 减 新比前缀」算, agent.host.csproj 这个配置文件没有动？");
        Assert.False(one.Ok);
        Assert.Equal("question_mark", one.Reason);

        // 明细有界: 词元多于 2 个时列前 2 个 + `+N`, 数目不丢 (遥测行不得被撑爆)
        Assert.Equal("a,b+3", LocalParaphraseChannel.JoinBounded(new[] { "a", "b", "c", "d", "e" }));
        Assert.Equal("a", LocalParaphraseChannel.JoinBounded(new[] { "a" }));
    }

    [Fact]
    public void 守卫_空输出与空原文必拒()
    {
        Assert.Equal("source_empty", LocalParaphraseChannel.Guard("", "x").Reason);
        Assert.Equal("source_empty", LocalParaphraseChannel.Guard(null, "x").Reason);
        Assert.Equal("empty_output", LocalParaphraseChannel.Guard(Src, "").Reason);
        Assert.Equal("empty_output", LocalParaphraseChannel.Guard(Src, "   ").Reason);
        Assert.Equal("empty_output", LocalParaphraseChannel.Guard(Src, null).Reason);
    }

    [Fact]
    public void 守卫_长度带两个方向都要拒()
    {
        var tooShort = LocalParaphraseChannel.Guard(Src, "r1 agent.host.csproj");
        Assert.False(tooShort.Ok);
        Assert.StartsWith("length_band:", tooShort.Reason, StringComparison.Ordinal);

        var tooLong = LocalParaphraseChannel.Guard(Src, Src + Src + Src);
        Assert.False(tooLong.Ok);
        Assert.StartsWith("length_band:", tooLong.Reason, StringComparison.Ordinal);

        Assert.Equal(0.4, LocalParaphraseChannel.MinLengthRatio);
        Assert.Equal(2.5, LocalParaphraseChannel.MaxLengthRatio);
    }

    [Fact]
    public void 标识符抽取_语言无关_只按字符类()
    {
        // 承 R447 语言无关令: 无后缀/关键词表 —— 按「长度≥4」或「长度≥2 且含数字」保留。
        var ids = LocalParaphraseChannel.Identifiers("LCM-8a88a4729346 / ISO-8859-1 / r1 / 3B / ok / 512").ToList();
        Assert.Contains("8a88a4729346", ids);
        Assert.Contains("8859", ids);
        Assert.Contains("r1", ids);
        Assert.Contains("3B", ids);
        Assert.Contains("512", ids);
        Assert.DoesNotContain("LCM", ids);   // 长度 3 且无数字 ⇒ 不在守恒面内 (诚实边界)
        Assert.DoesNotContain("ok", ids);    // 长度 2 且无数字 ⇒ 不在守恒面内
        // 中文不得进入词元
        Assert.DoesNotContain(ids, x => x.Any(c => c > 127));
    }

    // ── ④ 生成提示词 ────────────────────────────────────────────────────────
    [Fact]
    public void 提示词_必须携带全部硬约束且逐字含原文()
    {
        var p = LocalParaphraseChannel.BuildPrompt(Src);
        Assert.Contains(Src, p, StringComparison.Ordinal);
        Assert.Contains("原样保留", p, StringComparison.Ordinal);   // 标识符守恒
        Assert.Contains("动作声明", p, StringComparison.Ordinal);   // 动作声明禁增
        Assert.Contains("问号", p, StringComparison.Ordinal);       // 不得反问
        Assert.Contains("长度", p, StringComparison.Ordinal);       // 长度带
        Assert.Equal(p, LocalParaphraseChannel.BuildPrompt(Src));   // 确定性 (同输入同输出)
    }

    // ── ⑤ 结算类: 本地改写结果不得被兜底横幅覆盖 ────────────────────────────
    [Fact]
    public void 本地改写结算类_必须与回放同权()
    {
        Assert.Equal("local_paraphrase", ContinuationBrief.SettleLocalParaphrase);
        Assert.NotEqual(ContinuationBrief.SettleRepeatVerbatim, ContinuationBrief.SettleLocalParaphrase);
        // 控制组: 非本地结算类 + 短答复 ⇒ 兜底生效 (证明该判定面不是恒假)
        Assert.True(ContinuationBrief.ShouldApplyFallback(null, "短", null));
        // 处理组: 本地改写结算类 ⇒ 兜底不得覆盖
        Assert.False(ContinuationBrief.ShouldApplyFallback(ContinuationBrief.SettleLocalParaphrase, "短", null));
        Assert.False(ContinuationBrief.ShouldApplyFallback(ContinuationBrief.SettleRepeatVerbatim, "短", null));
        // 单源: 两个本地结算类都走 IsLocalSettled
        Assert.True(ContinuationBrief.IsLocalSettled(ContinuationBrief.SettleLocalParaphrase));
        Assert.True(ContinuationBrief.IsLocalSettled(ContinuationBrief.SettleRepeatVerbatim));
        Assert.False(ContinuationBrief.IsLocalSettled("template"));
        Assert.False(ContinuationBrief.IsLocalSettled(null));
    }

    // ── ⑥ 计数器: 失败方向必须可见 (不得把降级计成成功) ──────────────────────
    [Fact]
    public void 计数器_成功与降级分列且初值为零()
    {
        var c = new LocalParaphraseCounters();
        Assert.Equal(0, c.Attempted);
        Assert.Equal(0, c.Succeeded);
        Assert.Equal(0, c.GuardRejected);
        Assert.Equal(0, c.DegradedNoSource);
        Assert.Equal(0, c.DegradedNoPort);
        Assert.Equal(0, c.DegradedEngine);
        Assert.Equal(0, c.AccountingViolations);
        Assert.Equal("", c.LastRejectReason ?? "");

        c.RecordAttempt();
        c.RecordGuardReject("identifier_lost:r1");
        Assert.Equal(1, c.Attempted);
        Assert.Equal(0, c.Succeeded);
        Assert.Equal(1, c.GuardRejected);
        Assert.Equal("identifier_lost:r1", c.LastRejectReason);

        c.RecordNoSource();
        c.RecordNoPort();
        c.RecordEngineDegrade("exception:TimeoutException");
        c.RecordAccountingViolation("tokens_evaluated!=prompt_n+cache_n");
        c.RecordSuccess();
        Assert.Equal(1, c.Succeeded);
        Assert.Equal(1, c.DegradedNoSource);
        Assert.Equal(1, c.DegradedNoPort);
        Assert.Equal(1, c.DegradedEngine);
        Assert.Equal(1, c.AccountingViolations);
        Assert.Equal("tokens_evaluated!=prompt_n+cache_n", c.LastRejectReason);
        // 注: 生产路径下六个分类之和 == Attempted (每次尝试必落到一个分类); 本用例是**逐项单测**,
        // 直接调用各 Record* ⇒ 不构成该恒等 (故不断言之和, 只断言逐项值)。
    }
}
