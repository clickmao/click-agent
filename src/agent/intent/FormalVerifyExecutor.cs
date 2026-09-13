using System.Text;
using agent.config;
using agent.registry;

namespace agent.intent;

/// <summary>
/// v0.23.0-exp12 · R391(C7): **`formal.verify` 本地节点执行器** —— 计划链里的零 token 形式化裁决节点。
///
/// 位置: 计划节点 (LocalExecutorRegistry.FormalVerify) → PlanRunner 调度 → 本执行器 → 本地内核裁决。
/// 输入(确定性, 三选一, 逐级回退):
///   ① 本节点文本里的 ```` ```clickproof ```` 围栏;
///   ② 依赖节点输出里的 clickproof 围栏 (按 DependsOn → RuntimeDeps 顺序, 取首个命中);
///   ③ 本节点文本本身即契约 (以 premise/goal/no_formal 开头的裸契约行)。
/// 判定: 复用 PlanNodeFormalGate.Evaluate —— **与执行前闸门同一套四态语义**, 不新增第二套裁决口径。
///
/// 铁律 (可证伪):
///   · 缺失断言 ⇒ NoFormal(absent) ⇒ 放行, **绝不因此追问 LLM** (RequiresLlmRetry 恒 false);
///   · Refuted / Vacuous / Malformed ⇒ 节点 Failed (未证明绝不放行), 反例/理由码进 Error 供回注;
///   · Unknown ⇒ 节点 **Failed** 且 disposition=Abstained 显式落账 (诚实弃权: 不计违规, 但**一样不放行**);
///   · 全程零 LLM 调用 / 零网络 / 零 shell。
/// </summary>
public sealed class FormalVerifyExecutor : ILocalNodeExecutor
{
    public string Id => LocalExecutorRegistry.FormalVerify;

    public Task<NodeExecutionResult> RunAsync(PlanNode node, LocalNodeContext ctx, CancellationToken ct)
    {
        var (contractText, source) = ResolveContract(node, ctx);
        var d = PlanNodeFormalGate.Evaluate(contractText);
        var report = Render(node.Id, source, d, contractText);

        AgentTelemetry.Emit("plan_formal_verify", "PlanRunner",
            ("node", node.Id),
            ("exec", Id),
            ("verdict", d.VerdictText),
            ("reason", d.ReasonCode),
            ("disposition", d.Disposition.ToString()),
            ("allowed", d.Allowed),
            ("src", source),
            ("contract_chars", contractText?.Length ?? 0),
            ("tokens", 0L));

        if (!d.Allowed)
            // 文案与闸门**同源** (PlanNodeFormalGate.BlockMessage): 不另造第二套措辞/反例格式
            return Task.FromResult(PythonSelfTestExecutor.Fail(node.Id,
                report + "\n" + PlanNodeFormalGate.BlockMessage(d),
                NodeFailureKind.Permanent));

        return Task.FromResult(new NodeExecutionResult
        {
            NodeId = node.Id,
            FinalState = PlanNodeState.Completed,
            Output = report,
        });
    }

    /// <summary>契约文本解析 (确定性回退链; 返回来源标记供审计)。</summary>
    internal static (string? Text, string Source) ResolveContract(PlanNode node, LocalNodeContext ctx)
    {
        var own = ClickProofFence.ExtractTrimmed(node.Text);
        if (!string.IsNullOrEmpty(own)) return (own, "node:" + node.Id);

        foreach (var dep in Dependencies(node))
        {
            if (!ctx.NodeOutputs.TryGetValue(dep, out var upstream) || string.IsNullOrEmpty(upstream)) continue;
            var fenced = ClickProofFence.ExtractTrimmed(upstream);
            if (!string.IsNullOrEmpty(fenced)) return (fenced, "upstream:" + dep);
        }

        if (LooksLikeContract(node.Text)) return (node.Text, "node_raw:" + node.Id);

        return (null, "absent");
    }

    /// <summary>声明依赖在前、运行时依赖在后 (与 TextProcessExecutor.ResolveInput 同序, 保证确定性)。</summary>
    private static IEnumerable<string> Dependencies(PlanNode node)
    {
        foreach (var d in node.DependsOn) yield return d;
        foreach (var d in node.RuntimeDeps) yield return d;
    }

    /// <summary>裸契约判据: 任一行以 premise / goal / no_formal 起头 (整词)。</summary>
    internal static bool LooksLikeContract(string? text)
    {
        if (string.IsNullOrWhiteSpace(text)) return false;
        foreach (var raw in text.Split('\n'))
        {
            var line = raw.Trim();
            if (line.Length == 0 || line[0] == '#') continue;
            if (line.StartsWith("premise", StringComparison.Ordinal) || line.StartsWith("goal", StringComparison.Ordinal)
                || line.StartsWith(FormalAssertionContract.NoFormalMarker, StringComparison.OrdinalIgnoreCase))
                return true;
        }
        return false;
    }

    /// <summary>机器可读报告 (稳定格式, 供上层断言/回灌)。</summary>
    internal static string Render(string nodeId, string source, FormalGateDecision d, string? contractText)
    {
        var sb = new StringBuilder(160);
        sb.Append("formal{node=").Append(nodeId)
          .Append(" verdict=").Append(d.VerdictText)
          .Append(" disposition=").Append(d.Disposition)
          .Append(" reason=").Append(d.ReasonCode)
          .Append(" allowed=").Append(d.Allowed ? "true" : "false")
          .Append(" src=").Append(source)
          .Append(" chars=").Append(contractText?.Length ?? 0)
          .Append(" llm=0}");
        return sb.ToString();
    }
}
