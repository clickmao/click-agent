using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using agent.config;
using agent.registry;
using agent.skills;

namespace agent.intent;


/// <summary>
/// 本地先行批次 (v0.22.0 exp9 D4): 无依赖本地节点的**真并行**执行句柄。
/// 为什么需要句柄: 这些节点的输入 (用户原文) 在远程生成前就在手, 因此可以在模型调用
/// **进行中**就跑完 —— 而不是等远程产物回来再跑 (那是 D3 的串行语义)。
/// </summary>
public sealed class LocalFirstRun
{
    /// <summary>本批次节点 id (前端/KPI 显示"哪些步先跑了")</summary>
    public required IReadOnlyList<string> NodeIds { get; init; }

    /// <summary>批次完成信号 (PlanRunner.RunAsync 会 await 它并复用结果, **绝不重复执行**)</summary>
    public required Task Pending { get; set; }

    public required long StartedUs { get; init; }

    /// <summary>批次结束时刻 (全部无依赖本地节点落终态)</summary>
    public long EndedUs { get; internal set; }

    /// <summary>批次耗时 (微秒): 亚毫秒本地节点必须用 µs 计量, 否则重叠会被舍入成 0</summary>
    public long ElapsedUs => Math.Max(0, EndedUs - StartedUs);

    public int ElapsedMs => (int)(ElapsedUs / 1000);

    internal ConcurrentDictionary<string, NodeOutcome> Outcomes { get; } = new(StringComparer.Ordinal);

    internal ConcurrentDictionary<string, NodeExecutionResult> Results { get; } = new(StringComparer.Ordinal);

    internal void MarkEnded() => EndedUs = Monotonic.NowUs();
}
