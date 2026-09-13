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

/// <summary>产物校验结论来源 (插件实现, 路由器聚合, 主链消费)。</summary>
public interface IArtifactCheckSource
{
    /// <summary>取走自上次调用以来新增的结论 (含通过项: 复检需要"通过"证据, 不只是失败)。</summary>
    IReadOnlyList<ArtifactCheck> DrainNewChecks();
}

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

/// <summary>回流修复结果 (诚实字段: Attempted/Fixed 分开, 未修好时不伪装)。</summary>
public sealed record ArtifactRepairResult(
    string Content,
    bool Attempted,
    bool Fixed,
    int Attempts,
    string ErrorKind,
    string Detail);

/// <summary>
/// R374 (D3) 运行结果回流闭环: 机器校验失败 → 失败输出回灌模型 → 有界修复 → **复检**。
///
/// 关键设计 (与真机铁证对齐):
///  - 复检判据不是"模型说修好了", 而是**重新走一遍落盘+机器校验**, 且必须出现
///    与失败产物不同的新文件并通过校验 (同路径 = 内容未变 = 没修)。
///  - 修复轮必须带 `Intent=code_generation`: 首轮预算策略按意图给足输出预算,
///    否则修复脚本会被推理吃满预算再次截断 (R373 铁证)。
///  - 诚实边界: 修不好则**保留原文**并在 telemetry `artifact_feedback` 里记 fixed=false。
/// </summary>
public sealed class ArtifactRepairLoop
{
    private readonly ResponseSegmentRouter _router;
    private readonly ILLMCaller _caller;
    private readonly Func<bool> _gate;

    public ArtifactRepairLoop(ResponseSegmentRouter router, ILLMCaller caller, Func<bool>? gate = null)
    {
        _router = router;
        _caller = caller;
        // 快照闸门 (同 PythonArtifactPlugin.runGate 的理由: 避免同进程别的用例改 env 造成行为漂移)
        var on = ArtifactRepairPolicy.IsEnabled();
        _gate = gate ?? (() => on);
    }

    public async Task<ArtifactRepairResult> RunAsync(string content, CancellationToken ct = default)
    {
        var checks = _router.DrainArtifactChecks();
        if (checks.Count == 0)
            return new ArtifactRepairResult(content, false, false, 0, "none", "本轮无产物校验结论");
        if (!_gate())
            return new ArtifactRepairResult(content, false, false, 0, "none", "回流修复被闸门关闭");

        var target = checks.FirstOrDefault(ArtifactRepairPolicy.IsRepairable);
        if (target is null)
            return new ArtifactRepairResult(content, false, false, 0, "none", $"本产物全部通过 ({checks.Count} 项)");

        var kind = target.ErrorKind;
        var started = Environment.TickCount64;
        var prompt = new Prompt
        {
            Intent = "code_generation",
            // 复用主链同一份代码任务系统提示 (含输出纪律第 9 条围栏要求) → 单一来源, 防纪律漂移。
            SystemPrompt = IntentPromptTemplates.GetSystemPrompt("code_generation")
                + "\n\n本轮是**修复轮**：依据机器校验的失败事实修正脚本，不要复述或解释原脚本。",
            UserMessage = ArtifactRepairPolicy.BuildPrompt(target),
            EstimatedTokens = 2000,
        };

        LLMResponse? resp = null;
        var fixedOk = false;
        var detail = string.Empty;
        var outContent = content;
        try
        {
            resp = await _caller.CallAsync(prompt, ct).ConfigureAwait(false);
        }
        catch (OperationCanceledException) { throw; }
        catch (Exception ex) { detail = $"修复调用异常: {ex.Message}"; }

        if (resp is not null)
        {
            if (resp.Success && !string.IsNullOrWhiteSpace(resp.Content))
            {
                outContent = await _router.ProcessAsync(resp.Content, ct).ConfigureAwait(false);
                var after = _router.DrainArtifactChecks();
                // 复检铁律: 必须出现"新路径且通过"的产物; 同路径 = 内容未变 = 没修好。
                var good = after.FirstOrDefault(a =>
                    a.Passed && !string.Equals(a.Path, target.Path, StringComparison.Ordinal));
                fixedOk = good is not null;
                detail = good is not null
                    ? $"复检通过: {good.Path}"
                    : after.Count == 0
                        ? "修复轮未产出新产物 (无围栏代码段)"
                        : after.All(a => string.Equals(a.Path, target.Path, StringComparison.Ordinal))
                            ? "修复轮内容未变 (同产物路径 → 未产出新代码)"
                            : $"修复后仍未通过 (类别={after[0].ErrorKind})";
            }
            else if (string.IsNullOrWhiteSpace(detail))
            {
                detail = $"修复调用失败: {resp.Error}";
            }
        }

        AgentTelemetry.Emit("artifact_feedback", "artifact-repair",
            ("attempts", 1), ("fixed", fixedOk), ("error_kind", kind),
            ("compile_valid", target.CompileValid), ("run_exit", target.RunExitCode),
            ("budget_intent", "code_generation"), ("ms", Environment.TickCount64 - started),
            ("tokens", resp?.TokensUsed ?? 0), ("detail", ArtifactRepairPolicy.Head(detail, 200)));

        return new ArtifactRepairResult(fixedOk ? outContent : content, true, fixedOk, 1, kind, detail);
    }
}
