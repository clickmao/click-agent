using System.Collections.Generic;
using agent.contract;

namespace agent.r1;

/// <summary>
/// R1 管道 · 单次运行结果。
/// rc 域：0=可推进/无需执行（code_task/ops_task 且步骤全过）；2=缺信息要澄清；3=硬闸拒答；
/// 4=契约/计划非法；5=执行未达期望（链未达成：执行 rc≠0 或计划没跑完）；6=前缀漂移或传输失败（fail-closed，禁继续执行）；
/// 8=自测期望未达成 self_test_unmet（R536：计划已跑完、产物在盘，仅**模型自述的** expect_stdout 与执行器实测冲突
/// —— 既不算成功也不算失败；判分以外部门禁/隐藏用例为准，两个数都落盘）；
/// 8 的第二个阶段名 public_probe_unmet（R544：**非模型自述**的题面公开用例回放未过且修复预算耗尽
/// —— 同为成对报，rc 不作正确性证据）。
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
    IReadOnlyList<StepOutcome> Steps,
    PublicProbeResult? Probe = null,
    // R546 早停轴（默认 0=关）：>0 表示轴的阈值（该臂的探针开关轴开）；EarlyStopSkipped>0 表示
    //   确有 1 次「回灌修复调用」被主动跳过（省下的正是那次不必要的远端请求）。
    int EarlyStopThreshold = 0,
    int EarlyStopSkipped = 0,
    // R550 探针修复独立预算轴（默认 0=关）：>0 表示该臂**实际**用掉的探针证据修复轮数
    //   （由探针失败证据驱动、未挤占执行回灌预算）。轴关时不入台账 ⇒ 与旧台账逐字节同。
    int ProbeRepairs = 0,
    // R600 修复环「带现状」轴（AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER，默认开）：>0 表示该跑次实际
    //   随附过盘上产物原文的回灌修复轮数，Chars = 随附块字符数。轴关 ⇒ 恒 0 ⇒ 台账与旧逐字节同。
    int ArtifactCarryoverRounds = 0,
    int ArtifactCarryoverChars = 0,
    // R610（RF0004.2 · M3 第一刀）动作候选轴（AGENTFRAMEWORK_R1_ACTION_CANDIDATES，默认开）：
    //   远端在契约面部声明 `action_candidates`，本地机械裁选后落这三枚**机制面**计数；
    //   Declared==0（含轴关）⇒ 台账字段不出现 ⇒ 与旧台账逐字节同（零回归由字段缺席机检）。
    int ActionCandidatesDeclared = 0,
    int ActionCandidatesAccepted = 0,
    int ActionCandidatesRejected = 0)
{
    public bool Halted => Rc != 0;
}
