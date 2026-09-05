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

    /// <summary>子任务: 原文片段 + 独立意图 + 关系标记 + 规则置信度</summary>
    public sealed record SubTask(string Text, string Intent, bool DependsOnPrevious, int Order, TaskRelation Relation = TaskRelation.None,
        double Confidence = 1.0, ConfidenceFlags Flags = ConfidenceFlags.None);

    /// <summary>置信度扣分项 (可组合): 哪些信号导致不确定 — 证据补充请求的依据</summary>
    [Flags]
    public enum ConfidenceFlags
    {
        None = 0,

        /// <summary>意图词命中弱 (仅兜底规则命中, 无强特征)</summary>
        WeakIntent = 1,

        /// <summary>数据边界不清 (指代词/省略宾语: "这个/它/上面的文件")</summary>
        AmbiguousReference = 2,

        /// <summary>必需参数缺失 (意图要求的参数在子句中找不到)</summary>
        MissingParameter = 4,

        /// <summary>子句过短 (信息量不足, 如 "处理一下")</summary>
        TooVague = 8,

        /// <summary>与前序子任务存在未指明的数据关系 (疑似省略 "基于结果")</summary>
        SuspiciousDependency = 16,
    }

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
            var (confidence, flags) = AssessConfidence(clause, intent, i, tasks);
            tasks.Add(new SubTask(clause, intent, relation == TaskRelation.DependsOnOutput, tasks.Count, relation, confidence, flags));
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

    /// <summary>
    /// 指代词/省略宾语 — 数据边界不清的信号 ("这个/它/该文件/上面的")。
    /// 这类子任务的输入对象不明确 → 需要向发起者索要证据补充。
    /// </summary>
    private static readonly string[] AmbiguousReferences =
    [
        "这个", "那个", "它", "它们", "该文件", "此文件", "上面的文件", "那个文件",
        "这个数据", "该数据", "上述", "之前那个", "刚才那个", "it", "this", "that",
    ];

    /// <summary>意图强特征词: 命中这些说明意图判定有据 (抽样核对 IntentRecognizer 词表核心)</summary>
    private static readonly string[] StrongIntentMarkers =
    [
        "搜索", "查", "写", "读", "删除", "创建", "修改", "执行", "翻译", "总结", "分析",
        "search", "write", "read", "delete", "create", "run", "translate", "summarize",
    ];

    /// <summary>
    /// 置信度评估 (纯规则): 从 1.0 起, 按扣分项递减。
    /// 设计约束: 不调 LLM — 拆解是每次输入的必经路径, 必须微秒级。
    /// </summary>
    private static (double Confidence, ConfidenceFlags Flags) AssessConfidence(
        string clause, string intent, int index, List<SubTask> prior)
    {
        var flags = ConfidenceFlags.None;
        double confidence = 1.0;

        // ① 子句过短 (<4 字符且非纯参数): 信息量不足
        if (clause.Trim().Length < 4)
        {
            flags |= ConfidenceFlags.TooVague;
            confidence -= 0.35;
        }

        // ② 指代词: 数据边界不清
        var ambig = AmbiguousReferences.FirstOrDefault(r =>
            clause.Contains(r, StringComparison.OrdinalIgnoreCase));
        if (ambig != null)
        {
            flags |= ConfidenceFlags.AmbiguousReference;
            confidence -= 0.25;
        }

        // ③ 意图弱命中: general 兜底且无强特征词
        if (intent == IntentRecognizer.Intents.General &&
            !StrongIntentMarkers.Any(m => clause.Contains(m, StringComparison.OrdinalIgnoreCase)))
        {
            flags |= ConfidenceFlags.WeakIntent;
            confidence -= 0.20;
        }

        // ④ 疑似省略依赖: 非首任务、无显式依赖标记, 但含 "结果/输出/内容" 等产物词
        if (index > 0 && relation(prior, index) != TaskRelation.DependsOnOutput &&
            (clause.Contains("结果") || clause.Contains("输出") || clause.Contains("返回的内容")))
        {
            flags |= ConfidenceFlags.SuspiciousDependency;
            confidence -= 0.15;
        }

        // ⑤ 必需参数缺失: 文件操作无路径对象, 代码生成无语言/目标 (轻量启发)
        if (intent == IntentRecognizer.Intents.FileOperation &&
            !clause.Contains("文件") && !clause.Contains("路径") && !clause.Contains("/"))
        {
            flags |= ConfidenceFlags.MissingParameter;
            confidence -= 0.20;
        }

        return (Math.Max(0.0, confidence), flags);
    }

    private static TaskRelation relation(List<SubTask> tasks, int index) =>
        index > 0 && tasks.Count >= index ? tasks[index - 1].Relation : TaskRelation.None;

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
