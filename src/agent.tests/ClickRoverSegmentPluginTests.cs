using Xunit;
using agent.registry;

namespace agent.tests;

/// <summary>
/// v0.23.0-exp12 · R391(C7 消费侧) 机检: clickproof 段插件的**恒等透传 + 本地裁决**。
/// 核心不可协商项 (可证伪):
///   · 插件**绝不改写模型正文** —— 返回值必须与入参段内容逐字相等 (含被阻断的情形);
///   · 非 clickproof 段 (含其它语言 / PlainText) 一律恒等透传, 且不产生报告 (不误触发);
///   · 裁决走**同一套**节点闸门语义 (PlanNodeFormalGate), 四态分类不新增第二套口径;
///   · 经真实 ResponseSegmentRouter 走一遍: 全文输出逐字等于输入全文。
/// </summary>
public sealed class ClickRoverSegmentPluginTests
{
    private const string ProvedContract = "premise x >= 0\npremise x <= 10\ngoal x <= 20";
    private const string RefutedContract = "premise x >= 0\ngoal x > 0";

    private static ResponseSegment Code(string content, string? lang) => new()
    {
        Kind = SegmentKind.Code,
        Content = content,
        Language = lang,
    };

    // ── 恒等透传 ─────────────────────────────────────────────────────────

    [Fact]
    public async Task NonClickproof_Code_Segment_Passes_Through_And_Reports_Nothing()
    {
        var p = new ClickRoverSegmentPlugin();
        const string py = "print(1)\n";

        var back = await p.HandleAsync(Code(py, "python"));

        Assert.Equal(py, back);
        Assert.Empty(p.DrainReports());
    }

    [Fact]
    public async Task Null_Language_Segment_Passes_Through()
    {
        var p = new ClickRoverSegmentPlugin();

        Assert.Equal("正文", await p.HandleAsync(Code("正文", null)));
        Assert.Empty(p.DrainReports());
    }

    // ── Proved: 放行 + 逐字透传 ─────────────────────────────────────────

    [Fact]
    public async Task Proved_Contract_Is_Adjudicated_Locally_And_Content_Unchanged()
    {
        var p = new ClickRoverSegmentPlugin();

        var back = await p.HandleAsync(Code(ProvedContract, ClickProofFence.Language));

        Assert.Equal(ProvedContract, back);                 // 正文一字未改
        var reports = p.DrainReports();
        var r = Assert.Single(reports);
        Assert.True(r.Allowed);
        Assert.Equal("Proved", r.Verdict);
        Assert.Equal("proved", r.ReasonCode);
        Assert.Equal(ProvedContract.Length, r.ContractChars);
    }

    // ── Refuted: 阻断记账, 正文仍然逐字透传 ──────────────────────────────

    [Fact]
    public async Task Refuted_Contract_Blocks_But_Still_Does_Not_Rewrite_Content()
    {
        var p = new ClickRoverSegmentPlugin();

        var back = await p.HandleAsync(Code(RefutedContract, ClickProofFence.Language));

        Assert.Equal(RefutedContract, back);
        var r = Assert.Single(p.DrainReports());
        Assert.False(r.Allowed);
        Assert.Equal("Refuted", r.Verdict);
        Assert.False(string.IsNullOrEmpty(r.Counterexample));
        Assert.Contains("x=0", r.Counterexample!);
    }

    // ── Unknown / 空段: 弃权或 absent, 都不算改写 ───────────────────────

    [Fact]
    public async Task Unknown_And_Empty_Contracts_Are_Adjudicated_Honestly()
    {
        var p = new ClickRoverSegmentPlugin();

        Assert.Equal("premise x >= 0\ngoal x * y > 0",
            await p.HandleAsync(Code("premise x >= 0\ngoal x * y > 0", ClickProofFence.Language)));
        Assert.Equal(string.Empty, await p.HandleAsync(Code(string.Empty, ClickProofFence.Language)));

        var reports = p.DrainReports();
        Assert.Equal(2, reports.Count);
        Assert.Equal("Unknown", reports[0].Verdict);
        Assert.False(reports[0].Allowed);
        Assert.Equal("NoFormal", reports[1].Verdict);        // 空段 = 未声明断言, 放行
        Assert.True(reports[1].Allowed);
    }

    [Fact]
    public async Task DrainReports_Clears_On_Read()
    {
        var p = new ClickRoverSegmentPlugin();
        await p.HandleAsync(Code(ProvedContract, ClickProofFence.Language));

        Assert.Single(p.DrainReports());
        Assert.Empty(p.DrainReports());
    }

    // ── 经真实 Router 的端到端: 全文逐字不变 ────────────────────────────

    [Fact]
    public async Task Real_Router_Output_Is_Byte_Identical_To_Input()
    {
        var router = new ResponseSegmentRouter([new ClickRoverSegmentPlugin()]);
        Assert.Equal(ClickRoverSegmentPlugin.PluginId, router.PluginNames[0]);

        var text = "结论如下。\n\n```clickproof\n" + ProvedContract + "\n```\n\n以上。\n";

        var routed = await router.ProcessAsync(text, CancellationToken.None);

        Assert.Equal(text, routed);                          // 插件在场也不改一个字符
        Assert.True(router.PluginNames.Contains(ClickRoverSegmentPlugin.PluginId));
    }

    // ── 判据同源: 插件与路由谓词必须认同一套围栏语义 ────────────────────

    [Fact]
    public void Fence_Semantics_Are_Shared_With_Routing_Predicate()
    {
        var fenced = "说明\n```clickproof\n" + ProvedContract + "\n```\n";
        Assert.Equal(ProvedContract, ClickProofFence.ExtractTrimmed(fenced));
        Assert.True(agent.intent.PlanRoutePolicy.CarriesFormalClaim(fenced));

        // 负控: 其它语言的围栏 / 自然语言散文 不得被判为携带断言
        Assert.False(agent.intent.PlanRoutePolicy.CarriesFormalClaim("说明\n```python\nprint(1)\n```\n"));
        Assert.False(agent.intent.PlanRoutePolicy.CarriesFormalClaim("这个结论为什么成立?"));
    }
}
