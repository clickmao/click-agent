using agent.intent;
using agent.intent;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// R308 — 合并判定 API 单测 (TopicRelevanceEvaluator):
/// 隔离/牵引/正常三态 + 指代词一票否决 + 阈值与 TaskRelevanceChecker 同源。
/// </summary>
public class TopicRelevanceEvaluatorTests
{
    private static readonly string[] GoalEntities = { "WebAPI", "Python", "爬虫" };

    [Fact]
    public void Unrelated_Task_Triggers_Isolate()
    {
        // 无关新任务: 实体零重叠 + 无指代 (会话核心 = WebAPI 开发):
        var v = TopicRelevanceEvaluator.Evaluate(
            "帮我写一个红烧肉的菜谱", GoalEntities, "code_generation",
            "general", "Web API");
        Assert.True(v.Score >= 2, $"score={v.Score} signals=[{string.Join(",", v.Signals)}]");
        Assert.Equal(TopicRelevanceEvaluator.Recommendation.Isolate, v.Action);
        Assert.True(v.IsIsolated);
    }

    [Fact]
    public void Mild_Drift_Triggers_SteerHint()
    {
        // 偏题但非新任务 (一般问答, 实体重叠弱): 介于隔离与正常之间 → SteerHint
        var v = TopicRelevanceEvaluator.Evaluate(
            "红烧肉怎么做?", GoalEntities, "code_generation",
            "general", "Web API");
        Assert.Equal(TopicRelevanceEvaluator.Recommendation.SteerHint, v.Action);
        Assert.True(v.IsDrift);
        Assert.False(v.IsIsolated);
        Assert.Equal("Web API", v.CoreTopic);
    }

    [Fact]
    public void Related_Input_Is_Normal()
    {
        // 相关输入 (实体重叠): Normal
        var v = TopicRelevanceEvaluator.Evaluate(
            "继续 Web API 项目的接口设计", GoalEntities, "code_generation",
            "code_generation", "Web API");
        Assert.Equal(TopicRelevanceEvaluator.Recommendation.Normal, v.Action);
        Assert.False(v.IsDrift);
    }

    [Fact]
    public void Deixis_Followup_Is_Normal_Not_Isolated()
    {
        // 指代词一票否决: "刚才那个怎么优化" 依赖上文 → Normal (不是隔离也不是牵引)
        var v = TopicRelevanceEvaluator.Evaluate(
            "刚才那个怎么优化?", GoalEntities, "code_generation",
            "code_generation", "Web API");
        Assert.Equal(TopicRelevanceEvaluator.Recommendation.Normal, v.Action);
        Assert.Contains(v.Signals, s => s.Contains("指代") || s.Contains("依赖上文") || s.Contains("实现询问"));
    }

    [Fact]
    public void Threshold_Matches_TaskRelevanceChecker()
    {
        Assert.Equal(TaskRelevanceChecker.DefaultIsolationThreshold, 2);
    }
}
