using agent.nlp;
using Xunit;

namespace agent.tests;

/// <summary>
/// 「远端返回 ⇒ 优化 nlp 能力」机制的生效性 + 负控 (用户令 2026-09-19)。
/// 学到的是**形状** (面/语言/长度带/显著 token) ⇒ 同面不同措辞也本地命中; 负控证明不学/跨面/跨语言不命中。
/// 评分: 命中且有用 ⇒ 留; 一次无用 ⇒ 扔 (长期自迭代, 不靠预制器具)。
/// </summary>
public sealed class NlpGateLearnTests
{
    private static string NewStore()
    {
        var dir = Path.Combine(Path.GetTempPath(), "nlpgate-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return Path.Combine(dir, "gate-patches.txt");
    }

    [Fact]
    public void RemoteReturn_TeachesShape_ThenDifferentWordingHitsLocally()
    {
        NlpGate.PatchPath = NewStore();
        Assert.True(NlpGate.LearnFromRemote("换个说法。", "repeat", localizable: true));
        Assert.True(NlpGate.IsLearned("换个说法。", "repeat"));      // 学到的形状自身命中
        Assert.True(NlpGate.IsLearned("换一种表述吧", "repeat"));    // 泛化: 同面不同措辞
        Assert.True(NlpGate.ShapeCounters.ShapeLearned >= 1);
    }

    [Fact]
    public void NegativeControl_NoLearning_NoHit()
    {
        NlpGate.PatchPath = NewStore();
        Assert.False(NlpGate.IsLearned("换一种表述吧", "repeat"));
    }

    [Fact]
    public void NegativeControl_WrongFace_NoHit()
    {
        NlpGate.PatchPath = NewStore();
        Assert.True(NlpGate.LearnFromRemote("换个说法。", "repeat", localizable: true));
        Assert.False(NlpGate.IsLearned("换个说法。", "paraphrase"));
    }

    [Fact]
    public void NegativeControl_RemoteSaidNotLocalizable_NotLearned()
    {
        NlpGate.PatchPath = NewStore();
        Assert.False(NlpGate.LearnFromRemote("换个说法。", "repeat", localizable: false));
        Assert.False(NlpGate.IsLearned("换个说法。", "repeat"));
    }

    [Fact]
    public void Score_UsefulKeeps_UselessPrunes()
    {
        NlpGate.PatchPath = NewStore();
        Assert.True(NlpGate.LearnFromRemote("换个说法。", "repeat", localizable: true));
        Assert.Equal(1, NlpGate.ReportOutcome("换一种表述吧", "repeat", useful: true));   // 命中且有用 ⇒ 留
        Assert.True(NlpGate.IsLearned("换一种表述吧", "repeat"));
        Assert.Equal(0, NlpGate.ReportOutcome("换种说法再说。", "repeat", useful: false)); // 一次无用 ⇒ 扔
        Assert.False(NlpGate.IsLearned("换一种表述吧", "repeat"));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // RF0002 §2.1 接线自证 (用户令 2026-09-19「不补回」): 学的**消费面**必须是**产品判定面**
    // (TurnGateJudge / LocalParaphraseChannel) —— 只测 NlpGate 内部命中 = 未接线 (孤岛)。
    // 负控三项: ① 不学 ⇒ 不吸收 ② 注入补丁模式 (patches 非空) ⇒ 不读形状库 (纯函数口径, 顺序无关)
    // ③ 跨面 ⇒ 不吸收。
    // ─────────────────────────────────────────────────────────────────────────

    [Fact]
    public void Wiring_RemoteSuccess_TeachesShape_ThenProductionConsumerAbsorbsDifferentWording()
    {
        NlpGate.PatchPath = NewStore();
        agent.modelqueue.TurnGateJudge.LearnOnSuccess("再讲一遍。", success: true);   // 远端轮成功 ⇒ 唯一写入点
        Assert.True(NlpGate.ShapeCounters.ShapeLearned >= 1);
        Assert.True(agent.modelqueue.TurnGateJudge.IsPureRepeat("再讲一遍。"));
        Assert.True(agent.modelqueue.TurnGateJudge.IsPureRepeat("再说一遍。"), "同面不同措辞必须被生产判定面吸收 (接线生效)");
    }

    [Fact]
    public void Wiring_NegativeControl_NoLearn_NoAbsorb()
    {
        NlpGate.PatchPath = NewStore();
        Assert.False(agent.modelqueue.TurnGateJudge.IsPureRepeat("再说一遍。"));
    }

    [Fact]
    public void Wiring_NegativeControl_InjectedPatchMode_IgnoresShapeLibrary()
    {
        NlpGate.PatchPath = NewStore();
        agent.modelqueue.TurnGateJudge.LearnOnSuccess("再讲一遍。", success: true);
        Assert.True(agent.modelqueue.TurnGateJudge.IsPureRepeat("再讲一遍。"));
        Assert.False(agent.modelqueue.TurnGateJudge.IsPureRepeat("再讲一遍。", new HashSet<string>(StringComparer.Ordinal)));
    }

    [Fact]
    public void Wiring_ParaphraseFace_UsesSameShapeChannel_AndStaysFaceIsolated()
    {
        NlpGate.PatchPath = NewStore();
        agent.modelqueue.TurnGateJudge.LearnOnSuccess("换个说法。", success: true);
        Assert.True(agent.modelqueue.LocalParaphraseChannel.IsPureParaphrase("换个方式说。"));
        Assert.False(agent.modelqueue.TurnGateJudge.IsPureRepeat("换个方式说。"), "跨面负控: 改写形状不得被复述面吸收");
    }

    [Fact]
    public void Wiring_NonRemoteTurn_DoesNotLearn()
    {
        NlpGate.PatchPath = NewStore();
        agent.modelqueue.TurnGateJudge.LearnOnSuccess("再讲一遍。", success: false);   // 远端失败 ⇒ 不学
        Assert.False(agent.modelqueue.TurnGateJudge.IsPureRepeat("再讲一遍。"));
    }
}
