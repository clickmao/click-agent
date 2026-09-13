// v0.22.0 exp9 D4b 机检: 出站扣减 (子请求级"谁来做"的闭环)。
//
// 断言原则 (对齐用户审计口径): 每条断言绑定**组件真实行为**, 不用"看着像"的弱断言。
//  - 判定正向: 整段子请求=原文上的文本处理 ⇒ Local + IsLocalizedRequest=true (ZERO token 的前提)
//  - 判定负向: 含代码产物标记 / 有依赖 / 过长 ⇒ 必须**不**标 (负向控制: 不许乐观扣减)
//  - 去重正向: 拆解节点已本地承接时, 不再追加第二份 dep-free text.process 节点 (R382 重复计算的根)
//  - 扣减正向: 片段 + 左邻连接词 + 边界字符一起删; 删后正文 = 原文 − 删除字数 (字节级可对账)
//  - 扣减负向: 定位不到 / 多处出现 / 剩余比例不足 ⇒ 一律返回**逐字原文** + 真实原因 (绝不改坏用户原话)
//  - 渲染正向: 成功给结论, 失败给真实原因 (不静默) —— 扣掉的请求必须出现在回复里
using System;
using System.Collections.Generic;
using System.Linq;
using agent.intent;
using Xunit;

namespace agentframework.tests;

public class PlanAblationTests
{
    // R382 真机同一提示词 (逐字): 该轮模型自己算了 118 字符, 框架确定性统计 117 ⇒ 重复计算。
    private const string R382Prompt =
        "用 Python 开发一个贪吃蛇小游戏(终端, 单文件 snake.py): 逻辑与渲染分离; " +
        "无头自测 python3 snake.py --selftest 覆盖 移动/吃食物加分/撞墙判负/计分; " +
        "并且统计我这段需求描述的字数。";

    // ── 判定层: IsPureSourceTextOp ───────────────────────────────────────────

    [Theory]
    [InlineData("且统计我这段需求描述的字数", 0)]          // R382 真机片段 (逐字)
    [InlineData("统计我这段需求描述的字数", 0)]
    [InlineData("帮我统计一下原文的字符数", 0)]
    [InlineData("顺便汇总我写的内容", 0)]
    public void 纯原文文本处理_四条件全中为真(string text, int deps)
    {
        Assert.True(LocalVerifyNodePlanner.IsPureSourceTextOp(text, deps));
    }

    [Theory]
    [InlineData("用 Python 开发一个贪吃蛇小游戏(单文件 snake.py)", 0)]  // 产物型 → 不许判"纯文本处理"
    [InlineData("写个脚本统计我这段需求描述的字数", 0)]                  // 产物型 (脚本)
    [InlineData("统计我这段需求描述的字数", 1)]                          // 有依赖 → 输入不是原文
    [InlineData("统计这个项目有多少行代码", 0)]                          // 无"原文"对象词 → 不是处理用户原文
    [InlineData("", 0)]
    [InlineData(null, 0)]
    public void 纯原文文本处理_缺一即否(string? text, int deps)
    {
        Assert.False(LocalVerifyNodePlanner.IsPureSourceTextOp(text, deps));
    }

    [Fact]
    public void 纯原文文本处理_过长即否()
    {
        // 长片段里裹着别的诉求 ⇒ 整段扣减会连带删掉别的需求, 必须落回远程
        var longClause = "并且统计我这段需求描述的字数" + new string('好', 60);
        Assert.False(LocalVerifyNodePlanner.IsPureSourceTextOp(longClause, 0));
    }

    [Fact]
    public void 路由_R382真机提示词_原文文本处理子请求判Local且不再追加第二份本地节点()
    {
        var subTasks = IntentDecomposer.Decompose(R382Prompt);
        var plan = RoutedPlanBuilder.Build(R382Prompt, subTasks);

        // ① 恰好一个"原文级本地子请求"节点, 且是 Local
        var localized = plan.Nodes.Where(n => n.IsLocalizedRequest).ToList();
        Assert.Single(localized);
        Assert.Equal(NodeExecutionLocation.Local, localized[0].Location);
        Assert.Equal(LocalExecutorRegistry.TextProcess, localized[0].LocalExecutorId);
        Assert.Contains("统计", localized[0].Text, StringComparison.Ordinal);

        // ② D4b 去重: dep-free 的 text.process 节点**只有这一份** (R382 是"拆解节点 + 追加节点"两份)
        var depFreeTextNodes = plan.Nodes.Count(n =>
            n.LocalExecutorId == LocalExecutorRegistry.TextProcess && n.DependsOn.Count == 0);
        Assert.Equal(1, depFreeTextNodes);

        // ③ 仍有远程节点承担"写贪吃蛇" ⇒ 扣减闸门 (SubtractForPlan) 才会放行
        Assert.Contains(plan.Nodes, n => n.Location == NodeExecutionLocation.Remote);

        // ④ 扣减闸门放行, 且出站正文里不再有该子请求
        var ab = RequestAblation.SubtractForPlan(R382Prompt, plan.Nodes);
        Assert.True(ab.Applied, ab.AbortReason);
        Assert.DoesNotContain("统计我这段需求描述的字数", ab.Text, StringComparison.Ordinal);
        Assert.Contains("撞墙判负/计分", ab.Text, StringComparison.Ordinal);
    }

    // ── 扣减层: 片段定位 + 连接词/边界吸收 ────────────────────────────────────

    [Fact]
    public void 扣减_片段与左邻连接词边界一并删除_字数可对账()
    {
        var ab = RequestAblation.Subtract(R382Prompt, ["且统计我这段需求描述的字数"]);

        Assert.True(ab.Applied, ab.AbortReason);
        Assert.Single(ab.RemovedClauses);
        Assert.Equal(R382Prompt.Length - ab.Text.Length, ab.RemovedChars);
        Assert.True(ab.RemovedChars > "且统计我这段需求描述的字数".Length,
            "连接词/边界字符应一并删除 (否则留下孤立的 '并' 与 '; ')");
        Assert.DoesNotContain("统计", ab.Text, StringComparison.Ordinal);
        Assert.DoesNotContain("并且", ab.Text, StringComparison.Ordinal);
        Assert.StartsWith("用 Python 开发一个贪吃蛇小游戏", ab.Text, StringComparison.Ordinal);
    }

    [Fact]
    public void 扣减_多片段相邻_合并删除_不留下孤立连接词()
    {
        const string src = "用 python 写一个处理数据的小工具; 并且统计我这段需求描述的字数; 另外汇总我写的内容。";
        var ab = RequestAblation.Subtract(src, ["且统计我这段需求描述的字数", "汇总我写的内容"]);

        Assert.True(ab.Applied, ab.AbortReason);
        Assert.Equal(2, ab.RemovedClauses.Count);
        Assert.Equal(src.Length - ab.Text.Length, ab.RemovedChars);
        Assert.Equal("用 python 写一个处理数据的小工具", ab.Text.Trim());   // 两段本地子请求 + 其间连接词/标点全清
        Assert.DoesNotContain("并且", ab.Text, StringComparison.Ordinal);
        Assert.DoesNotContain("另外", ab.Text, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("这段原话不存在于原文")]                       // 定位失败
    [InlineData("")]
    public void 扣减_定位失败_逐字返回原文并给原因(string clause)
    {
        var ab = RequestAblation.Subtract(R382Prompt, [clause]);

        Assert.False(ab.Applied);
        Assert.Equal(R382Prompt, ab.Text);
        Assert.Equal(0, ab.RemovedChars);
        Assert.NotNull(ab.AbortReason);
    }

    [Fact]
    public void 扣减_片段出现多次_不确定删哪处_不扣()
    {
        const string src = "统计我这段需求描述的字数; 再统计我这段需求描述的字数";
        var ab = RequestAblation.Subtract(src, ["统计我这段需求描述的字数"]);

        Assert.False(ab.Applied);
        Assert.Equal(src, ab.Text);
        Assert.Contains("多次", ab.AbortReason!, StringComparison.Ordinal);
    }

    [Fact]
    public void 扣减_扣完只剩空壳_不扣()
    {
        const string src = "统计我这段需求描述的字数";
        var ab = RequestAblation.Subtract(src, ["统计我这段需求描述的字数"]);

        Assert.False(ab.Applied);
        Assert.Equal(src, ab.Text);
        Assert.NotNull(ab.AbortReason);
    }

    [Fact]
    public void 扣减_无子请求_逐字返回()
    {
        var ab = RequestAblation.Subtract(R382Prompt, Array.Empty<string>());
        Assert.False(ab.Applied);
        Assert.Equal(R382Prompt, ab.Text);
    }

    // ── 闸门层: 本地独占回合不实现, 就不许扣 ──────────────────────────────────

    [Fact]
    public void 闸门_全部节点均本地_不扣减_理由点名D4c边界()
    {
        var allLocal = new List<PlanNode>
        {
            new() { Text = "统计我这段需求描述的字数", Location = NodeExecutionLocation.Local, IsLocalizedRequest = true },
        };
        var ab = RequestAblation.SubtractForPlan("统计我这段需求描述的字数", allLocal);

        Assert.False(ab.Applied);
        Assert.Equal("统计我这段需求描述的字数", ab.Text);
        Assert.Contains("本地独占回合", ab.AbortReason!, StringComparison.Ordinal);
    }

    [Fact]
    public void 闸门_无本地子请求_不扣减()
    {
        var remoteOnly = new List<PlanNode>
        {
            new() { Text = "用 Python 开发贪吃蛇", Location = NodeExecutionLocation.Remote },
        };
        var ab = RequestAblation.SubtractForPlan(R382Prompt, remoteOnly);
        Assert.False(ab.Applied);
        Assert.Equal(R382Prompt, ab.Text);
    }

    // ── 渲染层: 扣掉的请求必须出现在回复里 (成功给结论 / 失败给原因) ──────────

    [Fact]
    public void 渲染_成功与失败都出现_失败不静默()
    {
        var items = new List<LocalAnswerItem>
        {
            new("且统计我这段需求描述的字数", "本地统计: 字符=117 行=1 中文=13 词≈2 指纹=deadbeef", true),
            new("汇总我写的内容", "无可用输入 ⇒ 本地处理无对象", false),
        };
        var s = PlanLocalAnswer.Render(items);

        Assert.Contains("[框架本地执行 (零 token)]", s, StringComparison.Ordinal);
        Assert.Contains("字符=117", s, StringComparison.Ordinal);
        Assert.Contains("本地执行未成功", s, StringComparison.Ordinal);
        Assert.Contains("无可用输入", s, StringComparison.Ordinal);
    }

    [Fact]
    public void 渲染_空列表或空请求_返回空串()
    {
        Assert.Equal(string.Empty, PlanLocalAnswer.Render(Array.Empty<LocalAnswerItem>()));
        Assert.Equal(string.Empty, PlanLocalAnswer.Render([new LocalAnswerItem("  ", "x", true)]));
    }

    // ── 主链契约: 出站正文替换点未生效时逐字等于原路径 ────────────────────────

    [Fact]
    public void 未扣减时_出站正文逐字等于原文_零改动()
    {
        // 主链取用规则: `_planAblation is { Applied: true } ? _planAblation.Text : message.Content`
        // 这条断言的语义载体 = 未扣减分支必须拿到**同一个字符串**(不是重算/归一过的)
        var ab = RequestAblation.Subtract(R382Prompt, ["不存在的片段"]);
        var outbound = ab is { Applied: true } ? ab.Text : R382Prompt;

        Assert.Equal(R382Prompt, outbound);
    }
}
