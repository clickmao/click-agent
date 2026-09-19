using agent.roles;
using Xunit;

namespace agent.tests;

/// <summary>R361 (对抗用例固话): 纠正检测器 — L1 规则/语境豁免 + L2 协议 (mock caller, 不调真 LLM)。</summary>
public class CorrectionDetectorTests
{
    private static CorrectionDetector.CorrectionVerdict? Rule(string user)
        => CorrectionDetector.RuleJudge(user, "上一轮回复");

    // ── 判罚正例 (L1 → 交 L2; 2026-09-19 词表移除后 L1 不再判罚) ──
    [Theory]
    [InlineData("不对，应该先 stop 再 rm")]
    [InlineData("错了，-v 要用绝对路径")]
    [InlineData("你理解错了，我说的是上游仓库")]
    [InlineData("Not what i meant, use rebase")]
    public void L1_纠正正例_交L2判官(string user)
        // 无词表 ⇒ L1 一律返回 null (模糊), 判罚由 L2 字母判官 (C/A/N) 承担 —— 见 L2_* 用例。
        => Assert.Null(Rule(user));

    // ── 判赏正例 (L1 → 交 L2) ──
    [Theory]
    [InlineData("好的，明白了")]
    [InlineData("没错，就是要这个效果")]
    [InlineData("Got it, thanks")]
    public void L1_采纳正例_交L2判官(string user)
        => Assert.Null(Rule(user));

    // ── 误杀陷阱 (对抗实证: 首轮 L1 错 3 例, 语境豁免后转 Neutral/进 L2) ──
    [Theory]
    [InlineData("同事说这个方案不对，你觉得呢")]     // 转述他人
    [InlineData("如果我说错了请纠正我：这个参数是必须的吗")] // 假设句
    [InlineData("上次那个方案错了所以被否了，这次的呢")]     // 历史对照
    public void L1_语境豁免_不误判罚(string user)
    {
        var v = Rule(user);
        Assert.True(v is null || v.Kind != CorrectionDetector.CorrectionKind.Correct,
            $"误杀: {user}");
    }

    // ── 求证句: L1 不再自行裁决 (词表已删) ⇒ 交 L2, 绝不误判罚 ✓ ──
    [Fact]
    public void L1_求证句_不判罚()
        => Assert.Null(Rule("这个配置是对的吧？我有点不确定"));

    // ── L2 协议 (mock: 单字母/全词/空 content 重试语义) ──
    [Fact]
    public async Task L2_单字母C_判Correct()
    {
        var v = await CorrectionDetector.JudgeAsync("继续的参数要怎么填", "先初始化再配置",
            (_, _) => Task.FromResult(("C", 100)));
        Assert.Equal(CorrectionDetector.CorrectionKind.Correct, v.Kind);
        Assert.Equal(100, v.TokensUsed);
    }

    [Fact]
    public async Task L2_空content_重试后判Adopt()
    {
        var calls = 0;
        var v = await CorrectionDetector.JudgeAsync("继续下一步的参数怎么填", "直接改即可", (_, max) =>
        {
            calls++;
            return Task.FromResult(calls == 1 ? ("", 64) : ("A", 128)); // 首次空 (reasoning 吃预算) → 重试
        });
        Assert.Equal(CorrectionDetector.CorrectionKind.Adopt, v.Kind);
        Assert.Equal(2, calls);          // 重试发生
        Assert.Equal(192, v.TokensUsed); // 两次累计
    }

    [Fact]
    public async Task L2_全N_判Neutral()
    {
        var v = await CorrectionDetector.JudgeAsync("顺便问下天气", "已重启服务", (_, _) => Task.FromResult(("N", 50)));
        Assert.Equal(CorrectionDetector.CorrectionKind.Neutral, v.Kind);
    }

    [Fact]
    public async Task L2_LLM异常_回退Neutral不抛()
    {
        var v = await CorrectionDetector.JudgeAsync("帮我看看这个报错", "这是权限问题",
            (_, _) => throw new IOException("网络断"));
        Assert.Equal(CorrectionDetector.CorrectionKind.Neutral, v.Kind);
    }

    // ── 空消息 ──
    [Fact]
    public void 空消息_Neutral()
        => Assert.Equal(CorrectionDetector.CorrectionKind.Neutral, Rule("")!.Kind);
}
