using agent.exploration;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.13.3 B2 — 微步骤会话单测 (回注预算/失败升级联动/结果轨迹)。
/// 微问题执行器 = 隔离 subagent (宿主侧, A5 语义), 本类只管编排语义。
/// </summary>
public class MicroStepSessionTests
{
    private static MicroStepResult Ok(string id, string answer, int tokens = 100) =>
        new() { MicroId = id, Ok = true, Answer = answer, TokensUsed = tokens };

    [Fact]
    public void Restore_Summary_Truncated_To_Budget()
    {
        // 用户钦定: 回注 ≤200 tok/条 (400 chars), 防止微结果反撑爆主上下文:
        var s = new MicroStepSession();
        var longAnswer = new string('x', 1000);
        var summary = s.BuildRestoreSummary(Ok("mq1", longAnswer));
        Assert.True(summary.Length <= 200 * 2 + 10, $"summary len={summary.Length}");
        Assert.Contains("[mq1]", summary);
    }

    [Fact]
    public void Restore_Summary_Empty_For_Empty_Answer()
    {
        var s = new MicroStepSession();
        Assert.Equal(string.Empty, s.BuildRestoreSummary(Ok("mq1", "")));
    }

    [Fact]
    public void ConsecutiveFailures_Counts_And_Resets()
    {
        var s = new MicroStepSession();
        s.Record(new MicroStepResult { MicroId = "a", Ok = false });
        s.Record(new MicroStepResult { MicroId = "b", Ok = false });
        Assert.Equal(2, s.ConsecutiveFailures); // FailureEscalation 联动点 (v0.13.2 §四)
        s.Record(Ok("c", "ok"));
        Assert.Equal(0, s.ConsecutiveFailures);
        Assert.Equal(3, s.Results.Count);
    }

    [Fact]
    public void Short_Answer_Passes_Through_Intact()
    {
        var s = new MicroStepSession();
        var summary = s.BuildRestoreSummary(Ok("mq9", "答案很短"));
        Assert.Equal("[mq9] 答案很短", summary);
    }
}
