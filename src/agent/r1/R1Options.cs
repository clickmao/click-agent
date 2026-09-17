using System;
using System.IO;

namespace agent.r1;

/// <summary>
/// R1 一次性结构化管道的运行参数。全部来自环境（无散落魔法值）：
///   AGENTFRAMEWORK_WORKSPACE     沙箱根（缺省 = 传入的 fallback）
///   AGENTFRAMEWORK_R1_MAX_REPAIR 契约不过时的最大修复轮数（0..3，默认 1）
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
    string Tag)
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

        var transcript = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R1_TRANSCRIPT");
        var tag = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R1_TAG");

        return new R1Options(
            Path.GetFullPath(root),
            maxRepair,
            timeout,
            string.IsNullOrWhiteSpace(transcript) ? null : transcript,
            R1RoleMount.ReadNote(),
            string.IsNullOrWhiteSpace(tag) ? "(untagged)" : tag);
    }
}
