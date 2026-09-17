using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;


/// <summary>R413 前置门判别结果。<c>Decided=false</c> ⇒ 调用方必须降级远端。</summary>
public sealed record TurnGateOutcome(bool Decided, TurnGateVerdict Verdict, string Raw, string? Error)
{
    // R413 证据纪律: 未判定也必须带回原文 (否则"为什么没判出来"无从对账)。
    public static TurnGateOutcome Undecided(string error, string raw = "") => new(false, TurnGateVerdict.Pass, raw, error);
    public static TurnGateOutcome Decide(TurnGateVerdict v, string raw) => new(true, v, raw, null);
}
