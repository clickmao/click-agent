using System.Text.RegularExpressions;

namespace agent.intent;

/// <summary>
/// 意图识别器: 规则化关键词 + 单词边界匹配, 输出 9 种意图。
/// 设计约束: 无 LLM 依赖 (AOT/离线可用)、编译期意图常量、词表可测试。
///
/// v7.6 修复的误判矩阵:
/// - "ls/cat/dir/git/push/pull" 等英文词曾用裸 Contains 子串匹配 →
///   "sales" 命中 ls、"category" 命中 cat → 必须词边界匹配
/// - 中文单字动词 "写/找" 语义过宽 → 升级为双字词组优先 + 单字词组上下文限定
/// </summary>
public static partial class IntentRecognizer
{
    /// <summary>意图常量 (与 IntentPromptTemplates 模板键一致, 编译期拼写安全)</summary>
    public static class Intents
    {
        public const string CodeGeneration = "code_generation";
        public const string CodeModification = "code_modification";
        public const string CodeReview = "code_review";
        public const string TestGeneration = "test_generation";
        public const string Search = "search";
        public const string FileOperation = "file_operation";
        public const string GitOperation = "git_operation";
        public const string MemorySearch = "memory_search";
        public const string General = "general";
    }

    /// <summary>全部已知意图 (供映射表/校验用)</summary>
    public static readonly IReadOnlyCollection<string> KnownIntents = new[]
    {
        Intents.CodeGeneration, Intents.CodeModification, Intents.CodeReview,
        Intents.TestGeneration, Intents.Search, Intents.FileOperation,
        Intents.GitOperation, Intents.MemorySearch, Intents.General
    };

    /// <summary>
    /// 意图规则: 按 (意图, 词表) 组织; 顺序即优先级 (先具体后泛化)。
    /// 英文词用词边界正则, 中文词用包含匹配 (中文无词边界概念)。
    /// </summary>
    private static readonly (string Intent, string[] CnKeywords, string[] EnWordPatterns)[] Rules =
    {
        // 0. 创作类 (必须在代码生成前: "写首诗/写文章/写故事" 是创作不是代码 — R116 真缺陷 47:
        //    "帮我写一首关于秋天的短诗" 曾命中 "帮我写" → code_generation → forecast/技能路由全偏)
        (Intents.General,
            ["写一首", "写首诗", "写一篇", "写篇文章", "写个故事", "写一个故事", "写故事", "写首歌词", "写一首诗", "作一首", "填一首", "写一副对联", "写对联", "写首俳句", "写段歌词"],
            [@"\bwrite\s+(a\s+)?(poem|story|essay|song)\b"]),

        // 1. 测试生成 (必须在代码生成前: "写测试" 是测试不是代码)
        (Intents.TestGeneration,
            ["写测试", "单元测试", "测试用例", "生成测试", "补测试"],
            [@"\bwrite\s+tests?\b", @"\bunit\s+test", @"\btest\s+cases?\b"]),

        // 2. Git 操作 ("git" 词边界: gitignore 不算; push/pull/commit 词边界)
        (Intents.GitOperation,
            ["提交代码", "拉取代码", "分支", "合并分支", "版本回退", "提交到", "推送到", "推送代码", "推送", "上传到", "代码回退", "检出"],
            [@"\bgit\b", @"\bcommit\b", @"\bpush\b", @"\bpull\b", @"\bbranch\b", @"\bmerge\b", @"\brebase\b"]),

        // 3. 代码生成 (中文动词限定: "写代码/写个/写一个/实现" 而非裸 "写")
        (Intents.CodeGeneration,
            ["写代码", "写个", "写一个", "新建", "创建", "生成", "实现一个", "帮我写", "编码"],
            [@"\bimplement\b", @"\bcreate\s+(a\s+)?(class|function|method|component|api)"]),

        // 4. 代码修改
        (Intents.CodeModification,
            ["修改", "改动", "重构", "调整代码", "更新代码", "改一下", "改改"],
            [@"\brefactor\b", @"\bmodify\b", @"\bfix\s+(the|this|a)\b"]),

        // 5. 代码审查 ("检查代码" 比 "review" 更具体; review 有名词歧义 (评审会议) 仍保留)
        (Intents.CodeReview,
            ["审查", "检查代码", "代码评审", "评审代码", "看下代码", "看看代码"],
            [@"\bcode\s+review\b", @"\breview\s+(the\s+)?code\b"]),

        // 6. 文件操作 (ls/dir/cat 词边界: sales/category 不再误判)
        (Intents.FileOperation,
            ["列出", "文件列表", "目录结构", "读取", "打开文件", "删掉文件", "移动文件", "复制文件"],
            [@"\bls\b", @"\bdir\b", @"\bcat\b", @"\blist\s+files\b", @"\bread\s+(the\s+)?file\b"]),

        // 7. 记忆搜索 ("之前/上次" 是强信号; "历史" 保留)
        (Intents.MemorySearch,
            ["之前说过", "之前的", "之前说", "上次", "记得吗", "聊天记录", "对话历史"],
            [@"\bremember\b", @"\blast\s+time\b", @"\bpreviously\b"]),

        // 8. 搜索 ("查找/搜索" 明确; 裸 "找" 过宽 → 限定 "找一下/找找/帮我找")
        (Intents.Search,
            ["搜索", "查找", "搜一下", "查一下", "找一下", "找找", "帮我找", "最新消息", "是什么"],
            [@"\bsearch\s+(for|the)\b", @"\blook\s+up\b", @"\bgoogle\b"]),

        // 9. 兜底 general 不设词表
    };

    [GeneratedRegex(@"[\w\-]+")]
    private static partial Regex WordPattern();

    /// <summary>识别意图 (返回 IntentTypes 常量之一)</summary>
    public static string Recognize(string content)
    {
        if (string.IsNullOrWhiteSpace(content))
            return Intents.General;

        foreach (var (intent, cnKeywords, enPatterns) in Rules)
        {
            foreach (var kw in cnKeywords)
            {
                if (content.Contains(kw, StringComparison.OrdinalIgnoreCase))
                    return intent;
            }

            foreach (var pattern in enPatterns)
            {
                if (Regex.IsMatch(content, pattern, RegexOptions.IgnoreCase))
                    return intent;
            }
        }

        return Intents.General;
    }
}
