namespace agent.exploration;

/// <summary>
/// 探索配置 (config/base/exploration.yaml; 缺省值=文档 §1.2)。
/// 用户钦定语义: agent 在一块上下文区域/一个文本/一个网络链接内的**最大渐进探索步骤**可配置。
/// </summary>
public sealed class ExplorationConfig
{
    /// <summary>v0.13.3 M-D (R273): 探索链总开关 (env AGENTFRAMEWORK_EXPLORE, 默认开) — A/B 跑测用。</summary>
    public bool Enabled { get; set; } = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_EXPLORE") != "0";

    public int MaxStepsPerContextBlock { get; set; } = 4;
    public int MaxStepsPerText { get; set; } = 2;
    public int MaxStepsPerUrl { get; set; } = 3;
    public int MaxStepsPerDir { get; set; } = 5;
    public int MaxTotalSteps { get; set; } = 16;

    /// <summary>URL 内发现的新 URL 是否继续追 (0=不追; 1=追一层)</summary>
    public int UrlDepth { get; set; } = 1;

    /// <summary>单 URL 抓取最大字节数 (超截断; 防 HTML 巨页)</summary>
    public int MaxUrlBytes { get; set; } = 512 * 1024;

    /// <summary>URL 抓取超时 ms</summary>
    public int UrlTimeoutMs { get; set; } = 8000;

    /// <summary>
    /// 源优先级 (小者先探; 用户例: 上下文中发现的链接 优先于 上下文外的目录)。
    /// key = ExploreSourceKind, value = priority; 来自 config priority 段。
    /// </summary>
    public Dictionary<ExploreSourceKind, int> Priority { get; set; } = new()
    {
        [ExploreSourceKind.ContextBlock] = 1,
        [ExploreSourceKind.Url] = 2,       // 上下文内发现的链接默认走此档
        [ExploreSourceKind.Directory] = 3, // 上下文内提到的目录
        [ExploreSourceKind.Text] = 4,
        [ExploreSourceKind.File] = 5,
    };

    /// <summary>external 目录/链接 (非上下文直接提及) 的降权档 — 用户例: 低于上下文内 URL。</summary>
    public int ExternalPriorityPenalty { get; set; } = 2;

    public int GetBudget(ExploreSourceKind kind) => kind switch
    {
        ExploreSourceKind.ContextBlock => MaxStepsPerContextBlock,
        ExploreSourceKind.Text => MaxStepsPerText,
        ExploreSourceKind.Url => MaxStepsPerUrl,
        ExploreSourceKind.Directory or ExploreSourceKind.File => MaxStepsPerDir,
        _ => 0,
    };

    public int GetPriority(ExploreSourceKind kind, bool fromContext) =>
        Priority.TryGetValue(kind, out var p)
            ? fromContext ? p : p + ExternalPriorityPenalty
            : 9;
}
