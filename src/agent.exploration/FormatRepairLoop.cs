namespace agent.exploration;

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
