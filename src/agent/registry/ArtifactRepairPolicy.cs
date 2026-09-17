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
/// 回流修复策略 (纯函数, 零副作用 → 可单测)。
/// 诚实边界: 只在"机器校验确证失败"时触发; 未修好时如实标记, 不替换正文。
/// </summary>
public static class ArtifactRepairPolicy
{
    public const string EnableEnvName = "AGENTFRAMEWORK_ARTIFACT_REPAIR";

    /// <summary>有界: 一次失败最多修 1 轮 (修 1 轮不改, 再修只会烧 token)。</summary>
    public const int MaxAttempts = 1;
    /// <summary>回灌模型的失败脚本上限 (字符)。</summary>
    public const int MaxCodeChars = 6000;
    /// <summary>回灌模型的运行/校验输出上限 (字符, 取**尾部** — 错误总在结尾)。</summary>
    public const int MaxOutputChars = 1500;

    /// <summary>闸门: 默认开 (raw 为空时读环境变量; 显式 0/false/off/no 关闭)。</summary>
    public static bool IsEnabled(string? raw = null)
    {
        var v = raw ?? Environment.GetEnvironmentVariable(EnableEnvName);
        if (string.IsNullOrWhiteSpace(v))
            return true;
        return v.Trim().ToLowerInvariant() is not ("0" or "false" or "off" or "no");
    }

    /// <summary>是否需要回流修复 (= 未通过机器校验)。</summary>
    public static bool IsRepairable(ArtifactCheck c) => !c.Passed;

    /// <summary>构造回灌提示词 (确定性: 同一输入 → 同一输出, 可断言)。</summary>
    public static string BuildPrompt(ArtifactCheck c)
    {
        var sb = new StringBuilder(8192);
        sb.Append("你上一轮交付的脚本**未通过机器校验**，请修复它。\n\n");
        sb.Append("[机器校验结论] 失败类别=").Append(c.ErrorKind)
          .Append("；语法编译通过=").Append(c.CompileValid ? "是" : "否")
          .Append("；编译退出码=").Append(c.ExitCode);
        if (c.Ran)
            sb.Append("；已实跑=是，运行退出码=").Append(c.RunExitCode).Append(c.RunTimedOut ? "（超时）" : string.Empty);
        else
            sb.Append("；已实跑=否");
        sb.Append('\n');

        // R374b: 闸门契约必须显式写出 (R371 D4 同类教训: 组件入口约定不写进上游纪律 → 模型无从满足)。
        sb.Append("\n[机器闸门契约] 该脚本会被这样执行: `python3 -I <文件>")
          .Append(c.SelfTestAvailable ? " --selftest" : string.Empty)
          .Append("`（无额外参数、无 stdin、无 TTY）; 要求 **退出码 0**。")
          .Append("脚本自带 --selftest 入口时, 闸门只以该入口判定成败。\n");

        var failed = FailedCases(c);
        if (failed.Length > 0)
            sb.Append("\n[未通过的用例（机器自测输出摘要）]\n").Append(failed).Append('\n');

        var output = Tail(c.Output, MaxOutputChars);
        if (!string.IsNullOrWhiteSpace(output))
            sb.Append("\n[校验/运行输出]\n").Append(output.Trim()).Append('\n');

        sb.Append("\n[失败脚本（原样）]\n```").Append(c.Language).Append('\n')
          .Append(Head(c.Code, MaxCodeChars)).Append("\n```\n");

        sb.Append("\n要求：只输出修正后的**完整**脚本（同样用 ```").Append(c.Language)
          .Append(" 围栏、内容不得省略号或片段），保持原有功能与命令行入口不变；")
          .Append("只做**最小改动**：只改导致未通过用例的那一处，其余已通过用例的行为不得回退；")
          .Append("自测入口与输出格式（每例一行 PASS/FAIL、结尾一行总判定）保持不变；")
          .Append("交稿前请在脑中逐条走一遍未通过用例。不要输出解释、不要输出其它语言片段。");
        return sb.ToString();
    }

    /// <summary>从机器输出里摘出未通过项 (确定性摘要, 不改写原文)。</summary>
    internal static string FailedCases(ArtifactCheck c)
    {
        if (string.IsNullOrWhiteSpace(c.Output))
            return string.Empty;
        var hits = new List<string>(8);
        foreach (var raw in c.Output.Split('\n'))
        {
            var line = raw.Trim();
            if (line.Length == 0 || hits.Count >= MaxFailedCases)
                continue;
            if (line.Contains("FAIL", StringComparison.OrdinalIgnoreCase)
                || line.Contains("Error", StringComparison.OrdinalIgnoreCase)
                || line.Contains("Traceback", StringComparison.OrdinalIgnoreCase))
                hits.Add(Head(line, 300));
        }
        return string.Join('\n', hits);
    }

    /// <summary>未通过用例摘要最多保留条数。</summary>
    public const int MaxFailedCases = 12;

    internal static string Head(string s, int max) =>
        string.IsNullOrEmpty(s) ? string.Empty : (s.Length <= max ? s : s[..max] + "\n…（已截断）");

    internal static string Tail(string s, int max) =>
        string.IsNullOrEmpty(s) ? string.Empty : (s.Length <= max ? s : "…（已截断）\n" + s[^max..]);
}
