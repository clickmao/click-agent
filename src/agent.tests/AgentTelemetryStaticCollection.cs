using Xunit;
namespace agent.tests;

/// <summary>
/// R498 候选② (存量并发竞态收口): <c>agent.config.AgentTelemetry</c> 是**进程级静态**面 ——
/// writer / _configured / 「Configure 前 pending 环」三者都是全局单例。任何与之并行的测试类
/// 都在与 <c>TelemetryPendingTests</c>「Configure 紧前的探针必须能被 flush」这条断言
/// **争用同一份状态**, 且争用方式是**容量挤占** (环满 ⇒ 探针被丢), 不是普通的读写竞争 ⇒
/// 表现为「同一二进制、同一测试、间歇红」(R497 全仓 1596 例 1 红, 三次红分属两个不同类)。
///
/// 本集合用 <c>DisableParallelization = true</c> (xUnit 语义: 本集合**不与任何其它集合**
/// 并行运行) ⇒ 「造现场 → 置状态 → 断言」之间不再有第三方写入者。
/// 成员 = 全部触碰 AgentTelemetry 的测试类 (R475AccountingTests / R497FingerprintAndSynonymTests /
/// TelemetryPendingTests / TendencySignalFilterTests / R498TelemetryRingTests)。
/// </summary>
[CollectionDefinition("agent-telemetry-static", DisableParallelization = true)]
public sealed class AgentTelemetryStaticCollection
{
    /// <summary>集合名 (单一来源; 成员类用 <c>[Collection(AgentTelemetryStaticCollection.Name)]</c>)。</summary>
    public const string Name = "agent-telemetry-static";
}
