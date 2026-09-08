namespace agent.exploration;

/// <summary>
/// v0.13.2 G1 (用户钦定) — 格式修复插件契约。
/// 收敛环: ①块内检测 → ②独立查找 → ③程序校验 → ④本地修复 → ⑤LLM 重修 (循环)。
/// 与 ImageRenderPlugin 同构的注册表模式; 本地修复器只用确定性规则 (LLM 只在环入口)。
/// </summary>
public interface IFormatRepairPlugin
{
    /// <summary>格式名 (json/csv/xml/generic — skill 分派键)</summary>
    string Format { get; }

    /// <summary>能否识别该格式的候选内容 (格式头/结构特征)</summary>
    bool CanDetect(string text);

    /// <summary>
    /// ②独立查找: 从全文提取最合法候选区段 (括号配平/引号扫描)。
    /// 找到返回 (start, length); 找不到返回 null。
    /// </summary>
    (int Start, int Length)? FindCandidate(string text);

    /// <summary>③程序校验: 返回错误列表 (空=合法)。必须用平台原生 parser 当权威。</summary>
    IReadOnlyList<string> Validate(string text);

    /// <summary>④本地修复 (确定性规则)。返回修复后文本 + 修改点数。</summary>
    (string Fixed, int ChangedN) Repair(string text);
}

/// <summary>修复单步结果 (打点 format_repair 源数据)。</summary>
public sealed class FormatRepairStep
{
    public string Stage { get; set; } = string.Empty;   // fenced|found|validate|local_fix|llm_round
    public bool Ok { get; set; }
    public int RoundsN { get; set; }
    public int ChangedN { get; set; }
    public string? Error { get; set; }
}

/// <summary>修复配置 (config format_repair 段 — 用户钦定)。</summary>
public sealed class FormatRepairConfig
{
    public bool Enabled { get; set; } = true;
    /// <summary>LLM 连续修复失败上限 (有校验机制所以可计数 — 用户钦定)</summary>
    public int MaxLlmRounds { get; set; } = 3;
    /// <summary>notify_user | agent_autonomous (托管权限 → 超限后静默探索新方案)</summary>
    public string OnExhaust { get; set; } = "notify_user";
    /// <summary>启用的修复插件 (skill-校验矩阵: 决定 ①是否进入/④是否可用)</summary>
    public string[] Plugins { get; set; } = { "json", "csv", "xml" };
}

/// <summary>
/// 格式修复插件注册表 — 技能-校验矩阵判定 (用户钦定硬性规则):
/// ✓技能+✓校验+✓程序 → 完整收敛环; ✓技能+✓校验+✗程序 → 全程 LLM 修复;
/// ✓技能+✗校验 → 不进入循环修复; ✗技能 → 通用降级。
/// </summary>
public sealed class FormatRepairRegistry
{
    private readonly List<IFormatRepairPlugin> _plugins;
    public FormatRepairRegistry(IEnumerable<IFormatRepairPlugin> plugins) => _plugins = plugins.ToList();

    public IFormatRepairPlugin? Get(string format) =>
        _plugins.FirstOrDefault(p => string.Equals(p.Format, format, StringComparison.OrdinalIgnoreCase));

    /// <summary>该格式是否有本地校验能力 (非 Generic 专用插件存在 = 有)</summary>
    public bool HasValidator(string format) => Get(format) is not null;

    /// <summary>是否有本地修复程序 (专用插件存在 = 有; 只有 generic = 无④)</summary>
    public bool HasLocalRepairer(string format) =>
        _plugins.Any(p => string.Equals(p.Format, format, StringComparison.OrdinalIgnoreCase)
                          && !string.Equals(p.Format, "generic", StringComparison.OrdinalIgnoreCase));
}

/// <summary>
/// 修复循环执行器 — 实现①→⑤状态机 (LLM 交互由宿主注入: requestLlmRound 委托)。
/// </summary>
public sealed class FormatRepairLoop
{
    private readonly FormatRepairRegistry _registry;
    private readonly FormatRepairConfig _config;

    public FormatRepairLoop(FormatRepairRegistry registry, FormatRepairConfig? config = null)
    {
        _registry = registry;
        _config = config ?? new FormatRepairConfig();
    }

    /// <summary>
    /// 修复入口。requestLlmRound: 宿主侧把 (原文+错误列表) 交 LLM 重修, 返回 LLM 新回复。
    /// 返回 (最终文本, 是否通过, 步骤轨迹)。
    /// </summary>
    public async Task<(string Text, bool Passed, IReadOnlyList<FormatRepairStep> Trail)> RunAsync(
        string format, string originalText, string llmReply,
        Func<string, IReadOnlyList<string>, Task<string>> requestLlmRound,
        CancellationToken ct = default)
    {
        var trail = new List<FormatRepairStep>();
        // 矩阵: 技能不存在 → 通用降级; 校验机制不存在 → 不进入修复 (用户钦定):
        var plugin = _registry.Get(format);
        if (plugin is null)
        {
            var generic = _registry.Get("generic");
            if (generic is null)
                return (llmReply, false, new[] { new FormatRepairStep { Stage = "matrix", Ok = false, Error = "无可用修复插件 (技能缺失)" } });
            plugin = generic;
        }
        var hasLocal = _registry.HasLocalRepairer(format);
        var current = llmReply;
        var rounds = 0;
        while (true)
        {
            ct.ThrowIfCancellationRequested();
            // ① 块内检测 (```fmt fenced):
            var fenced = ExtractFenced(current, format);
            var candidate = fenced ?? plugin.FindCandidate(current)?.Let(r => current.Substring(r.Start, r.Length));
            var stage = fenced is not null ? "fenced" : (candidate is not null ? "found" : "none");
            if (candidate is null)
            {
                // ②查找失败 → ⑤交回 LLM:
                if (rounds >= _config.MaxLlmRounds)
                {
                    trail.Add(new FormatRepairStep { Stage = "exhaust", Ok = false, RoundsN = rounds, Error = "LLM 修复轮数耗尽 (查找失败)" });
                    return (current, false, trail);
                }
                rounds++;
                trail.Add(new FormatRepairStep { Stage = "llm_round", Ok = false, RoundsN = rounds, Error = "未找到合法候选区段" });
                current = await requestLlmRound(current, new[] { "回复中未检测到可解析的 " + format + " 内容, 请将修复结果完整放入 ```" + format + " 代码块内" }).ConfigureAwait(false);
                continue;
            }
            // ③程序校验 (平台原生 parser 当权威):
            var errors = plugin.Validate(candidate);
            if (errors.Count == 0)
            {
                trail.Add(new FormatRepairStep { Stage = stage, Ok = true, RoundsN = rounds });
                return (candidate, true, trail);
            }
            // ④本地修复 (矩阵: 无本地程序 → 全程 LLM):
            if (hasLocal)
            {
                var (fixedText, changedN) = plugin.Repair(candidate);
                var errors2 = plugin.Validate(fixedText);
                if (errors2.Count == 0)
                {
                    trail.Add(new FormatRepairStep { Stage = "local_fix", Ok = true, RoundsN = rounds, ChangedN = changedN });
                    return (fixedText, true, trail);
                }
                candidate = fixedText; // 修了一部分, 带着残余错误交 LLM
                errors = errors2;
            }
            // ⑤交回 LLM (计数 — 用户钦定可计数):
            if (rounds >= _config.MaxLlmRounds)
            {
                trail.Add(new FormatRepairStep { Stage = "exhaust", Ok = false, RoundsN = rounds, Error = "LLM 修复轮数耗尽: " + string.Join("; ", errors.Take(3)) });
                return (current, false, trail);
            }
            rounds++;
            trail.Add(new FormatRepairStep { Stage = "llm_round", Ok = false, RoundsN = rounds, Error = errors.FirstOrDefault() });
            current = await requestLlmRound(current, errors).ConfigureAwait(false);
        }
    }

    /// <summary>①```fmt fenced 块提取 (用户钦定: 修复代码必须放块内)。</summary>
    public static string? ExtractFenced(string text, string format)
    {
        if (string.IsNullOrEmpty(text)) return null;
        var tag = "```" + format;
        var i = text.IndexOf(tag, StringComparison.OrdinalIgnoreCase);
        if (i < 0) return null;
        var bodyStart = i + tag.Length;
        if (bodyStart < text.Length && text[bodyStart] == '\n') bodyStart++;
        var end = text.IndexOf("```", bodyStart, StringComparison.Ordinal);
        var body = end < 0 ? text[bodyStart..] : text[bodyStart..end];
        body = body.Trim();
        return body.Length > 0 ? body : null;
    }
}

internal static class RepairExtensions
{
    public static TOut Let<TIn, TOut>(this TIn v, Func<TIn, TOut> f) => f(v);
}
