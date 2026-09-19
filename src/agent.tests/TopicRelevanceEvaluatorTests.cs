using agent.intent;
using Xunit;
namespace agent.tests;

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
        // 无关新任务: 实体零重叠 + 无指代 (会话核心 = WebAPI 开发) ⇒ 隔离。
        // 注 (2026-09-19): 短消息 (< EvidenceTokenFloor) 一律不下离题结论 (证据不足 ⇒ 不隔离),
        // 故本用例须用**证据充分**的长句表达"无关新任务"; 旧短句 "帮我写一个红烧肉的菜谱" 与
        // 指代短句在 token 口径上不可分, 已按现有机制让位于 fail-safe 方向。
        var v = TopicRelevanceEvaluator.Evaluate(
            "帮我写一个红烧肉的菜谱，要包含用料清单、火候步骤、常见失败点和补救办法", GoalEntities, "code_generation",
            "general", "Web API");
        Assert.True(v.Score >= 2, $"score={v.Score} signals=[{string.Join(",", v.Signals)}]");
        Assert.Equal(TopicRelevanceEvaluator.Recommendation.Isolate, v.Action);
        Assert.True(v.IsIsolated);
    }

    [Fact]
    public void Mild_Drift_Triggers_SteerHint()
    {
        // 偏题但非新任务: **有实体重叠** (Python/爬虫, 不隔离) + 已离开会话核心 (无 "Web API")
        // ⇒ SteerHint。词表移除后 (2026-09-19): 牵引带只能由"重叠但偏核心"构成 —
        // 零重叠的短句一律落「证据不足」⇒ Normal (旧用例 "红烧肉怎么做?" 依赖已删词表把零重叠短句留在牵引带)。
        var v = TopicRelevanceEvaluator.Evaluate(
            "Python 的异步爬虫性能优化和并发控制应该怎么设计比较好", GoalEntities, "code_generation",
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
        // 指代/依赖上文的短句 ⇒ Normal。词表移除后 (2026-09-19): 依据由「证据充分性」闸给出
        // (短消息 token < EvidenceTokenFloor ⇒ 不下结论, 既不隔离也不牵引), 理由文本不带词表词面。
        var v = TopicRelevanceEvaluator.Evaluate(
            "刚才那个怎么优化?", GoalEntities, "code_generation",
            "code_generation", "Web API");
        Assert.Equal(TopicRelevanceEvaluator.Recommendation.Normal, v.Action);
        Assert.Contains(v.Signals, s => s.Contains("证据不足"));
    }

    [Fact]
    public void Threshold_Matches_TaskRelevanceChecker()
    {
        Assert.Equal(TaskRelevanceChecker.DefaultIsolationThreshold, 2);
    }
}
