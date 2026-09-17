using System.Collections.Generic;
using agent.contract;

namespace agent.r1;

/// <summary>
/// R1 管道 · 单次运行结果。
/// rc 域：0=可推进/无需执行（code_task/ops_task 且步骤全过）；2=缺信息要澄清；3=硬闸拒答；
/// 4=契约/计划非法；5=执行未达期望；6=前缀漂移或传输失败（fail-closed，禁继续执行）。
/// </summary>
public sealed record R1RunResult(
    int Rc,
    string Stage,
    string Reason,
    string ReplyText,
    R1CallStats Stats,
    int PrefixChars,
    string PrefixSha256,
    string TaskSha256,
    Semantics? Semantics,
    int RoleNoteChars,
    string? TranscriptPath,
    IReadOnlyList<StepOutcome> Steps)
{
    public bool Halted => Rc != 0;
}
