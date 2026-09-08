using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.11.0 R39b/R39c: 隔离判定修复 — ascii 连写 4-gram 交叉匹配 + 实现询问一票否决。
/// v0.11.0 R149 (用户质疑: TaskRelevanceChecker 不可靠/批测覆盖空心): 补对抗样本族 —
/// 八类真实对话形态逐类锚定判定边界, 防止 "组件存在但判定空心" 复发。
/// </summary>
public class TaskRelevanceCheckerTests
{
    [Fact]
    public void Ascii_Compound_Technames_Share_Gram()
    {
        // goal 实体含 "RESTAPI", 新消息 "用 FastAPI 怎么写" → 4-gram 交叉 (stap/tapi) = 重叠, 不隔离
        var goal = new List<string> { "RESTAPI", "设计服务" };
        var (isolated, score, reason) = agent.intent.TaskRelevanceChecker.Check(goal, "coding", "用 FastAPI 怎么写", "coding");
        Assert.False(isolated);
    }

    [Fact]
    public void Deixis_With_Inserted_Spaces_Still_Vetoes()
    {
        // R183 泛化: "刚才 那个" 空格/标点插入 → 归一化后仍命中词表 (用户指出的脆弱点)
        var goal = new List<string> { "向量数据库", "对比报告" };
        var (isolated, _, _) = agent.intent.TaskRelevanceChecker.Check(goal, "coding", "刚才 那个方案再讲一下", "general");
        Assert.False(isolated);
    }

    [Fact]
    public void Deixis_With_Punctuation_Inserted_Still_Vetoes()
    {
        // "记，得" — 中文标点插入同样免疫 (归一化去标点)
        var goal = new List<string> { "Redis", "缓存" };
        var (isolated, _, _) = agent.intent.TaskRelevanceChecker.Check(goal, "coding", "还记，得上次说了什么吗？", "general");
        Assert.False(isolated);
    }

    [Fact]
    public void FullWidth_Punct_Short_Question_Structural_Signal()
    {
        // 全角"？"+ 短问句 → 结构信号 (语言无关) 减分, 不隔离
        var goal = new List<string> { "Redis", "缓存" };
        var (isolated, score, reason) = agent.intent.TaskRelevanceChecker.Check(goal, "coding", "为什么？", "general");
        Assert.False(isolated);
    }

    [Fact]
    public void Memory_Recall_Deixis_Vetoes_Isolation()
    {
        // R182 (真缺陷 61): "还记得上一条消息" — 记忆回指必然依赖上文, 一票否决隔离
        var goal = new List<string> { "向量数据库", "对比报告" };
        var (isolated, score, reason) = agent.intent.TaskRelevanceChecker.Check(goal, "coding", "还记得我上一条消息说了什么吗", "general");
        Assert.False(isolated);
    }

    [Fact]
    public void Last_Message_Deixis_Vetoes_Isolation()
    {
        // "上一条消息" 变体覆盖
        var goal = new List<string> { "Redis", "缓存" };
        var (isolated, score, reason) = agent.intent.TaskRelevanceChecker.Check(goal, "coding", "你上次说的方案继续展开一下", "general");
        Assert.False(isolated);
    }

    [Fact]
    public void HowTo_Short_Message_Vetoes_Isolation()
    {
        // "用 requests 库怎么写" — 实现询问 + 短消息 → 一票否决 (即使与爬虫标题零重叠)
        var goal = new List<string> { "python", "爬虫", "网页标题" };
        var (isolated, score, reason) = agent.intent.TaskRelevanceChecker.Check(goal, "coding", "用 requests 库怎么写", "coding");
        Assert.False(isolated);
    }

    [Fact]
    public void Truly_OffTopic_Still_Isolated()
    {
        // 离题诗 (长消息, 无实现询问词) → 保持隔离
        var goal = new List<string> { "csharp", "性能优化", "学习计划" };
        var (isolated, score, reason) = agent.intent.TaskRelevanceChecker.Check(goal, "task_planning",
            "写一首关于秋天的诗，要求意境优美感情真挚字数不少于两百字", "creative_writing");
        Assert.True(isolated);
    }

    // ===== R149 对抗样本族 (八类) =====

    [Theory]
    [InlineData("它有什么问题")]          // 指代词一票否决
    [InlineData("继续刚才的分析")]        // "继续"+"刚才" 双命中
    [InlineData("然后呢")]                // 短指代
    [InlineData("那个方案再优化一下")]    // 指代+任务延续
    public void Deixis_Veto_Matrix(string msg)
    {
        // 指代词族: 无论实体/意图如何, 一律不隔离 (强依赖上文)
        var goal = new List<string> { "redis", "缓存" };
        var (isolated, score, reason) = agent.intent.TaskRelevanceChecker.Check(goal, "coding", msg, "general");
        Assert.False(isolated);
        Assert.Equal(0, score);
    }

    [Fact]
    public void Entity_Overlap_Negative_Even_When_Intent_Differs()
    {
        // 实体重叠 (-2) 压过意图差异 (+1): 同主题不同意图 → 不隔离
        var goal = new List<string> { "redis", "缓存优化", "热点key" };
        var (isolated, score, reason) = agent.intent.TaskRelevanceChecker.Check(goal, "coding", "redis 持久化配置帮我写一下", "config");
        Assert.False(isolated);
    }

    [Fact]
    public void Empty_Goal_Entities_Never_Isolate_On_Entity_Path()
    {
        // goal 实体为空 (新会话/锚缺失): 实体路径不给分, 措辞避开离题词 — 意图差 1 分 < 阈值 2 → 不隔离
        var goal = new List<string>();
        var (isolated, score, reason) = agent.intent.TaskRelevanceChecker.Check(goal, "coding", "附近有什么好吃的火锅店", "search");
        Assert.False(isolated);
    }

    [Fact]
    public void Empty_Goal_With_OffTopicMarker_And_IntentDiff_Isolates()
    {
        // R149 行为锚定: goal 空 + 显式离题词 (+1) + 意图差 (+1) = 2 → 仍隔离
        // (锚缺失时组件退化为"信号词+意图"判定 — 已知边界, 有意保留)
        var goal = new List<string>();
        var (isolated, score, reason) = agent.intent.TaskRelevanceChecker.Check(goal, "coding", "帮我查下天气", "search");
        Assert.True(isolated);
    }

    [Fact]
    public void OffTopic_Marker_Alone_Under_Threshold()
    {
        // 显式离题词 (+1) 但实体重叠 (-2): "顺便问一下 redis 持久化" → 净分 -1 → 不隔离
        var goal = new List<string> { "redis", "缓存" };
        var (isolated, score, reason) = agent.intent.TaskRelevanceChecker.Check(goal, "coding", "顺便问一下 redis 持久化怎么配", "config");
        Assert.False(isolated);
    }

    [Fact]
    public void Long_MultiEntity_OffTopic_Isolates()
    {
        // 长离题消息多实体零重叠 + 意图不同 + 离题词 → 净分 3 ≥ 2 → 隔离
        var goal = new List<string> { "redis", "缓存优化", "热点key" };
        var (isolated, score, reason) = agent.intent.TaskRelevanceChecker.Check(goal, "coding",
            "另外帮我查一下附近有什么好吃的火锅店推荐", "search");
        Assert.True(isolated);
        Assert.True(score >= 2);
    }

    [Fact]
    public void Threshold_Parameter_Is_Honored()
    {
        // R149 阈值参数化语义: 实体重叠=-2 分压过意图差, 得分 -1 → 任何阈值 ≥0 都不隔离;
        // 零重叠消息 (今天几号) = 2+1=3 分 → 默认阈值 2 已隔离 (阈值再降到 1 不改变结果, 只影响 1 分边界)。
        var goal = new List<string> { "redis", "缓存" };
        var (isolatedOverlap, scoreOverlap, _) = agent.intent.TaskRelevanceChecker.Check(goal, "coding", "redis 持久化配置", "config");
        Assert.False(isolatedOverlap);
        var (_, scoreZero, _) = agent.intent.TaskRelevanceChecker.Check(goal, "coding", "今天几号", "search");
        Assert.True(scoreZero >= 2);
        // threshold=1: 意图差 1 分即隔离 — 需零重叠以外信号为 0 的输入难构造, 用空 goal (实体路径 0 分):
        var (isolatedEmpty, scoreEmpty, _) = agent.intent.TaskRelevanceChecker.Check(new List<string>(), "coding", "附近有什么好吃的火锅店", "search", threshold: 1);
        Assert.True(isolatedEmpty);
        Assert.True(scoreEmpty >= 1);
    }
}
