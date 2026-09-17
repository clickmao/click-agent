using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using agent.context;
using agent.intent;
using agent.registry;
using Xunit;
using SubTask = agent.intent.IntentDecomposer.SubTask;
namespace agent.tests;

/// <summary>
/// R458 承接轮人性化 —— 单测。
///
/// 用户令: 「一个人对另一个人突然说一句"继续"，另一个人不明所以，肯定就会反问"继续什么"」
///   ⇒ 判定面复用意图层既有分支; 接地面只列**工作区真实产物**; 收口面模型不接地时链自身组装反问。
///
/// 负控 (机检): ① 空工作区 ⇒ 块里/兜底里不得出现任何文件名; ② 块里不得出现未扫描到的名字;
///              ③ 人话承接句不得含内部术语 (可选范围/检查点/作废/槽位); ④ 非承接轮不得被误判。
/// </summary>
public sealed class ContinuationBriefTests
{
    private static string NewTempRoot()
    {
        var dir = Path.Combine(Path.GetTempPath(), "r458-brief-" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(dir);
        return dir;
    }

    // ---------- 面 1: 判定 (复用意图层既有分支, 不新立关键词表) ----------

    [Fact]
    public void Judgement_BareContinueIsContinuation_ConcreteWriteIsNot()
    {
        var vague = IntentDecomposer.Decompose("继续");
        var concrete = IntentDecomposer.Decompose("把 notes.md 的第一行内容写入 first.txt（只要那一行）");

        Assert.True(ContinuationBrief.IsContinuationTurn(vague),
            "裸『继续』应判为承接轮; 实际 flags=" + string.Join(",", vague.Select(t => t.Flags.ToString())));
        Assert.False(ContinuationBrief.IsContinuationTurn(concrete),
            "带动作+对象的完整任务不得判为承接轮; 实际 flags=" + string.Join(",", concrete.Select(t => t.Flags.ToString())));
    }

    [Fact]
    public void Judgement_AmbiguousReferenceIsNotContinuation()
    {
        // 指代不明有更具体的缺口 (该问"它指什么") ⇒ 不走承接轮路径 (负控: 别把两种问询混成一种)
        var t = new SubTask("把它写进文件", IntentRecognizer.Intents.General, false, 0,
            IntentDecomposer.TaskRelation.None, 0.4,
            IntentDecomposer.ConfidenceFlags.WeakIntent | IntentDecomposer.ConfidenceFlags.AmbiguousReference);
        Assert.False(ContinuationBrief.IsContinuationTurn(new[] { t }));
    }

    [Fact]
    public void Judgement_EmptyInputIsNotContinuation()
    {
        Assert.False(ContinuationBrief.IsContinuationTurn(null));
        Assert.False(ContinuationBrief.IsContinuationTurn(Array.Empty<SubTask>()));
    }

    // ---------- 面 2: 扫描 (只认真实磁盘事实) ----------

    [Fact]
    public void Scan_ReturnsRealArtifactsWithFirstLine_AndSkipsRuntimeNoise()
    {
        var root = NewTempRoot();
        try
        {
            File.WriteAllText(Path.Combine(root, "count.txt"), "4");
            File.WriteAllText(Path.Combine(root, "merged.txt"), "ALPHA\nBETA\n");
            Directory.CreateDirectory(Path.Combine(root, "data"));
            File.WriteAllText(Path.Combine(root, "data", "telemetry.jsonl"), "{}");
            Directory.CreateDirectory(Path.Combine(root, ".git"));
            File.WriteAllText(Path.Combine(root, ".git", "HEAD"), "ref: x");

            var facts = ContinuationBrief.ScanArtifacts(root, ContinuationBrief.MaxArtifacts, out var total);
            var names = facts.Select(f => f.Name).ToList();

            Assert.Equal(2, total);                                   // 只数真实产物, 不含 data/ .git
            Assert.Contains("count.txt", names);
            Assert.Contains("merged.txt", names);
            Assert.DoesNotContain(names, n => n.StartsWith("data/", StringComparison.Ordinal));
            Assert.DoesNotContain(names, n => n.StartsWith(".git", StringComparison.Ordinal));

            var merged = facts.First(f => f.Name == "merged.txt");
            Assert.Equal("ALPHA", merged.FirstLine);          // 首行, 不是整文件
            Assert.Equal(11, merged.Bytes);                    // "ALPHA\nBETA\n"
            var count = facts.First(f => f.Name == "count.txt");
            Assert.Equal("4", count.FirstLine);
            Assert.Equal(1, count.Bytes);
        }
        finally { Directory.Delete(root, true); }
    }

    [Fact]
    public void Scan_MissingRootOrUnreadable_ReturnsEmpty_NoThrow()
    {
        Assert.Empty(ContinuationBrief.ScanArtifacts(null, ContinuationBrief.MaxArtifacts, out _));
        Assert.Empty(ContinuationBrief.ScanArtifacts("", ContinuationBrief.MaxArtifacts, out _));
        Assert.Empty(ContinuationBrief.ScanArtifacts(
            Path.Combine(Path.GetTempPath(), "r458-not-exist-" + Guid.NewGuid().ToString("N")),
            ContinuationBrief.MaxArtifacts, out _));
    }

    [Fact]
    public void Judgement_ConcreteQuestionAtHighConfidence_IsNotContinuation()
    {
        // R458 run1 实测教训 (机检固化): 「当前目录下一共有几个 .py 文件？」门置信 0.8、门未发问,
        // 但意图层带了弱意图标记 ⇒ 只看 flags 会误注入承接块 (run1 真发生过, 模型还把它写进回复)。
        // 判据必须与门同一: flags 弱 **且** 置信度低于门限。
        var question = IntentDecomposer.Decompose("当前目录下一共有几个 .py 文件？");
        Assert.True(question.All(t => t.Confidence >= ContinuationBrief.ConfidenceFloor),
            "该问句的门置信度应 ≥ 门限; 实际=" + string.Join(",", question.Select(t => t.Confidence)));
        Assert.False(ContinuationBrief.IsContinuationTurn(question));

        // 反向正控: 同一批 flags 但置信度低于门限 (裸『继续』0.45) ⇒ 必须判为承接轮
        var bare = IntentDecomposer.Decompose("继续");
        Assert.True(bare.All(t => t.Confidence < ContinuationBrief.ConfidenceFloor));
        Assert.True(ContinuationBrief.IsContinuationTurn(bare));
    }

    [Fact]
    public void Block_MarksTruncationHonestly_TotalVsListed()
    {
        var root = NewTempRoot();
        try
        {
            for (var i = 0; i < 3; i++) File.WriteAllText(Path.Combine(root, $"f{i}.txt"), "x");
            var facts = ContinuationBrief.ScanArtifacts(root, 2, out var total);
            var block = ContinuationBrief.BuildBlock(facts, total);
            Assert.Equal(3, total);
            Assert.Equal(2, facts.Count);
            Assert.Contains("共 3 项, 只列最近 2 项", block);      // 如实标注 ⇒ 模型不会自己发现"被截断"
        }
        finally { Directory.Delete(root, true); }
    }

    // ---------- 面 3: 接地块 (只列真实项; 空态禁编造) ----------

    [Fact]
    public void Block_ListsExactlyTheRealArtifacts()
    {
        var facts = new[]
        {
            new ArtifactFact("count.txt", 1, "4"),
            new ArtifactFact("stats.txt", 9, "chars=14"),
        };
        var block = ContinuationBrief.BuildBlock(facts);

        Assert.Contains("[承接状态 v1]", block);
        Assert.Contains("count.txt=4", block);
        Assert.Contains("stats.txt=chars=14", block);
        Assert.Contains("继续什么", block);                       // 要求里有反问
        Assert.DoesNotContain("ghost.txt", block);                // 负控: 不得出现未扫描到的名字
        Assert.DoesNotContain("(无)", block);
    }

    [Fact]
    public void Block_EmptyState_SaysNone_AndNeverNamesAFile()
    {
        var block = ContinuationBrief.BuildBlock(Array.Empty<ArtifactFact>());
        Assert.Contains("无产物", block);
        Assert.DoesNotContain(".txt", block);                     // 负控: 空态不得列举任何文件名
        Assert.DoesNotContain(".md", block);
        Assert.Contains("继续什么", block);
    }

    // ---------- 面 4: 收口判据 (fail-closed 闸门) ----------

    [Fact]
    public void NeedsFallback_EmptyOrUngrounded_True_GroundedFalse()
    {
        var facts = new[] { new ArtifactFact("stats.txt", 9, "chars=14") };

        Assert.True(ContinuationBrief.NeedsFallback(null, facts));
        Assert.True(ContinuationBrief.NeedsFallback("   ", facts));
        Assert.True(ContinuationBrief.NeedsFallback("好的。", facts));                       // 无问句无事实 ⇒ 不接地
        Assert.True(ContinuationBrief.NeedsFallback("请给出下一步指令。", facts));            // 无问句无事实 ⇒ 不接地
        Assert.False(ContinuationBrief.NeedsFallback("上一步 stats.txt 已写定 chars=14；要继续哪一项？", facts));
        Assert.False(ContinuationBrief.NeedsFallback("你想让我做什么?", facts));              // 有问句 ⇒ 放过 (闸门只管"无用", 不评文风)

        // 无事实可用: 只有反问才算承接
        Assert.True(ContinuationBrief.NeedsFallback("好的。", Array.Empty<ArtifactFact>()));
        Assert.False(ContinuationBrief.NeedsFallback("继续什么?", Array.Empty<ArtifactFact>()));
    }

    [Fact]
    public void Fallback_OnlyUsesRealFacts_AndNeverInventsFiles()
    {
        var facts = new[]
        {
            new ArtifactFact("count.txt", 1, "4"),
            new ArtifactFact("merged.txt", 12, "ALPHA"),
        };
        var reply = ContinuationBrief.ComposeFallback("继续", facts);
        Assert.Contains("count.txt", reply);
        Assert.Contains("merged.txt", reply);
        Assert.Contains("？", reply);
        Assert.DoesNotContain("stats.txt", reply);                // 负控: 未扫描到的不得出现

        var empty = ContinuationBrief.ComposeFallback("继续", Array.Empty<ArtifactFact>());
        Assert.Contains("？", empty);
        Assert.DoesNotContain(".txt", empty);                     // 负控: 空事实不得提任何文件名
        Assert.DoesNotContain(".md", empty);
    }

    // ---------- 面 5: 问句接地 (EvidenceGate 承接轮分支) ----------

    [Fact]
    public void EvidenceGate_VagueQuestion_IsGroundedInRealFacts()
    {
        var tasks = IntentDecomposer.Decompose("继续");
        var facts = new[]
        {
            new ArtifactFact("count.txt", 1, "4"),
            new ArtifactFact("stats.txt", 9, "chars=14"),
        };

        var grounded = new EvidenceGate(facts: facts).Evaluate(tasks);
        Assert.NotEmpty(grounded.ToAsk);
        var q = grounded.ToAsk[0].Questions[0].Question;
        Assert.Contains("count.txt=4", q);
        Assert.Contains("stats.txt=chars=14", q);
        Assert.DoesNotContain("(如:", q);                          // 内部示例枚举不再上前台
        var choices = grounded.ToAsk[0].Questions[0].Choices;
        Assert.Contains(choices, c => c.Contains("count.txt", StringComparison.Ordinal));  // 菜单接地到真实项
        Assert.DoesNotContain(choices, c => c.Contains("搜索资料", StringComparison.Ordinal)); // R460: 示例菜单禁止
        Assert.Equal(ContinuationBrief.BuildMenu(facts), choices);  // R460: 菜单单源 (门 == 构造器)

        var plain = new EvidenceGate().Evaluate(tasks);
        Assert.NotEmpty(plain.ToAsk);
        var q2 = plain.ToAsk[0].Questions[0].Question;
        Assert.DoesNotContain(".txt", q2);                        // 负控: 无事实 ⇒ 不得出现任何文件名
        Assert.Contains("还没有", q2);
        // R460: 空态**不再**给通用示例菜单 (用户点名的机器味)
        Assert.DoesNotContain(plain.ToAsk[0].Questions[0].Choices, c => c.Contains("搜索资料", StringComparison.Ordinal));
        Assert.DoesNotContain(plain.ToAsk[0].Questions[0].Choices, c => c.Contains("写文档", StringComparison.Ordinal));
    }

    // ---------- 面 5b: R460 精炼 + 菜单 (可机检形态) ----------

    [Fact]
    public void R460_BlockAndMenuAndAsk_RespectBrevityCaps()
    {
        var facts = new[]
        {
            new ArtifactFact("count.txt", 2, "4"),
            new ArtifactFact("merged.txt", 18, "ALPHA"),
            new ArtifactFact("stats.txt", 9, "chars=14"),
        };
        var block = ContinuationBrief.BuildBlock(facts, 11);
        Assert.True(block.Length <= ContinuationBrief.MaxBlockChars,
            $"注入块须 ≤ {ContinuationBrief.MaxBlockChars} 字符 (实际 {block.Length})");
        Assert.Contains("共 11 项, 只列最近 3 项", block);          // 截断诚实性不因瘦身丢失

        var menu = ContinuationBrief.BuildMenu(facts, 11);
        Assert.True(menu.Count <= ContinuationBrief.MaxMenuItems, "菜单不超过 3 项");
        foreach (var m in menu)
            Assert.True(m.Length <= ContinuationBrief.MaxMenuItemChars, $"菜单项过长 ({m.Length}): {m}");
        Assert.Contains("count.txt", menu[0]);                     // 首项接地最近真实产物

        var ask = ContinuationBrief.BuildAsk("继续", facts, 11);
        Assert.True(ask.Length <= ContinuationBrief.MaxAskChars, $"反问须 ≤ {ContinuationBrief.MaxAskChars} (实际 {ask.Length})");
        Assert.Contains("1. ", ask);                               // 编号菜单
        Assert.Contains("2. ", ask);
        Assert.Contains("继续什么", ContinuationBrief.BuildBlock(facts, 11));

        // 单源: 兜底反问 == 门问句 (同形 ⇒ 不靠模型自觉)
        Assert.Equal(ask, ContinuationBrief.ComposeFallback("继续", facts, 11));
        // 空态: 单项菜单, 且绝不出现示例枚举/文件名
        var emptyAsk = ContinuationBrief.BuildAsk("继续", Array.Empty<ArtifactFact>());
        Assert.DoesNotContain("搜索资料", emptyAsk);
        Assert.DoesNotContain(".txt", emptyAsk);
        Assert.Single(ContinuationBrief.BuildMenu(Array.Empty<ArtifactFact>()));
    }

    // ---------- 面 6: 作废告知人性化 (内部术语机检) ----------

    [Fact]
    public void HumanizeVoidNotice_IsPlainSpeech_NoInternalJargon()
    {
        var pending = "「继续」意图不明确。你想让 agent 做什么? (如: 搜索/写文档/执行命令/分析数据)";
        var text = PlanResumeService.HumanizeVoidNotice(pending, PlanResumeService.RefuseChoiceMismatch);

        Assert.DoesNotContain("(如:", text);                      // 内部示例枚举被去掉
        Assert.DoesNotContain("[", text);
        Assert.Contains("上一轮", text);
        Assert.Single(text.Split('\n'));                          // 一句话, 不刷屏
        foreach (var bad in PlanResumeService.InternalJargon)
            Assert.DoesNotContain(bad, text);                     // 负控: 内部术语一律不上前台
        Assert.DoesNotContain(PlanResumeService.RefuseChoiceMismatch, text); // 内部理由(可选范围)不上前台
        // R460 精炼令: 承接句硬上限 (78 → ≤48 字符)
        Assert.True(text.Length <= PlanResumeService.MaxNoticeChars,
            $"人话承接句须 ≤ {PlanResumeService.MaxNoticeChars} 字符 (实际 {text.Length})");
    }

    [Fact]
    public void HumanizeVoidNotice_NoPendingQuestion_StillOnePlainSentence()
    {
        var text = PlanResumeService.HumanizeVoidNotice(null, PlanResumeService.RefuseNoSlot);
        Assert.Contains("上一轮", text);
        Assert.DoesNotContain("(无问题文本)", text);
        foreach (var bad in PlanResumeService.InternalJargon)
            Assert.DoesNotContain(bad, text);
    }

    [Fact]
    public void CompactQuestion_PrefersQuotedUserWords_ElseFirstSentence_AndCapsLength()
    {
        // 问句里引了用户原话 ⇒ 取原话 (人话承接说的是"你上一轮说的那句")
        Assert.Equal("继续",
            PlanResumeService.CompactQuestion("「继续」意图不明确。你想让 agent 做什么? (如: 搜索/写文档/执行命令/分析数据)"));
        Assert.Equal("把 notes.md 第一行写入 first.txt",
            PlanResumeService.CompactQuestion("「把 notes.md 第一行写入 first.txt」缺少执行所需的参数 (目标对象/路径/范围)。请补充。"));

        // 没有用户原话 ⇒ 取首句, 并去掉方括号选项表
        Assert.Equal("读文件，然后写总结。",
            PlanResumeService.CompactQuestion("读文件，然后写总结。 [搜索资料/写文档/总结]"));

        var longQ = new string('甲', 80) + "。后面还有";
        Assert.True(PlanResumeService.CompactQuestion(longQ, 20).Length <= 20);
        Assert.Equal(string.Empty, PlanResumeService.CompactQuestion(null));
    }

    // ── R461: 零字节产物必须如实标 "(空)", 不给模型留编造空间 ─────────────

    [Fact]
    public void Empty_Artifact_Is_Marked_Empty_In_Block_And_Ask()
    {
        var facts = new[]
        {
            new ArtifactFact("stats.txt", 0, string.Empty),
            new ArtifactFact("count.txt", 4, "4"),
        };

        var block = ContinuationBrief.BuildBlock(facts, 2);
        Assert.Contains("stats.txt=(空)", block);
        Assert.Contains("count.txt=4", block);

        var ask = ContinuationBrief.BuildAsk("继续", facts, 2);
        Assert.Contains("stats.txt=(空)", ask);
    }

    /// <summary>
    /// R461 (命中率): 每轮注入的"新内容"是 miss 的唯一来源 —— 这些预算常量是命中率红线的**算术杠杆**,
    /// 回退任何一个都会把命中率打回去。它们不是风格参数, 所以用机检锁住 (改了必须走一轮重新测量)。
    /// </summary>
    [Fact]
    public void R461_Injection_Budget_Locks()
    {
        Assert.True(agent.context.ContextAssembler.MemorySourceBudgetTokens <= 120);
        Assert.True(agent.session.SessionMemory.DefaultMaxChars <= 400);
        Assert.True(agent.session.SessionMemory.MilestonesInPrompt <= 2);
        Assert.True(agent.registry.NextTurnForecast.HeaderTaskPreviewChars <= 24);
    }

    // ── R466: 承接反问 vs 本地确定性结算的优先级 (修 R465 预注册判据 C3 FAIL) ─────────────

    /// <summary>
    /// 因果: 承接反问的前提 = 「本轮无可确定的答复对象」; 纯复述轮的对象 = 会话里上一条答复原文
    /// (真实、逐字可核验) ⇒ 前提不成立 ⇒ 不得覆盖。负控反向 (template / null / 已接地) 必须仍走原行为。
    /// 读数来源: R465 p12 网格同二进制实测 t6「再讲一遍。」被覆盖成 46 字符承接反问 (应 21 字符回放)。
    /// </summary>
    [Fact]
    public void R466_RepeatReplay_Wins_Over_ContinuationAsk()
    {
        var facts = new[] { new ArtifactFact("count.txt", 4, "4") };
        // R465 t6 应回放的上一条答复 (21 字符; 无问句、无产物名)
        const string replay = "收到，继续按当前方向推进，本轮不重新规划。";

        // 前提自证: 这条答复**本来**会被覆盖 (否则 suppress 断言是虚的)
        Assert.True(ContinuationBrief.NeedsFallback(replay, facts));
        Assert.True(ContinuationBrief.NeedsFallback(replay, Array.Empty<ArtifactFact>()));

        // 正控: 复述结算 ⇒ 不覆盖 (两种事实集口径都不覆盖 ⇒ 与工作区有无产物无关)
        Assert.False(ContinuationBrief.ShouldApplyFallback(ContinuationBrief.SettleRepeatVerbatim, replay, facts));
        Assert.False(ContinuationBrief.ShouldApplyFallback(ContinuationBrief.SettleRepeatVerbatim, replay, Array.Empty<ArtifactFact>()));

        // 负控: 其它结算类 / 无结算 ⇒ 仍按接地收口覆盖 (优先级面必须**窄**)
        Assert.True(ContinuationBrief.ShouldApplyFallback("template", replay, facts));
        Assert.True(ContinuationBrief.ShouldApplyFallback("repeat_no_prev", replay, facts));
        Assert.True(ContinuationBrief.ShouldApplyFallback(null, replay, facts));
        Assert.True(ContinuationBrief.ShouldApplyFallback("", replay, facts));

        // 负控: 已接地的回复一律不覆盖 (与既有 NeedsFallback 语义逐位一致)
        Assert.False(ContinuationBrief.ShouldApplyFallback(null, "上一步 count.txt 已写定；要继续哪一项？", facts));
        Assert.False(ContinuationBrief.ShouldApplyFallback("template", "上一步 count.txt 已写定；要继续哪一项？", facts));

        // 口径单源: 常量必须等于 skip 层打点字面 (漂移 ⇒ 规则静默失效)
        Assert.Equal("repeat_verbatim", ContinuationBrief.SettleRepeatVerbatim);
    }
}
