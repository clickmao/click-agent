using System.Text.RegularExpressions;
using agent.context;

namespace agent.intent;

/// <summary>
/// 意图级子任务拆解器 (v7.9): 复合句 → 有序子任务序列。
///
/// 现状缺陷: V2 对 "先搜索 X, 然后基于结果写个 Y" 只识别单一意图 (首关键词命中),
/// 后半句被静默忽略。拆解器将复合请求切为独立子任务, 每段独立识别意图并标注依赖。
///
/// 设计约束: 纯规则 (AOT/离线可用, 无 LLM 依赖); 单意图句子退化为单任务, 调用方零特判。
/// </summary>
public static class IntentDecomposer
{
    /// <summary>子任务与前序的关系 (调度器: sequential 串行, parallel 可并行)</summary>
    public enum TaskRelation
    {
        /// <summary>首子任务 (无前序)</summary>
        None,

        /// <summary>顺序连接 (然后/接着/最后) — 与前序保持执行序, 但无数据依赖</summary>
        Sequential,

        /// <summary>并行连接 (同时/以及/还/另外) — 与前序无序可并行</summary>
        Parallel,

        /// <summary>数据依赖 (基于/根据) — 必须等前序产物</summary>
        DependsOnOutput,
    }

    /// <summary>子任务: 原文片段 + 独立意图 + 关系标记</summary>
    public sealed record SubTask(string Text, string Intent, bool DependsOnPrevious, int Order, TaskRelation Relation = TaskRelation.None);

    /// <summary>
    /// 顺序连接词 (中英文)。切分后丢弃连接词本身, 保留两侧子句。
    /// 注意先匹配长词组再匹配短词 (如 "首先" 先于 "先"), 避免残段。
    /// </summary>
    /// <summary>顺序连接词: 切分点, 后续子任务 Relation=Sequential (保执行序, 无数据依赖)</summary>
    private static readonly string[] SequentialConnectors =
    [
        "首先", "然后", "接着", "之后", "其次", "接下来", "最后", "再帮我", "再", "先",
        "then", "after that", "afterwards", "next", "and then"
    ];

    /// <summary>并行连接词: 切分点, 后续子任务 Relation=Parallel (与前序无执行序约束)</summary>
    private static readonly string[] ParallelConnectors =
    [
        "同时", "以及", "另外", "还", "并",
        "also", "meanwhile", "and", "at the same time"
    ];

    /// <summary>
    /// 依赖指示词: 子句以这些词开头 → 依赖前序子任务的输出 (如 "基于结果写文档")。
    /// </summary>
    private static readonly string[] DependencyMarkers =
    [
        "基于", "根据", "按照", "参考", "结合", "用它", "拿它", "以上", "上面的", "刚才",
        "based on", "according to", "using that", "from that"
    ];

    /// <summary>拆解: 复合句 → 子任务序列 (单句返回单元素序列)</summary>
    public static IReadOnlyList<SubTask> Decompose(string content)
    {
        if (string.IsNullOrWhiteSpace(content))
            return [new SubTask(content ?? string.Empty, IntentRecognizer.Intents.General, false, 0)];

        var clauses = SplitClauses(content);
        var tasks = new List<SubTask>(clauses.Count);

        for (var i = 0; i < clauses.Count; i++)
        {
            var (clause, connector) = clauses[i];
            clause = clause.Trim(' ', '\t', '\r', '\n', '，', '。', '；', '、', ',', '.', ';');
            if (clause.Length == 0)
                continue;

            // 关系分级: 数据依赖 ("基于/根据" 切分或开头) > 顺序词 > 并行词 > 首任务
            var relation = i == 0 ? TaskRelation.None
                : connector == "dep" || StartsWithDependencyMarker(clause) ? TaskRelation.DependsOnOutput
                : connector == "seq" ? TaskRelation.Sequential
                : TaskRelation.Parallel;

            var intent = IntentRecognizer.Recognize(clause);
            tasks.Add(new SubTask(clause, intent, relation == TaskRelation.DependsOnOutput, tasks.Count, relation));
        }

        if (tasks.Count == 0)
            return [new SubTask(content, IntentRecognizer.Intents.General, false, 0)];

        return tasks;
    }

    /// <summary>全部子任务意图的并集所需数据源 (V2 装配用)</summary>
    public static HashSet<DataSourceType> AggregateSources(IReadOnlyList<SubTask> tasks)
    {
        var sources = new HashSet<DataSourceType>();
        foreach (var task in tasks)
        {
            foreach (var s in IntentSourceMapping.GetSources(task.Intent))
                sources.Add(s);
        }
        return sources;
    }

    /// <summary>主意图 = 首个子任务的意图 (向后兼容: 模板选择仍由首意图驱动)</summary>
    public static string PrimaryIntent(IReadOnlyList<SubTask> tasks) =>
        tasks.Count > 0 ? tasks[0].Intent : IntentRecognizer.Intents.General;

    /// <summary>连接词切分: 返回 (子句, 连接词类型 "seq"/"par"/"") 序列 (首段 kind="" 无连接词)</summary>
    private static List<(string Clause, string Kind)> SplitClauses(string content)
    {
        // 段结构: (文本, 进入该段的连接词类型 ""=无/seq/par)
        var segments = new List<(string, string)> { (content, "") };

        foreach (var (connectors, kind, requireBoundary) in
                 new[] { (SequentialConnectors, "seq", false), (ParallelConnectors, "par", false), (DependencyMarkers, "dep", true) })
        {
            foreach (var connector in connectors)
            {
                var next = new List<(string, string)>(segments.Count);
                foreach (var (seg, segKind) in segments)
                {
                    // 分隔词右侧的新段标记当前连接词类型; 延续段 (无该分隔词/首段) 保留原类型
                    var parts = SplitByConnector(seg, connector, requireBoundary);
                    for (var i = 0; i < parts.Count; i++)
                        next.Add((parts[i], i == 0 ? segKind : kind));
                }
                segments = next;
            }
        }

        return segments;
    }

    private static List<string> SplitByConnector(string text, string connector, bool requireBoundary = false)
    {
        var parts = new List<string>();
        var comparison = StringComparison.OrdinalIgnoreCase;

        var isEnglish = connector.All(char.IsAsciiLetterOrDigit);
        var searchFrom = 0;
        var segmentStart = 0;   // 当前未切割段的起点
        var cut = false;        // 是否发生真实切分

        while (searchFrom <= text.Length)
        {
            int idx;
            if (isEnglish)
            {
                idx = FindEnglishConnector(text, connector, searchFrom);
            }
            else
            {
                idx = text.IndexOf(connector, searchFrom, comparison);
            }

            if (idx < 0)
                break;

            // "先/再/还/并/同时" 等单字中文词有误切风险: 前后必须非汉字 (如 "再次" 不切)
            if (!isEnglish && connector.Length == 1 && !SafeSingleCharSplit(text, idx))
            {
                searchFrom = idx + connector.Length;
                continue;
            }

            // 依赖词 ("基于/结合" 等) 只在子句边界切分: 前一字符必须是句读/空白, 防止 "把A和B结合" 误切
            if (requireBoundary && idx > 0 && !IsClauseBoundary(text[idx - 1]))
            {
                searchFrom = idx + connector.Length;
                continue;
            }

            // 真实切分: 记录前段, 推进段起点
            parts.Add(text[segmentStart..idx]);
            segmentStart = idx + connector.Length;
            searchFrom = segmentStart;
            cut = true;
        }

        // 尾段: 有切分时补余段; 无切分时返回整段
        parts.Add(cut ? text[segmentStart..] : text);
        return parts;
    }

    /// <summary>句读/空白 = 子句边界</summary>
    private static bool IsClauseBoundary(char c) =>
        c is ' ' or '\t' or '，' or '。' or '；' or '、' or ',' or '.' or ';' or '\n' or '\r' or '！' or '？' or '!' or '?';

    private static int FindEnglishConnector(string text, string connector, int start)
    {
        var idx = text.IndexOf(connector, start, StringComparison.OrdinalIgnoreCase);
        while (idx >= 0)
        {
            var beforeOk = idx == 0 || !char.IsLetterOrDigit(text[idx - 1]);
            var after = idx + connector.Length;
            var afterOk = after >= text.Length || !char.IsLetterOrDigit(text[after]);
            if (beforeOk && afterOk)
                return idx;
            idx = text.IndexOf(connector, idx + 1, StringComparison.OrdinalIgnoreCase);
        }
        return -1;
    }

    /// <summary>单字中文连接词的安全切分判定: 左右邻接字符都不是汉字才切</summary>
    private static bool SafeSingleCharSplit(string text, int idx)
    {
        var beforeOk = idx == 0 || !IsHan(text[idx - 1]);
        var after = idx + 1;
        var afterOk = after >= text.Length || !IsHan(text[after]);
        // 单字词至少一侧贴近标点/空白/边界才可靠 ("先搜索" 中 "先" 后是汉字 → 不切)
        return beforeOk || afterOk;
    }

    private static bool IsHan(char c) => c is >= (char)0x4E00 and <= (char)0x9FFF;

    private static bool StartsWithDependencyMarker(string clause)
    {
        foreach (var marker in DependencyMarkers)
        {
            if (clause.StartsWith(marker, StringComparison.OrdinalIgnoreCase))
                return true;
        }
        return false;
    }
}
