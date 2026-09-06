using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.11.0 R39b/R39c: 隔离判定修复 — ascii 连写 4-gram 交叉匹配 + 实现询问一票否决。
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
}
