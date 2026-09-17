using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using agent.config;
using agent.templates;

namespace agent.registry;


/// <summary>
/// R374 (D3): 一次"机器校验结论" (编译 + 可选实跑) —— 回流闭环的输入事实。
///
/// 为什么需要它: 校验结论此前只落在 PythonArtifactReport/台账里 (exit 码一个数字),
/// 运行输出 (stdout/stderr) 在插件内部被丢弃 → 失败信息**从未回到模型上下文**,
/// 于是"自测失败"与"任务结束"没有区别, agent 无法自我迭代。
/// 本类型把结论连同**可复现的失败输出**交给上层, 由 ArtifactRepairLoop 回灌模型。
/// </summary>
public sealed record ArtifactCheck(
    string Path,
    string Language,
    string Code,
    bool CompileValid,
    int ExitCode,
    bool Ran,
    int RunExitCode,
    bool RunTimedOut,
    string Output)
{
    /// <summary>是否通过机器校验: 编译通过, 且 (未实跑 或 实跑退出码 0 且未超时)。</summary>
    public bool Passed => CompileValid && (!Ran || (RunExitCode == 0 && !RunTimedOut));

    /// <summary>失败类别 (compile / run / timeout / none) — 遥测与提示词共用同一判据。</summary>
    public string ErrorKind => !CompileValid
        ? "compile"
        : RunTimedOut ? "timeout"
        : Ran && RunExitCode != 0 ? "run"
        : "none";

    /// <summary>脚本自带无头自测入口 —— 闸门据此决定是否以 --selftest 判定成败。</summary>
    public bool SelfTestAvailable => MentionsSelfTest(Code);

    /// <summary>自测入口判据 (与 PythonArtifactPlugin 选参规则**同源**, 防提示词与闸门漂移)。</summary>
    public static bool MentionsSelfTest(string? content) =>
        content is not null && content.Contains("--selftest", StringComparison.Ordinal);
}
