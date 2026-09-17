using System.Collections.Generic;

namespace agent.contract;

/// <summary>R1 「精准语义」：下游管道**直接消费**的字段集合（唯一真源 = StructuredContract）。</summary>
public sealed record Semantics(
    string SchemaVersion,
    string Intent,
    double Confidence,
    IReadOnlyList<Entity> Entities,
    IReadOnlyList<string> Constraints,
    IReadOnlyList<string> MissingSlots,
    IReadOnlyList<Ambiguity> Ambiguities,
    IReadOnlyList<PlanStep> Plan,
    IReadOnlyList<string> DoneWhen,
    RefusalInfo? Refusal);
