using agent.config;
using agent.registry;

namespace agent.intent;

using Kernel = clickrover.formal.FormalKernel;
using KernelVerdict = clickrover.formal.Verdict;

/// <summary>闸门处置 (DCR 台账的分类口径 —— 合规/违规/弃权/畸形 四态不可混算)。</summary>
public enum FormalGateDisposition
{
    /// <summary>放行 (未声明形式化义务, 或断言已证毕)。</summary>
    Proceed = 0,

    /// <summary>违规: 断言被反例反驳, 或前提空真(Vacuous) —— 节点不许执行。</summary>
    Violation = 1,

    /// <summary>正确弃权: 可判定片段之外(Unknown) —— 未证明不放行, 但**不计为违规**(外部口径待 T1–T4 对齐)。</summary>
    Abstained = 2,

    /// <summary>契约畸形: 断言残缺/自相矛盾 —— 阻断, 且不追问 LLM(模型不能靠写坏断言绕过闸门)。</summary>
    Malformed = 3,
}

/// <summary>节点闸门裁决 (不可变, 可审计/可离线重放)。</summary>
public sealed record FormalGateDecision(
    bool Allowed,
    FormalGateDisposition Disposition,
    string ReasonCode,
    string VerdictText,
    string? Counterexample,
    string? AssertText,
    double Ms)
{
    /// <summary>硬约束: 本层纯本地, 任何分支都不产生 LLM 调用。</summary>
    public bool WouldCallLlm => false;
}

/// <summary>
/// v0.23.0-exp12 · S2: **节点级形式化闸门** —— 每个节点执行前的必经判定 (纯本地 / 零 token / 零 shell)。
///
/// 语义表(逐条有单测, 可证伪):
/// <list type="bullet">
/// <item>未声明断言 (缺省/空) → Proceed, 零 token, **不追问 LLM**</item>
/// <item>显式 `no_formal: 理由` → Proceed, 零 token</item>
/// <item>断言 → Proved → Proceed (证毕)</item>
/// <item>断言 → Refuted → Violation: 阻断 + 精确反例回注(交上层有界重规划 ≤1)</item>
/// <item>断言 → Vacuous → Violation: 前提不可满足 ⇒ 空真, 不是证据 ⇒ 拒绝</item>
/// <item>断言 → Unknown → Abstained: 片段外/溢出 ⇒ 未证明不放行, 但正确弃权不算违规</item>
/// <item>契约畸形 (残缺/矛盾) → Malformed: 阻断</item>
/// </list>
/// 铁律: 未证明绝不放行; 闸门只做判定, 不改写模型输出。
/// </summary>
public static class PlanNodeFormalGate
{
    /// <summary>消融/负向控制开关: =0 时全部节点视同未声明断言 (用于 DCR 对照组)。</summary>
    public const string EnvSwitch = "AGENTFRAMEWORK_FORMAL_GATE";

    /// <summary>闸门是否启用 (缺省启用; 仅显式 "0" 关闭)。</summary>
    public static bool IsEnabled()
    {
        var v = Environment.GetEnvironmentVariable(EnvSwitch);
        return !string.Equals(v, "0", StringComparison.Ordinal);
    }

    /// <summary>核心判定: 契约文本 → 裁决。无 I/O, 无 LLM, 可在任意线程反复调用。</summary>
    public static FormalGateDecision Evaluate(string? contractText)
    {
        var contract = FormalAssertionContract.Parse(contractText);

        switch (contract.Decision)
        {
            case FormalContractDecision.NoFormal:
                // 缺失 ≠ 错误: 不要求 LLM 返回形式化数据, 放行且零 token。
                return new FormalGateDecision(
                    Allowed: true,
                    Disposition: FormalGateDisposition.Proceed,
                    ReasonCode: "no_formal_" + contract.ReasonCode,
                    VerdictText: "NoFormal",
                    Counterexample: null,
                    AssertText: null,
                    Ms: 0);

            case FormalContractDecision.Malformed:
                return new FormalGateDecision(
                    Allowed: false,
                    Disposition: FormalGateDisposition.Malformed,
                    ReasonCode: contract.ReasonCode,
                    VerdictText: "Malformed",
                    Counterexample: null,
                    AssertText: contract.AssertionText,
                    Ms: 0);
        }

        var assert = FormalAssertionContract.ToKernelAssertText(contract);
        var r = Kernel.CheckText(assert);

        return r.Verdict switch
        {
            KernelVerdict.Proved => new FormalGateDecision(
                Allowed: true,
                Disposition: FormalGateDisposition.Proceed,
                ReasonCode: "proved",
                VerdictText: nameof(KernelVerdict.Proved),
                Counterexample: null,
                AssertText: assert,
                Ms: r.Ms),

            KernelVerdict.Refuted => new FormalGateDecision(
                Allowed: false,
                Disposition: FormalGateDisposition.Violation,
                ReasonCode: "refuted",
                VerdictText: nameof(KernelVerdict.Refuted),
                Counterexample: FormatCounterexample(r.Counterexample),
                AssertText: assert,
                Ms: r.Ms),

            KernelVerdict.Vacuous => new FormalGateDecision(
                Allowed: false,
                Disposition: FormalGateDisposition.Violation,
                ReasonCode: r.Note,
                VerdictText: nameof(KernelVerdict.Vacuous),
                Counterexample: null,
                AssertText: assert,
                Ms: r.Ms),

            KernelVerdict.Unknown => new FormalGateDecision(
                Allowed: false,
                Disposition: FormalGateDisposition.Abstained,
                ReasonCode: r.Note,
                VerdictText: nameof(KernelVerdict.Unknown),
                Counterexample: null,
                AssertText: assert,
                Ms: r.Ms),

            // 内核视断言为畸形 ⇒ 与契约畸形同处置 (不放行, 不追问)
            _ => new FormalGateDecision(
                Allowed: false,
                Disposition: FormalGateDisposition.Malformed,
                ReasonCode: "kernel_" + r.Note,
                VerdictText: nameof(KernelVerdict.Malformed),
                Counterexample: null,
                AssertText: assert,
                Ms: r.Ms),
        };
    }

    /// <summary>阻断说明 (写入节点失败原因: 含精确反例, 供上层回注一次)。</summary>
    public static string BlockMessage(FormalGateDecision d)
    {
        var ce = string.IsNullOrEmpty(d.Counterexample) ? string.Empty : $"; 反例: {d.Counterexample}";
        var kind = d.Disposition switch
        {
            FormalGateDisposition.Violation => "违规",
            FormalGateDisposition.Abstained => "弃权",
            _ => "畸形",
        };
        return $"形式化闸门阻断[{kind} {d.VerdictText}/{d.ReasonCode}]: 该节点声明了可判定片段但未被证明 ⇒ 不执行 (未证明绝不放行){ce}";
    }

    /// <summary>反例格式化 (变量名排序保证确定性, 便于对账/重放)。</summary>
    public static string? FormatCounterexample(Dictionary<string, Int128>? model)
    {
        if (model is null || model.Count == 0)
            return null;
        var parts = new List<string>(model.Count);
        foreach (var k in model.Keys.OrderBy(k => k, StringComparer.Ordinal))
            parts.Add($"{k}={model[k]}");
        return string.Join(", ", parts);
    }

    /// <summary>
    /// 闸门留痕: 每节点一条 —— S3/S4 的 DCR 分子/分母唯一来源 (含 disposition 分类与"零 token"事实)。
    /// 合规 = Proceed ∪ Abstained; 违规 = Violation; 畸形单列(不计入合规率分子)。
    /// </summary>
    public static void Emit(PlanNode node, string planId, FormalGateDecision d)
        => AgentTelemetry.Emit("plan_formal_gate", "PlanRunner",
            ("plan_id", planId),
            ("node", node.Id),
            ("verdict", d.VerdictText),
            ("disposition", d.Disposition.ToString()),
            ("allowed", d.Allowed),
            ("reason", d.ReasonCode),
            ("ms", d.Ms),
            ("tokens", 0));
}
