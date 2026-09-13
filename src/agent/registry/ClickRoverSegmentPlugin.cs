using agent.config;
using agent.intent;

namespace agent.registry;

/// <summary>一条区段级形式化裁决 (不可变, 供上层审计/回灌)。</summary>
public sealed record FormalSegmentReport(
    string Verdict,
    string ReasonCode,
    bool Allowed,
    string? Counterexample,
    int ContractChars);

/// <summary>
/// v0.23.0-exp12 · R391(C7 消费侧): **回答侧 clickproof 段插件**。
///
/// 职责边界 (极窄, 故意不扩张):
///   ① 只消费 ```` ```clickproof ```` 段 (其它 Code 段**逐字透传**, 零损耗);
///   ② 对 clickproof 段调用**同一套**节点闸门判定 (PlanNodeFormalGate) ⇒ 与计划执行期裁决同源, 不产生第二套语义;
///   ③ **绝不改写模型正文**: 段内容原样返回 (判定结论走报告通道, 由上层决定是否回灌/阻断)。
///
/// 诚实边界: 本件只"提取 + 裁决 + 记账", 不自行决定"要不要拿它去改计划" ——
///   那属于计划装配层 (把 formal.verify 节点插到依赖它的节点之前), 见 R392 待办。
/// 零 token / 零 shell / 零反射: 纯内存 + 本地内核。
/// </summary>
public sealed class ClickRoverSegmentPlugin : IResponseSegmentPlugin
{
    private readonly object _gate = new();
    private readonly List<FormalSegmentReport> _reports = [];

    /// <summary>插件名 (静态前缀在场判定的依据, 见 FormalPromptContract.IsPresent)。</summary>
    public const string PluginId = "clickrover.formal";

    /// <summary>
    /// 挂载开关: 缺省**开**; `AGENTFRAMEWORK_FORMAL_SEGMENT=0` 整段关闭。
    /// 关闭后插件不在场 ⇒ 静态前缀**逐字回到 R380 形态** (零 token 负担), 可作 A/B 对照臂。
    /// </summary>
    public static bool Enabled =>
        !string.Equals(Environment.GetEnvironmentVariable("AGENTFRAMEWORK_FORMAL_SEGMENT"), "0", StringComparison.Ordinal);

    public string Name => PluginId;

    /// <summary>只挂 Code 段 —— 排他性由语言标识二次收窄, 非 clickproof 段恒等透传。</summary>
    public IReadOnlySet<SegmentKind> Consumes { get; } = new HashSet<SegmentKind> { SegmentKind.Code };

    /// <summary>判定 + 记账; 返回值恒等于入参 (透传, 一字不改)。</summary>
    public Task<string> HandleAsync(ResponseSegment segment, CancellationToken ct = default)
    {
        if (!string.Equals(segment.Language, ClickProofFence.Language, StringComparison.OrdinalIgnoreCase))
            return Task.FromResult(segment.Content);

        var decision = PlanNodeFormalGate.Evaluate(segment.Content);

        lock (_gate)
            _reports.Add(new FormalSegmentReport(
                decision.VerdictText, decision.ReasonCode, decision.Allowed,
                decision.Counterexample, segment.Content.Length));

        AgentTelemetry.Emit("plan_formal_segment", "ResponseSegment",
            ("verdict", decision.VerdictText),
            ("reason", decision.ReasonCode),
            ("allowed", decision.Allowed),
            ("contract_chars", segment.Content.Length),
            ("tokens", 0L));

        return Task.FromResult(segment.Content);
    }

    /// <summary>取走累计报告 (取即清: 同一失败不被反复消费)。</summary>
    public IReadOnlyList<FormalSegmentReport> DrainReports()
    {
        lock (_gate)
        {
            if (_reports.Count == 0) return [];
            var copy = _reports.ToArray();
            _reports.Clear();
            return copy;
        }
    }
}
