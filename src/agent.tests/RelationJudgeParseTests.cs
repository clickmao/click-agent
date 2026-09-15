using System;
using System.IO;
using System.Linq;
using agent.modelqueue;
using agent.roles;
using Xunit;

namespace agent.tests;

/// <summary>
/// R435 单组件回归 —— J 判官（关系判官）本地可解析性 + prompt 形状。
///
/// 真机根因（raw 取证, 本轮跑出）: `eval/rover/r435/probe-j1-raw.json`
///   7 条实发 prompt 喂给 r1 ⇒ **1/7** 可解析（与产品 BRJ 臂 remote_fallback 6/7 逐位吻合 ⇒ 器具互证）。
///   6 条失败的确定形态:
///     ① 结论区**逐字回声**尾行片段「只输出一个字母。」（3/7: turn3/6/7）⇒ 无任何字母 ⇒ no_marker;
///     ② 思考链吃光 512 token（2/7: turn5/8, pred=512 ∧ stop=limit ∧ 无 </think> 闭合）⇒ thinking_truncated;
///     ③ 结论区是别的词（1/7: turn1 结论区 = `'build'`）⇒ no_marker。
///   断言 = **机器不变量**（形状/边界/负控），不是「跑一次看是不是绿」。
/// </summary>
public sealed class RelationJudgeParseTests
{
    private const string ThinkOpen = "<think>";
    private const string ThinkClose = "</think>";

    // ── 正例: 结论区散文 + 分类词（R435 raw turn9 逐字形态） ──
    [Fact]
    public void K1_结论区散文含判定词_可解析为字母()
    {
        var raw = ThinkOpen + "让我想想，用户说从头再说。" + ThinkClose +
                  "\n根据指示，判定用户消息相对上一轮回答：“从头再说。”这表明用户希望重新规划，因此应判定为N。\n\n\\boxed{N}";
        Assert.True(RelationLetterJudge.TryNormalize(raw, out var letter, out var reason));
        Assert.Equal("N", letter);
        Assert.Equal("ok", reason);
    }

    // ── R435 撤回记录（词表兜底被既有预注册判据否决） ──
    // 曾实现「结论区中文分类词 ⇒ 定字母」，被 RelationJudgeLocalizationTests.J13 否决:
    //   契约 = 结论区必须含**独立字母**; 「这是采纳」这类散文必须未判定（交远端）。
    // 且四臂实测词表零增益 ⇒ 撤回。本 Theory 由「词表命中」改为「散文一律未判定」的负控。
    [Theory]
    [InlineData("因此应判定为：认可采纳。")]
    [InlineData("这属于认可，用户接受了上一轮。")]
    [InlineData("用户在纠正上一轮的结论。")]
    [InlineData("这是否定上一轮的说法。")]
    [InlineData("该消息与上一轮无关。")]
    [InlineData("这是新话题。")]
    public void K2_负控_散文分类词无独立字母_必须未判定(string conclusion)
    {
        var raw = ThinkOpen + "推理正文" + ThinkClose + "\n" + conclusion;
        Assert.False(RelationLetterJudge.TryNormalize(raw, out var letter, out var reason));
        Assert.Equal(string.Empty, letter);
        Assert.Equal("no_marker", reason);
    }

    // ── 负控 1 (R435 根因本体): 结论区是尾行片段的**逐字回声** ⇒ 必须判失败, 不许当作判定 ──
    [Fact]
    public void K3_负控_结论区回声指令片段_必须失败()
    {
        var raw = ThinkOpen + "好，我现在要解决这个问题。" + ThinkClose + "\n\n只输出一个字母。";
        Assert.False(RelationLetterJudge.TryNormalize(raw, out var letter, out var reason));
        Assert.Equal("", letter);
        Assert.Equal("no_marker", reason);
    }

    // ── 负控 2: 推理正文里的字母不得胜出（Parse 铁律: 结论只认思考块之后） ──
    [Fact]
    public void K4_负控_只在思考链正文出现字母_必须失败()
    {
        var raw = ThinkOpen + "如果认可就是 A，如果纠正就是 C，如果无关就是 N。所以应该是 A。" + ThinkClose +
                  "\n\n根据以上分析，我的判断写在上面。";
        Assert.False(RelationLetterJudge.TryNormalize(raw, out var letter, out var reason));
        Assert.Equal("", letter);
        Assert.Equal("no_marker", reason);
    }

    // ── 负控 3: 有开无闭 = 被 max_tokens 截断 ⇒ thinking_truncated（预算不足的确定形态） ──
    [Fact]
    public void K5_负控_有开无闭_归因thinking_truncated()
    {
        var raw = ThinkOpen + "让我想想…";
        Assert.False(RelationLetterJudge.TryNormalize(raw, out _, out var reason));
        Assert.Equal("thinking_truncated", reason);
    }

    // ── 负控 4: 空/空白 ⇒ empty ──
    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   \n ")]
    public void K6_负控_空输入归因empty(string? raw)
    {
        Assert.False(RelationLetterJudge.TryNormalize(raw, out _, out var reason));
        Assert.Equal("empty", reason);
    }

    // ── 位置裁定: 字母与分类词并存 ⇒ 最后出现者胜出（与 TurnGateJudge.Parse 同规则） ──
    [Fact]
    public void K7_并列_最后出现者胜出()
    {
        // 契约 = 只认独立字母，取**最后**一个（与 J12「所以用户是采纳，应输出 A。」同规则）。
        // R435 撤回: 原先这里还断言「分类词在后也胜出」，随词表一起撤销（J13 否决散文兜底）。
        var b = ThinkOpen + "x" + ThinkClose + "\n这属于认可。\n最终答案: C";
        Assert.True(RelationLetterJudge.TryNormalize(b, out var l2, out _));
        Assert.Equal("C", l2);   // 字母在后

        var a = ThinkOpen + "x" + ThinkClose + "\n答案是 C。\n再确认一次: A";
        Assert.True(RelationLetterJudge.TryNormalize(a, out var l1, out _));
        Assert.Equal("A", l1);   // 后者胜出
    }

    // ── 无思考块 ⇒ 只看尾部 64 字符（防从长正文里取字母） ──
    [Fact]
    public void K8_无思考块_只看尾部64字符()
    {
        // 字母在**正文前部**（离尾部 64 字符之外）⇒ 必须判失败；只有尾部窗口内的标记才算结论。
        var raw = " A " + new string('字', 200) + new string('补', 10);
        Assert.Equal(213, raw.Length);
        Assert.False(RelationLetterJudge.TryNormalize(raw, out _, out var reason));
        Assert.Equal("no_marker", reason);

        // 同一字母落进尾部窗口内 ⇒ 必须可解析（证明窗口是唯一分界, 不是整体失效）。
        var near = new string('字', 200) + " A ";
        Assert.True(RelationLetterJudge.TryNormalize(near, out var l, out _));
        Assert.Equal("A", l);
    }

    // ── prompt 形状 (R435 承重修正本体): 尾行不再是裸片段, 且带「答案:」答案位 ──
    [Fact]
    public void K9_prompt形状_尾行是答案位而非裸指令片段()
    {
        var p = CorrectionDetector.BuildJudgePrompt("再讲一遍。", "收到，继续按当前方向推进，本轮不重新规划。");
        Assert.EndsWith("答案:\n", p);
        Assert.DoesNotContain("只输出一个字母。", p);
        Assert.Contains("无法确定时也必须写 N。", p);
        Assert.Contains("用户: 再讲一遍。", p);
        Assert.Contains("上一轮: 收到，继续按当前方向推进，本轮不重新规划。", p);
    }

    [Fact]
    public void K10_prompt截断_用户120字上一轮160字()
    {
        var p = CorrectionDetector.BuildJudgePrompt(new string('用', 200), new string('回', 300));
        Assert.Contains("用户: " + new string('用', 120), p);
        Assert.Contains("上一轮: " + new string('回', 160), p);
        Assert.DoesNotContain(new string('用', 121), p);
        Assert.DoesNotContain(new string('回', 161), p);
    }

    // ── R435: prompt 金标准落盘（探针与产品**同一文本**, 消除双份实现漂移）
    //    仅当 AGENTFRAMEWORK_R435_DUMP=<path> 时写盘；否则 0 成本跳过。
    [Fact]
    public void K11_prompt金标准落盘_探针同源()
    {
        var path = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R435_DUMP");
        if (string.IsNullOrEmpty(path)) return;
        var cases = new (string Prev, string User, string Name)[]
        {
            ("", "把构建命令写成一行。", "turn1"),
            ("收到，继续按当前方向推进，本轮不重新规划。", "再讲一遍。", "turn3"),
            ("桩应答: 收到, 已完成该步。", "讲细一点。", "turn5"),
            ("桩应答: 收到, 已完成该步。", "嗯嗯，知道了。", "turn6"),
            ("收到，继续按当前方向推进，本轮不重新规划。", "换个说法。", "turn7"),
            ("桩应答: 收到, 已完成该步。", "明白，多谢。", "turn8"),
            ("收到，继续按当前方向推进，本轮不重新规划。", "从头再说。", "turn9"),
            ("已把前置门接进链里，跳过轮的 token 已降下来。", "嗯，好像不太对。", "syn-c"),
            ("已把前置门接进链里，跳过轮的 token 已降下来。", "嗯，这个方向没问题。", "syn-a"),
        };
        var lines = cases.Select(c =>
            System.Text.Json.JsonSerializer.Serialize(new
            {
                @case = c.Name, prev = c.Prev, user = c.User,
                prev_len = c.Prev.Length, user_len = c.User.Length,
                prompt = CorrectionDetector.BuildJudgePrompt(c.User, c.Prev),
            }));
        File.WriteAllLines(path, lines);
        Assert.True(File.Exists(path));
        Assert.Equal(cases.Length, File.ReadAllLines(path).Length);
    }

    // ── R446: 判官 prompt 紧凑变体 (消融用; 截断口径必须与 verbose 逐字一致) ──
    [Fact]
    public void K14_紧凑prompt_形状与截断口径一致且更短()
    {
        var u = new string('用', 200);
        var p = new string('回', 300);
        var c = CorrectionDetector.BuildJudgePromptCompact(u, p);
        var v = CorrectionDetector.BuildJudgePrompt(u, p); // 默认 (无开关) = verbose

        Assert.EndsWith("答案:\n", c);
        Assert.Contains("无法确定时也必须写 N。", c);
        Assert.Contains("用户: " + new string('用', 120), c);
        Assert.Contains("上一轮: " + new string('回', 160), c);
        Assert.DoesNotContain(new string('用', 121), c);
        Assert.DoesNotContain(new string('回', 161), c);

        Assert.True(c.Length < v.Length, $"紧凑变体未变短: {c.Length} vs {v.Length}");
        // 尾部两行 (上一轮/用户/答案) 必须逐字同源 ⇒ 消融只改指令块
        Assert.Equal(v[v.IndexOf("上一轮: ", StringComparison.Ordinal)..], c[c.IndexOf("上一轮: ", StringComparison.Ordinal)..]);
    }
}
