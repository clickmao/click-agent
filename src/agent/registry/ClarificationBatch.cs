using agent.intent;
using agent.core;

namespace agent.registry;

/// <summary>
/// 批量问询 (v7.13): 问用户不一条一条问 — 按 GroupId/节点分组一次给全部问题,
/// 一次交互收全部答案。每组单条交互, 减少打断次数; 校验失败只重问出错条目。
/// </summary>
public static class ClarificationBatch
{
    /// <summary>单个问询条目的应答结果</summary>
    public sealed class ItemAnswer
    {
        public ClarificationItem Item { get; init; } = null!;
        public bool Answered { get; init; }
        public string? Value { get; init; }
        public string? Error { get; init; }
        public PromptAnswerSource Source { get; init; } = PromptAnswerSource.RealUser;
    }

    /// <summary>一批的应答结果</summary>
    public sealed class BatchResult
    {
        public List<ItemAnswer> Answers { get; } = new();
        public bool AllAnswered => Answers.All(a => a.Answered);
        public int AnsweredCount => Answers.Count(a => a.Answered);
    }

    /// <summary>分组: 待澄清条目按 GroupId (空则按 NodeId) 分组</summary>
    public static List<List<ClarificationItem>> Group(IEnumerable<ClarificationItem> items)
    {
        var groups = new Dictionary<string, List<ClarificationItem>>();
        foreach (var item in items)
        {
            var key = string.IsNullOrEmpty(item.GroupId) ? item.NodeId : item.GroupId;
            if (!groups.TryGetValue(key, out var list))
                groups[key] = list = new List<ClarificationItem>();
            list.Add(item);
        }
        return groups.Values.ToList();
    }

    /// <summary>
    /// R375 (exp2 P0-3): 条目 → 通道条目 —— 选项/数据类型/多选/默认值**结构化**下发。
    /// 旧实现只把菜单拼进 Describe() 文本, 前端拿不到 options[] → 只能当自由文本输入 (菜单名存实亡)。
    /// </summary>
    private static CredentialItem BuildItem(ClarificationItem it, string? suffix = null)
    {
        var item = new CredentialItem
        {
            Key = it.ParameterName,
            DisplayName = suffix is null ? Describe(it) : $"{Describe(it)} ({suffix})",
            Required = true,
            Sensitive = it.Kind == ClarificationKinds.ApiKey,
            DataType = MapDataType(it),
            MultiSelect = it.DataType == PromptDataType.MultiChoice,
            DefaultValue = it.SuggestedValues.Count > 0 ? it.SuggestedValues[0] : null,
        };
        foreach (var c in it.Choices)
            item.Choices.Add(new CredentialChoice
            {
                Value = c,
                Label = c,
                Recommended = it.SuggestedValues.Contains(c),
            });
        return item;
    }

    /// <summary>R375: 数据类型透传 (choice/multi_choice 是菜单渲染的关键; 未知类型退化为 text, 不臆造)。</summary>
    private static string MapDataType(ClarificationItem it) => it.DataType switch
    {
        PromptDataType.Choice => "choice",
        PromptDataType.MultiChoice => "multi_choice",
        PromptDataType.Number => "number",
        PromptDataType.Integer => "integer",
        PromptDataType.Boolean => "boolean",
        PromptDataType.Date => "date",
        PromptDataType.Time => "time",
        PromptDataType.DateTime => "datetime",
        PromptDataType.Url => "url",
        PromptDataType.Email => "email",
        PromptDataType.Path => "path",
        PromptDataType.Port => "port",
        _ => "text",
    };

    /// <summary>
    /// 执行一批问询 (调 prompt 一次): 每个条目按 DataType 校验,
    /// 校验失败立即重问该条 (最多 maxRetries 次), 仍失败则该条放弃 (返回 Error, 不伪造)。
    /// v7.13: 问询前应用偏好库 (类似问题复用历史偏好), 合法答案回写偏好 (只记模式, 不记凭据/原值)。
    /// </summary>
    public static async Task<BatchResult> AskAsync(
        IUserPromptService prompts,
        string serviceName,
        IReadOnlyList<ClarificationItem> batch,
        int maxRetries = 2,
        CancellationToken ct = default,
        ClarificationPreferenceStore? preferences = null)
    {
        var result = new BatchResult();

        // 偏好复用: 有历史偏好的条目 → SuggestedValues/选项序预排 (同类问题不重复问同样的东西)
        if (preferences != null)
            foreach (var it in batch)
                preferences.ApplyTo(it);

        // 问询请求打包: 每个条目一个 CredentialItem (非敏感参数也走同一通道, Sensitive 标记控制打码)
        var request = new CredentialRequest
        {
            ServiceName = serviceName,
            Purpose = batch.Count == 1
                ? batch[0].Question
                : $"{batch.Count} 个参数需要确认 (一次回答全部):\n" +
                  string.Join("\n", batch.Select((it, i) => $"  {i + 1}. {it.Question}")),
            Origin = PromptOrigin.Main(),
        };

        foreach (var it in batch)
            request.Items.Add(BuildItem(it));

        for (var attempt = 0; attempt <= maxRetries; attempt++)
        {
            var answers = await prompts.RequestCredentialsAsync(request, ct);
            if (answers == null)
            {
                // 用户整体放弃 — 全部标未答
                foreach (var it in batch)
                    result.Answers.Add(new ItemAnswer { Item = it, Answered = false, Error = "用户放弃" });
                return result;
            }

            var pending = new List<ClarificationItem>();
            foreach (var it in batch)
            {
                if (!answers.TryGetValue(it.ParameterName, out var raw))
                {
                    result.Answers.Add(new ItemAnswer { Item = it, Answered = false, Error = "未提供" });
                    continue;
                }

                var (ok, normalized, error) = PromptDataValidator.Validate(it.DataType, raw, it.Choices);
                if (ok)
                {
                    preferences?.RecordAnswer(it, normalized); // 偏好学习 (凭据被 Store 内部拒收)
                    result.Answers.Add(new ItemAnswer { Item = it, Answered = true, Value = normalized });
                }
                else
                    pending.Add(it);
            }

            if (pending.Count == 0)
                return result;

            // 只重问失败条目
            batch = pending;
            request.Items.Clear();
            foreach (var it in pending)
            {
                request.Items.Add(BuildItem(it, "上次输入无效, 重试"));
            }
        }

        // 重试耗尽 — 剩余条目放弃
        foreach (var it in batch)
            result.Answers.Add(new ItemAnswer { Item = it, Answered = false, Error = "校验失败, 重试耗尽" });
        return result;
    }

    private static string Describe(ClarificationItem it)
    {
        var typeHint = it.DataType switch
        {
            PromptDataType.Choice => $" [选择: {string.Join(" / ", it.Choices)}]",
            PromptDataType.MultiChoice => $" [多选: {string.Join(" / ", it.Choices)}]",
            PromptDataType.Number => " [数字]",
            PromptDataType.Integer => " [整数]",
            PromptDataType.Date => " [日期 yyyy-MM-dd]",
            PromptDataType.Path => " [路径]",
            PromptDataType.Url => " [URL]",
            PromptDataType.Boolean => " [是/否]",
            _ => "",
        };
        return it.ParameterName + typeHint;
    }
}
