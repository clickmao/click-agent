using Xunit;
using agent.intent;
using agent.registry;

namespace agent.tests;

/// <summary>
/// v0.23.0-exp12 · R391(C7) 机检: `formal.verify` 本地节点执行器。
/// 判别力 (可证伪):
///   · 四态不可混算 —— Proved 放行 / Refuted·Vacuous 阻断 / Unknown 诚实弃权(仍不放行) / Malformed 阻断;
///   · 缺失 ≠ 错误 —— 无断言 ⇒ NoFormal(absent) 放行, 且**任何分支零 LLM 调用** (llm=0 落在报告里);
///   · 输入回退链确定性 —— 本节点围栏 → 上游围栏 → 裸契约行;
///   · 登记表与实现同源 —— `LocalExecutorRegistry` 里 formal.verify 条目 Id 必须等于执行器 Id。
/// </summary>
public sealed class FormalVerifyExecutorTests
{
    private const string Proved = "premise x >= 0\npremise x <= 10\ngoal x <= 20";
    private const string Refuted = "premise x >= 0\ngoal x > 0";
    private const string Vacuous = "premise x > 5\npremise x < 3\ngoal x == 99";
    private const string Unknown = "premise x >= 0\ngoal x * y > 0";
    private const string Malformed = "premise x >=\ngoal x > 0";

    private static readonly FormalVerifyExecutor Executor = new();

    private static PlanNode Node(string id, string text, params string[] deps)
    {
        var n = new PlanNode { Id = id, Text = text, Intent = IntentRecognizer.Intents.General };
        n.DependsOn.AddRange(deps);
        return n;
    }

    private static string Fenced(string contract) => "```" + ClickProofFence.Language + "\n" + contract + "\n```";

    // ── 放行侧: Proved ───────────────────────────────────────────────────

    [Fact]
    public async Task Proved_Fence_Completes_With_Zero_Llm()
    {
        var r = await Executor.RunAsync(Node("n1", Fenced(Proved)), new LocalNodeContext(), CancellationToken.None);

        Assert.Equal(PlanNodeState.Completed, r.FinalState);
        Assert.Null(r.Error);
        Assert.Contains("verdict=Proved", r.Output!);
        Assert.Contains("disposition=Proceed", r.Output!);
        Assert.Contains("allowed=true", r.Output!);
        Assert.Contains("src=node:n1", r.Output!);
        Assert.Contains("llm=0", r.Output!);
    }

    // ── 阻断侧: Refuted / Vacuous / Malformed ────────────────────────────

    [Fact]
    public async Task Refuted_Fence_Fails_With_Counterexample_Injected()
    {
        var r = await Executor.RunAsync(Node("n1", Fenced(Refuted)), new LocalNodeContext(), CancellationToken.None);

        Assert.Equal(PlanNodeState.Failed, r.FinalState);
        Assert.Equal(NodeFailureKind.Permanent, r.FailureKind);
        Assert.Contains("verdict=Refuted", r.Error!);
        Assert.Contains("反例: x=0", r.Error!);
    }

    [Fact]
    public async Task Vacuous_And_Malformed_Fences_Fail()
    {
        var vac = await Executor.RunAsync(Node("n1", Fenced(Vacuous)), new LocalNodeContext(), CancellationToken.None);
        Assert.Equal(PlanNodeState.Failed, vac.FinalState);
        Assert.Contains("verdict=Vacuous", vac.Error!);
        Assert.Contains("disposition=Violation", vac.Error!);

        var mal = await Executor.RunAsync(Node("n2", Fenced(Malformed)), new LocalNodeContext(), CancellationToken.None);
        Assert.Equal(PlanNodeState.Failed, mal.FinalState);
        Assert.Contains("disposition=Malformed", mal.Error!);
    }

    // ── 未知: 诚实弃权, 但**一样不放行** ───────────────────────────────

    [Fact]
    public async Task Unknown_Abstains_And_Still_Does_Not_Pass()
    {
        var r = await Executor.RunAsync(Node("n1", Fenced(Unknown)), new LocalNodeContext(), CancellationToken.None);

        Assert.Equal(PlanNodeState.Failed, r.FinalState);          // 未证明绝不放行
        Assert.Contains("verdict=Unknown", r.Error!);
        Assert.Contains("disposition=Abstained", r.Error!);        // 但分类是"弃权"而非"违规"
        Assert.Contains("弃权", r.Error!);
    }

    // ── 缺失 ≠ 错误: 不追问 LLM ─────────────────────────────────────────

    [Fact]
    public async Task Absent_Assertion_Passes_Without_Any_Llm_Retry()
    {
        var r = await Executor.RunAsync(Node("n1", "整理一下这段文本"), new LocalNodeContext(), CancellationToken.None);

        Assert.Equal(PlanNodeState.Completed, r.FinalState);
        Assert.Contains("verdict=NoFormal", r.Output!);
        Assert.Contains("reason=no_formal_absent", r.Output!);
        Assert.Contains("allowed=true", r.Output!);
        Assert.Contains("llm=0", r.Output!);
        Assert.False(PlanNodeFormalGate.Evaluate(null).WouldCallLlm);
    }

    [Fact]
    public async Task Explicit_NoFormal_Marker_Passes()
    {
        var r = await Executor.RunAsync(Node("n1", "no_formal: 该步骤是散文叙述"),
            new LocalNodeContext(), CancellationToken.None);

        Assert.Equal(PlanNodeState.Completed, r.FinalState);
        Assert.Contains("verdict=NoFormal", r.Output!);
        Assert.Contains("allowed=true", r.Output!);
    }

    // ── 输入回退链: 上游围栏 / 裸契约 ───────────────────────────────────

    [Fact]
    public async Task Upstream_Fence_Is_Consumed_When_Node_Text_Has_None()
    {
        var ctx = new LocalNodeContext();
        ctx.NodeOutputs["n0"] = "前面的推理。\n\n" + Fenced(Proved) + "\n";

        var r = await Executor.RunAsync(Node("n1", "据此继续", "n0"), ctx, CancellationToken.None);

        Assert.Equal(PlanNodeState.Completed, r.FinalState);
        Assert.Contains("src=upstream:n0", r.Output!);
        Assert.Contains("verdict=Proved", r.Output!);
    }

    [Fact]
    public async Task Raw_Contract_Lines_In_Node_Text_Are_Accepted()
    {
        var r = await Executor.RunAsync(Node("n1", Refuted), new LocalNodeContext(), CancellationToken.None);

        Assert.Equal(PlanNodeState.Failed, r.FinalState);
        Assert.Contains("src=node_raw:n1", r.Error!);
        Assert.Contains("verdict=Refuted", r.Error!);
    }

    [Fact]
    public void LooksLikeContract_Negative_Control()
    {
        Assert.True(FormalVerifyExecutor.LooksLikeContract("premise x >= 0"));
        Assert.True(FormalVerifyExecutor.LooksLikeContract("no_formal: 无"));
        Assert.False(FormalVerifyExecutor.LooksLikeContract("这个结论成立的前提是什么"));
        Assert.False(FormalVerifyExecutor.LooksLikeContract(null));
    }

    // ── 登记表 ↔ 实现 同源 + 路由可达 ──────────────────────────────────

    [Fact]
    public void Registry_Entry_Matches_Executor_And_Is_Reachable()
    {
        var d = LocalExecutorRegistry.All.Single(x => x.Id == LocalExecutorRegistry.FormalVerify);

        Assert.True(d.Wired);
        Assert.Equal(Executor.Id, d.Id);
        Assert.Contains(PlanNodeIntents.VerifyFormal, d.Intents);
        Assert.Empty(d.PostActionMarkers);      // 触发靠机器可读围栏, 不靠自然语言关键词
        Assert.Equal(LocalExecutorRegistry.FormalVerify, LocalExecutorRegistry.ForIntent(PlanNodeIntents.VerifyFormal)!.Id);

        // 路由谓词: 机器可读围栏 ⇒ 判本地 formal.verify
        Assert.True(PlanRoutePolicy.CarriesFormalClaim(Fenced(Proved)));
        Assert.False(PlanRoutePolicy.CarriesFormalClaim("```python\nprint(1)\n```"));
    }

    // ── 全套围栏语义一致: 提取器 ⇄ 执行器 ───────────────────────────────

    [Fact]
    public void Extractor_Semantics_Match_Executor_Input()
    {
        Assert.Equal(Proved, ClickProofFence.ExtractTrimmed(Fenced(Proved)));
        // 负控: 行内反引号 / 其它语言围栏不得被当成 clickproof
        Assert.Null(ClickProofFence.Extract("行内 `clickproof` 提及"));
        Assert.Null(ClickProofFence.Extract("```python\nprint(1)\n```"));
        // 未闭合 ⇒ 返回剩余正文 (截断不得静默当"未声明")
        Assert.Equal(Proved, ClickProofFence.ExtractTrimmed("```clickproof\n" + Proved));
    }
}
