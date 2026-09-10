using agent.roles;
using Xunit;

namespace agent.tests;

/// <summary>R360: 成长账本 — Beta 置信度/倾向三态/落盘重载 (跨会话成长)。</summary>
public class RoleGrowthLedgerTests : IDisposable
{
    private readonly string _dir = Path.Combine(Path.GetTempPath(), "rgl_" + Guid.NewGuid().ToString("N"));
    public void Dispose()
    {
        if (Directory.Exists(_dir)) Directory.Delete(_dir, true);
    }

    [Fact]
    public void 赏罚计数_Laplace置信度()
    {
        var l = new RoleGrowthLedger("t", _dir);
        l.Record(CorrectionDetector.CorrectionKind.Correct, "docker");
        l.Record(CorrectionDetector.CorrectionKind.Correct, "docker");
        l.Record(CorrectionDetector.CorrectionKind.Adopt, "docker");
        // 1赏2罚 → Laplace = (赏+1)/(总+2) = 2/5 = 0.4
        Assert.Equal(0.4, l.ConfidenceFor("docker")!.Value, 3);
    }

    [Fact]
    public void 无样本_confidence_null()
    {
        var l = new RoleGrowthLedger("t", _dir);
        Assert.Null(l.ConfidenceFor("nonexistent"));
    }

    [Fact]
    public void 倾向三态_Distrust_观察中_Trust()
    {
        var l = new RoleGrowthLedger("t", _dir);
        for (var i = 0; i < 6; i++) l.Record(CorrectionDetector.CorrectionKind.Correct, "bad");
        for (var i = 0; i < 6; i++) l.Record(CorrectionDetector.CorrectionKind.Adopt, "good");
        for (var i = 0; i < 3; i++) l.Record(CorrectionDetector.CorrectionKind.Correct, "few");
        Assert.Equal("Distrust", l.TendencyFor("bad").Tendency);   // 0/6 → <0.4
        Assert.Equal("Trust", l.TendencyFor("good").Tendency);     // 6/6 → >0.7
        Assert.Equal("None", l.TendencyFor("few").Tendency);       // 样本 3 <5 → 诚实观察中
    }

    [Fact]
    public void Neutral_不计数()
    {
        var l = new RoleGrowthLedger("t", _dir);
        l.Record(CorrectionDetector.CorrectionKind.Neutral, "x");
        Assert.Null(l.ConfidenceFor("x"));
    }

    [Fact]
    public void 落盘重载_跨会话成长保持()
    {
        var l1 = new RoleGrowthLedger("t", _dir);
        for (var i = 0; i < 6; i++) l1.Record(CorrectionDetector.CorrectionKind.Correct, "docker");
        l1.Save();

        var l2 = new RoleGrowthLedger("t", _dir); // 新实例 = 模拟重启
        Assert.Equal("Distrust", l2.TendencyFor("docker").Tendency);
        Assert.Equal(l1.ConfidenceFor("docker"), l2.ConfidenceFor("docker"));
    }

    [Fact]
    public void RenderForPrompt_含域与倾向()
    {
        var l = new RoleGrowthLedger("t", _dir);
        for (var i = 0; i < 6; i++) l.Record(CorrectionDetector.CorrectionKind.Correct, "docker");
        var rendered = l.RenderForPrompt();
        Assert.Contains("docker", rendered);
        Assert.Contains("先怀疑", rendered);
    }
}
