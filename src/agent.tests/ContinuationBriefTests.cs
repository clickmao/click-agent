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

namespace agentframework.tests;

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
        Assert.Contains("(无)", block);
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
        Assert.Contains("继续", grounded.ToAsk[0].Questions[0].Choices[0]);

        var plain = new EvidenceGate().Evaluate(tasks);
        Assert.NotEmpty(plain.ToAsk);
        var q2 = plain.ToAsk[0].Questions[0].Question;
        Assert.DoesNotContain(".txt", q2);                        // 负控: 无事实 ⇒ 不得出现任何文件名
        Assert.Contains("还没有", q2);
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
}
