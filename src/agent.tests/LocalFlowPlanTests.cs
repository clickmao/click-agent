using System.Linq;
using agent.vision;
using Xunit;

namespace agent.tests;

/// <summary>本地视觉模型返回的「多步骤操作流程 JSON」解析判据（长短任务 + fail-closed）。</summary>
public class LocalFlowPlanTests
{
    private const string Good = """
    {"goal":"搜索并打开第一条结果","mode":"short","steps":[
      {"op":"click","target":"search field","box_2d":[140,64,620,108]},
      {"op":"type","target":"search field","box_2d":[140,64,620,108],"text":"lfm"},
      {"op":"click","target":"search button","box_2d":[636,64,748,108]},
      {"op":"assert","verify":"结果列表非空"}
    ],"notes":"4 步完成"}
    """;

    [Fact]
    public void Good_ShortFlow_Parses()
    {
        var p = LocalFlowPlan.TryParse(Good, out var errs);
        Assert.Empty(errs);
        Assert.NotNull(p);
        Assert.Equal("short", p!.Mode);
        Assert.Equal(4, p.Steps.Count);
        Assert.Equal(8, p.Budget);
        Assert.False(p.NeedsReperception);
        Assert.Equal(new[] { 140, 64, 620, 108 }, p.Steps[0].Box);
        Assert.Equal("lfm", p.Steps[1].Text);
    }

    [Theory]
    [InlineData("drag", "op 非法")]
    [InlineData("click", null)]
    public void UnknownOp_Rejected(string op, string? hint)
    {
        var json = "{\"goal\":\"g\",\"mode\":\"short\",\"steps\":[{\"op\":\"" + op + "\"}]}";
        var p = LocalFlowPlan.TryParse(json, out var errs);
        Assert.Null(p);
        Assert.NotEmpty(errs);
        if (hint is not null)
        {
            Assert.Contains(errs, e => e.Contains(hint, System.StringComparison.Ordinal));
        }
    }

    [Fact]
    public void BoxOutOfRange_Rejected()
    {
        var json = "{\"goal\":\"g\",\"mode\":\"short\",\"steps\":[{\"op\":\"click\",\"box_2d\":[140,64,620,1200]}]}";
        var p = LocalFlowPlan.TryParse(json, out var errs);
        Assert.Null(p);
        Assert.Contains(errs, e => e.Contains("越界", System.StringComparison.Ordinal));
    }

    [Fact]
    public void BoxInverted_Rejected()
    {
        var json = "{\"goal\":\"g\",\"mode\":\"short\",\"steps\":[{\"op\":\"click\",\"box_2d\":[620,64,140,108]}]}";
        Assert.Null(LocalFlowPlan.TryParse(json, out var errs));
        Assert.Contains(errs, e => e.Contains("x1<x2", System.StringComparison.Ordinal));
    }

    [Fact]
    public void TypeWithoutText_Rejected()
    {
        var json = "{\"goal\":\"g\",\"mode\":\"short\",\"steps\":[{\"op\":\"type\",\"box_2d\":[1,1,9,9]}]}";
        Assert.Null(LocalFlowPlan.TryParse(json, out var errs));
        Assert.Contains(errs, e => e.Contains("op=type 必须带 text", System.StringComparison.Ordinal));
    }

    [Fact]
    public void AssertWithoutVerify_Rejected()
    {
        var json = "{\"goal\":\"g\",\"mode\":\"short\",\"steps\":[{\"op\":\"assert\"}]}";
        Assert.Null(LocalFlowPlan.TryParse(json, out var errs));
        Assert.Contains(errs, e => e.Contains("op=assert 必须带 verify", System.StringComparison.Ordinal));
    }

    [Fact]
    public void ClickWithoutBox_Rejected()
    {
        var json = "{\"goal\":\"g\",\"mode\":\"short\",\"steps\":[{\"op\":\"click\",\"target\":\"ok\"}]}";
        Assert.Null(LocalFlowPlan.TryParse(json, out var errs));
        Assert.Contains(errs, e => e.Contains("必须带 box_2d", System.StringComparison.Ordinal));
    }

    private static string ManySteps(int n, string mode)
    {
        var steps = string.Join(",", Enumerable.Range(0, n).Select(i =>
            "{\"op\":\"click\",\"target\":\"b" + i + "\",\"box_2d\":[10,10,20,20]}"));
        return "{\"goal\":\"g\",\"mode\":\"" + mode + "\",\"steps\":[" + steps + "]}";
    }

    [Fact]
    public void ShortBudget_9Steps_Rejected_LongBudget_SameShape_Accepted()
    {
        Assert.Null(LocalFlowPlan.TryParse(ManySteps(9, "short"), out var errs));
        Assert.Contains(errs, e => e.Contains("超预算", System.StringComparison.Ordinal));

        var longPlan = LocalFlowPlan.TryParse(ManySteps(9, "long"), out var errs2);
        Assert.Empty(errs2);
        Assert.NotNull(longPlan);
        Assert.Equal(64, longPlan!.Budget);
        Assert.True(longPlan.NeedsReperception);
    }

    [Theory]
    [InlineData("not json")]
    [InlineData("[]")]
    [InlineData("{\"mode\":\"short\",\"steps\":[]}")]
    [InlineData("{\"goal\":\"g\",\"steps\":[{\"op\":\"click\",\"box_2d\":[1,1,9,9]}]}")]
    public void Malformed_Rejected(string json)
    {
        Assert.Null(LocalFlowPlan.TryParse(json, out var errs));
        Assert.NotEmpty(errs);
    }
}
