using agent.critique;
using Finding = agent.critique.OutputCritic.Finding;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.14.0 T1 OutputCritic 单测: 每规则 阳性 + 阴性 (R149 真断言标准 — 检测器自身可证伪)。
/// </summary>
public class OutputCriticTests
{
    private static IReadOnlyList<Finding> Review(string code) => OutputCritic.Review($"```csharp\n{code}\n```");

    [Fact]
    public void R01_NewArrayInLoop_Positive()
    {
        var code = """
            foreach (var input in new[] { a.In0, a.In1 })
            {
                var x = g.Resolve(input);
            }
            """;
        var f = Review(code);
        Assert.Contains(f, x => x.RuleId == "R01");
    }

    [Fact]
    public void R01_RefLocal_Negative()
    {
        // R0071 转正修法形态 — 不应命中
        var code = """
            ref var nn = ref g.N[id];
            var a0 = g.Resolve(nn.In0);
            var a1 = g.Resolve(nn.In1);
            """;
        Assert.DoesNotContain(Review(code), x => x.RuleId == "R01");
    }

    [Fact]
    public void R02_StringConcatInLoop_Positive()
    {
        var code = """
            foreach (var item in items)
            {
                report += item.Name + ",";
            }
            """;
        Assert.Contains(Review(code), x => x.RuleId == "R02");
    }

    [Fact]
    public void R02_SimpleAssignment_Negative()
    {
        var code = "var x = compute(a + b);";
        Assert.DoesNotContain(Review(code), x => x.RuleId == "R02");
    }

    [Fact]
    public void R03_AsyncVoid_Positive()
    {
        Assert.Contains(Review("async void HandleClick() { DoWork(); }"), x => x.RuleId == "R03");
    }

    [Fact]
    public void R03_AsyncTask_Negative()
    {
        Assert.DoesNotContain(Review("async Task HandleClickAsync() { DoWork(); }"), x => x.RuleId == "R03");
    }

    [Fact]
    public void R04_ResultBlocking_Positive()
    {
        Assert.Contains(Review("var v = GetValueAsync().Result;"), x => x.RuleId == "R04");
    }

    [Fact]
    public void R05_EmptyCatch_Positive()
    {
        Assert.Contains(Review("try { Load(); } catch (Exception) { }"), x => x.RuleId == "R05");
    }

    [Fact]
    public void R06_CountGtZero_Positive()
    {
        Assert.Contains(Review("if (items.Count() > 0) { }"), x => x.RuleId == "R06");
    }

    [Fact]
    public void R07_DoubleEquality_Positive()
    {
        Assert.Contains(Review("double d = Compute();\nif (d == 0d) { }"), x => x.RuleId == "R07");
    }

    [Fact]
    public void R08_UndisposedStream_Positive()
    {
        Assert.Contains(Review("var s = new FileStream(path, FileMode.Open);"), x => x.RuleId == "R08");
    }

    [Fact]
    public void NoCodeBlock_NoFindings()
    {
        Assert.Empty(OutputCritic.Review("纯文本回复, 没有代码块。"));
    }

    [Fact]
    public void Render_Empty_ReturnsEmpty()
    {
        Assert.Equal(string.Empty, OutputCritic.Render(Array.Empty<Finding>()));
    }

    [Fact]
    public void Render_HasEvidenceLineAndRule()
    {
        var out_ = OutputCritic.Render(new[] { new Finding("R01", 12, "new[] { a.In0 }", "用 ref") });
        Assert.Contains("R01", out_);
        Assert.Contains("行 12", out_);
    }
}
