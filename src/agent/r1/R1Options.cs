using System;
using System.IO;

namespace agent.r1;

/// <summary>
/// R1 一次性结构化管道的运行参数。全部来自环境（无散落魔法值）：
///   AGENTFRAMEWORK_WORKSPACE     沙箱根（缺省 = 传入的 fallback）
///   AGENTFRAMEWORK_R1_MAX_REPAIR 契约不过时的最大修复轮数（0..3，默认 1）
///   AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR 执行实测与期望不符时的最大回灌修复轮数（0..3，默认 1）
///   AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL 早停阈值（0..10，默认 0=关）：产物公开用例回放已失败 ≥ 阈值
///                                     ⇒ 不再花一次调用做回灌修复（R546 轴；关闭态逐位等于旧行为）
///   AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR 探针证据回灌修复的**独立**预算（0..3，默认 0=关）：
///                                     0 ⇒ 探针失败仍只借「执行回灌」的预算（逐位等于旧行为）；
///                                     >0 ⇒ 探针失败驱动的那次修复不再挤占执行回灌预算（R550 轴）
///   AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER 修复轮「带现状」轴（默认 **1=开**）：修复指令随附管道
///                                     自己写入的盘上产物原文（R600；=0/off/false ⇒ 关，修复轮
///                                     user 轮逐位等于旧行为）
///   AGENTFRAMEWORK_R1_STEP_TIMEOUT 单步 run 超时秒（5..1800，默认 120）
///   AGENTFRAMEWORK_R1_TRANSCRIPT 落盘路径（缺省 = 不落盘，只打 stdout 标记）
///   AGENTFRAMEWORK_R1_ROLE_FILE  role 额外数据（明文 profile 文件；见 R1RoleMount）
///   AGENTFRAMEWORK_R1_TAG        本轮归属标记（进 transcript，禁硬编码轮号）
/// </summary>
public sealed record R1Options(
    string SandboxRoot,
    int MaxRepair,
    int StepTimeoutSeconds,
    string? TranscriptPath,
    string? RoleNote,
    string Tag,
    int MaxExecRepair = 1,
    bool PublicSelfCheck = false,
    int EarlyStopPfail = 0,
    int MaxProbeRepair = 0,
    bool ArtifactCarryoverEnabled = true)
{
    public static R1Options FromEnvironment(string fallbackRoot)
    {
        var root = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_WORKSPACE");
        if (string.IsNullOrWhiteSpace(root))
        {
            root = fallbackRoot;
        }

        var maxRepair = 1;
        if (int.TryParse(Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R1_MAX_REPAIR"), out var mr) && mr >= 0 && mr <= 3)
        {
            maxRepair = mr;
        }

        var timeout = 120;
        if (int.TryParse(Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R1_STEP_TIMEOUT"), out var to) && to >= 5 && to <= 1800)
        {
            timeout = to;
        }

        // R533: 执行证据回灌修复轮 (0..3, 默认 1)。>0 ⇒ 执行实测与期望不符时把真证据回灌重发起,
        // 而不是「产物已落盘却直接停机」。
        var maxExecRepair = 1;
        if (int.TryParse(Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"), out var xr) && xr >= 0 && xr <= 3)
        {
            maxExecRepair = xr;
        }

        var transcript = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R1_TRANSCRIPT");
        var tag = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R1_TAG");

        // R544: 产物侧独立自检（题面公开用例机械抽取 + 独立回放）。
        // **默认关**（关闭态逐位等于旧行为 ⇒ 零回归可用单变量证明），环境轴显式开。
        var publicSelfCheck = false;
        var psc = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK");
        if (!string.IsNullOrWhiteSpace(psc))
        {
            var v = psc.Trim();
            publicSelfCheck = v == "1" || string.Equals(v, "on", StringComparison.OrdinalIgnoreCase)
                || string.Equals(v, "true", StringComparison.OrdinalIgnoreCase);
        }

        // R546: 早停轴（0..10，默认 0=关）。>0 ⇒ 探针已判定产物不合格(pfail ≥ 阈值)时不再花一次
        // 远端调用做回灌修复。关闭态逐位等于旧行为（新台账字段缺席可机检）。
        var earlyStopPfail = 0;
        if (int.TryParse(Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL"), out var esp)
            && esp >= 0 && esp <= 10)
        {
            earlyStopPfail = esp;
        }

        // R550: 探针证据回灌的**独立**预算（0..3，默认 0=关）。R549 定因: 探针（题面公开用例回放, 非模型自述）
        //   已判定产物不合格时, 那次回灌修复与「执行实测回灌」**共用**同一预算 ⇒ 二者只能行使其一。
        //   轴开 ⇒ 探针证据驱动的修复自成预算, 不与执行回灌挤占。关闭态逐位等于旧行为（新字段缺席可机检）。
        var maxProbeRepair = 0;
        if (int.TryParse(Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR"), out var pr)
            && pr >= 0 && pr <= 3)
        {
            maxProbeRepair = pr;
        }

        // R600: 修复环「带现状」轴（默认 **开**）。关(=0/off/false) ⇒ 修复轮 user 轮逐位等于旧行为,
        //   零回归由 R1ArtifactCarryoverTests 的 off 列 + 同单测的正/负控钉住。
        var artifactCarryover = true;
        var ac = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER");
        if (!string.IsNullOrWhiteSpace(ac))
        {
            var av = ac.Trim();
            artifactCarryover = !(av == "0"
                || string.Equals(av, "off", StringComparison.OrdinalIgnoreCase)
                || string.Equals(av, "false", StringComparison.OrdinalIgnoreCase));
        }

        return new R1Options(
            Path.GetFullPath(root),
            maxRepair,
            timeout,
            string.IsNullOrWhiteSpace(transcript) ? null : transcript,
            R1RoleMount.ReadNote(),
            string.IsNullOrWhiteSpace(tag) ? "(untagged)" : tag,
            maxExecRepair,
            publicSelfCheck,
            earlyStopPfail,
            maxProbeRepair,
            artifactCarryover);
    }
}
