using System.Text.Json.Serialization;

namespace agent.intent;


/// <summary>
/// 本地执行能力登记表 (v0.22.0 exp9 D2) —— 单一事实源。
///
/// 硬约束: 这张表与真实实现一一对应。
///   · Wired=true  的实现体见 PlanRunner.cs (PythonSelfTestExecutor / TextProcessExecutor / FormalVerifyExecutor), 有单测覆盖;
///   · Wired=false 的条目只作"已识别但未接线"的显式登记, 路由函数永不返回它们。
/// 这样"本地可跑"就不是口号: 表里没有 = 路由只能判 Remote = 不会假装本地能跑。
/// </summary>
public static class LocalExecutorRegistry
{
    /// <summary>跑产物自带的无头自测入口 (python3 &lt;artifact&gt; --selftest, 退出码即判据)</summary>
    public const string PythonSelfTest = "python.selftest";

    /// <summary>本地文本处理/证据汇总 (统计/格式化/摘要, 纯 CPU)</summary>
    public const string TextProcess = "text.process";

    /// <summary>本地形式化验证 (R391 C7): clickproof 断言 → 本地内核确定性裁决 (零 token / 零 shell)</summary>
    public const string FormalVerify = "formal.verify";

    /// <summary>真机按键回放 + 截图反核 (跨平台按键通道未接线 → 见 D3b)</summary>
    public const string RealMachineReplay = "realmachine.replay";

    /// <summary>本地命令路由 (/ls、/git 等 LocalCommandRouter 能力, 未接进计划节点 → D3b)</summary>
    public const string LocalCommand = "command.local";

    public static readonly IReadOnlyList<LocalExecutorDescriptor> All =
    [
        new(PythonSelfTest, "本地跑产物自测 (--selftest)",
            [PlanNodeIntents.VerifyLocal, IntentRecognizer.Intents.TestGeneration],
            "产物自带 --selftest 无头入口 ⇒ 本地子进程跑一遍, 退出码即判据 (零 token)",
            Wired: true,
            PostActionMarkers: ["自测", "selftest", "--selftest", "校验", "验证", "编译", "跑一遍", "py_compile"]),

        new(TextProcess, "本地文本处理 / 证据汇总",
            [PlanNodeIntents.TextProcessing, PlanNodeIntents.VerifyLocal],
            "纯文本统计/格式化无需模型 ⇒ 本地 CPU 直接算 (零 token)",
            Wired: true,
            PostActionMarkers: ["统计", "格式化", "汇总", "转换", "计数", "摘要", "整理", "合并"]),

        new(FormalVerify, "本地形式化验证 (clickproof 断言)",
            [PlanNodeIntents.VerifyFormal],
            "节点携带 clickproof 断言 ⇒ 本地内核确定性裁决 (Proved/Refuted/Vacuous/Unknown 四态), 零 token",
            Wired: true,
            PostActionMarkers: []),

        new(RealMachineReplay, "真机按键回放 + 截图反核",
            [PlanNodeIntents.VerifyLocal],
            "需真机按键通道 (tmux/pty 抽象) 与截图渲染 — 未接线, 本轮不参与路由",
            Wired: false,
            PostActionMarkers: []),

        new(LocalCommand, "本地命令 (ls/git/文件操作)",
            [IntentRecognizer.Intents.FileOperation, IntentRecognizer.Intents.GitOperation],
            "LocalCommandRouter 已存在但未接进计划节点 — 未接线, 本轮不参与路由",
            Wired: false,
            PostActionMarkers: []),
    ];

    private static readonly Dictionary<string, LocalExecutorDescriptor> ById =
        All.ToDictionary(d => d.Id, StringComparer.Ordinal);

    /// <summary>意图 → 已接线执行器 (未接线/未登记 → null ⇒ 调用方必须判 Remote)</summary>
    public static LocalExecutorDescriptor? ForIntent(string intent)
    {
        foreach (var d in All)
        {
            if (!d.Wired)
                continue;
            foreach (var i in d.Intents)
            {
                if (string.Equals(i, intent, StringComparison.Ordinal))
                    return d;
            }
        }
        return null;
    }

    public static LocalExecutorDescriptor? ByIdOrNull(string? id) =>
        id is not null && ById.TryGetValue(id, out var d) ? d : null;

    /// <summary>
    /// 文本里的"远程生成后本地可立刻做"的动作 → 已接线执行器 (Hybrid 判定用)。
    /// 只返回 Wired=true 项 —— 未接线的动作词不会让节点变成 Hybrid (负向控制)。
    /// </summary>
    public static LocalExecutorDescriptor? ForPostAction(string? text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return null;
        foreach (var d in All)
        {
            if (!d.Wired)
                continue;
            foreach (var m in d.PostActionMarkers)
            {
                if (text.Contains(m, StringComparison.OrdinalIgnoreCase))
                    return d;
            }
        }
        return null;
    }

    /// <summary>该执行器是否已接线 (路由/执行体共用同一判据 — 防"登记了但没人实现")</summary>
    public static bool IsWired(string? id) => ByIdOrNull(id)?.Wired == true;
}
