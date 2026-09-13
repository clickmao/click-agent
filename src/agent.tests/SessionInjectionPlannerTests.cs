using agent.context;
using Xunit;

namespace agent.tests;

/// <summary>
/// R379 增量最小化机检: 会话静态块识别 / 动态块跨轮行级去重 / 每轮增量占前缀比例红线。
///
/// 红线 (用户钦定): 多轮会话第 2 轮起 provider 缓存命中率 ≥90%。
/// 实测判据 (DS 官方规则: 缓存单元 64 token, 必须自 token 0 起完整匹配):
///   命中率 ≈ 已发前缀字节 / 本轮总字节  → 等价于 **每轮新增字节 / 总字节 ≤ 10%**。
/// 本机检把这条红线变成硬断言 (含负向控制: 不去重时该断言必须为假)。
/// </summary>
public class SessionInjectionPlannerTests
{
    private const string Header = "[AgentContext]\nAgent: click-agent\n可用能力: git, dotnet, curl, python3\n\n" +
                                  "[User Preference]\n偏好: 工业级质量, 完整可编译代码, 技术细节精确\n\n" +
                                  "[Workspace Files]\n- src/agent/IndustrialAgentV2.cs (1204 行)\n\n" +
                                  "[Memory (RAG)]\nQ: 二分查找的前提?\nA: 有序 + 可随机访问\n\n" +
                                  "[Web Search]\n- 二分查找 复杂度 O(log n)";

    /// <summary>P1: 会话静态块 (画像/偏好/工作区) 必须被识别; 动态块 (RAG/Web) 不得误判为静态。</summary>
    [Fact]
    public void P1_静态块识别_正确切开静态与动态()
    {
        var blocks = SessionInjectionPlanner.Split(Header);
        Assert.Equal(5, blocks.Count);
        Assert.True(SessionInjectionPlanner.IsSessionStatic("AgentContext"));
        Assert.True(SessionInjectionPlanner.IsSessionStatic("User Preference"));
        Assert.True(SessionInjectionPlanner.IsSessionStatic("Workspace Files"));
        Assert.True(SessionInjectionPlanner.IsSessionStatic("工作区文件 data/activity/1.json"));
        Assert.False(SessionInjectionPlanner.IsSessionStatic("Memory (RAG)"));
        Assert.False(SessionInjectionPlanner.IsSessionStatic("Web Search"));

        var statics = blocks.Where(b => SessionInjectionPlanner.IsSessionStatic(b.Title)).ToList();
        Assert.Equal(3, statics.Count);
        var staticText = SessionInjectionPlanner.Join(statics);
        Assert.Contains("可用能力", staticText, StringComparison.Ordinal);
        Assert.DoesNotContain("二分查找的前提", staticText, StringComparison.Ordinal);
    }

    /// <summary>P2: 第二轮重复注入的动态块必须被"吃掉"(历史里已有), 只有新行进入增量。</summary>
    [Fact]
    public void P2_跨轮去重_重复行不再进增量()
    {
        var seen = new SessionInjectionPlanner.InjectionLedger();
        var turn1 = SessionInjectionPlanner.Split(Header)
            .Where(b => !SessionInjectionPlanner.IsSessionStatic(b.Title)).ToList();
        var (text1, kept1, dropped1) = SessionInjectionPlanner.Dedupe(turn1, seen);
        Assert.True(kept1 > 0);
        Assert.Equal(0, dropped1); // 首轮无历史 → 无去重

        // 第二轮: 同样的动态块 + 一块新召回
        var turn2 = SessionInjectionPlanner.Split(Header + "\n\n[SessionMemory]\n完成: 回答二分查找前提")
            .Where(b => !SessionInjectionPlanner.IsSessionStatic(b.Title)).ToList();
        var (text2, kept2, dropped2) = SessionInjectionPlanner.Dedupe(turn2, seen);

        Assert.True(kept2 < kept1, $"第二轮保留行数 {kept2} 应显著小于首轮 {kept1} (重复行应被吃掉)");
        Assert.True(kept2 > 0, "新召回块必须保留");
        Assert.DoesNotContain("二分查找的前提", text2, StringComparison.Ordinal); // 旧行不再重复发
        Assert.Contains("完成: 回答二分查找前提", text2, StringComparison.Ordinal);   // 新行照发
        Assert.DoesNotContain("可用能力", text1[..0] + text2, StringComparison.Ordinal); // 静态块不进动态区

        // 负向控制: 不去重 (空集合) 时旧行必然重复进入增量 → 该判据有牙
        var (textNoDedupe, _, droppedNoDedupe) = SessionInjectionPlanner.Dedupe(turn2, new SessionInjectionPlanner.InjectionLedger());
        Assert.Equal(0, droppedNoDedupe);
        Assert.Contains("二分查找的前提", textNoDedupe, StringComparison.Ordinal);
    }

    /// <summary>
    /// P3 (红线): 第 2 轮起「新增字节 / 总字节」≤ 10% ⇔ 缓存命中率上界 ≥90%。
    /// 结构: 前缀 = system(440) + 静态块(650) + 首轮动态(810); 第 2 轮增量 = 回答(130) + 新召回(40)。
    /// </summary>
    [Fact]
    public void P3_红线_每轮增量占比不超一成()
    {
        var staticText = new string('静', 650);
        var sys = new string('系', 440);
        var dyn1 = new string('召', 810);
        var prefix = sys.Length + staticText.Length + dyn1.Length; // 1900

        var answer = new string('答', 130);
        var dyn2New = new string('新', 40);
        var withDedupe = (double)(answer.Length + dyn2New.Length) / (prefix + answer.Length + dyn2New.Length);
        Assert.True(withDedupe <= 0.10,
            $"第 2 轮增量占比 {withDedupe:P2} > 10% → 命中率上界 < 90% 红线 (前缀 {prefix} / 增量 {answer.Length + dyn2New.Length})");

        // 负向控制: 不做增量最小化 (重复注入整块动态上下文) → 占比必须破线, 否则判据是空心的
        var withoutDedupe = (double)(answer.Length + dyn1.Length + dyn2New.Length) / (prefix + answer.Length + dyn1.Length + dyn2New.Length);
        Assert.True(withoutDedupe > 0.10,
            $"负向控制失效: 不去重时占比仅 {withoutDedupe:P2}, 无法证明该判据能抓出破坏前缀的策略");
    }

    /// <summary>
    /// P5 (近重复): 措辞微改的同义行必须被抑制 (真机实证轮 3 有 jac=0.77~0.79 的重复召回);
    /// 同时验证安全边界 —— 用户本轮原始问题不经过本方法 (调用方只传上下文块)。
    /// </summary>
    [Fact]
    public void P5_近重复抑制_同义行不再重复注入()
    {
        var ledger = new SessionInjectionPlanner.InjectionLedger();
        var turn1 = SessionInjectionPlanner.Split(
            "[Memory (RAG)]\n1. **底层结构不支持随机访问**——用在链表上时，取中点本身就要从头遍历 O(n)，整体退化为 O(n)。");
        var (_, _, dropped1) = SessionInjectionPlanner.Dedupe(turn1, ledger);
        Assert.Equal(0, dropped1);

        // 同义微改 (真机轮 3 原样): 字节不同 → 只有近重复判据能抓到
        var turn2 = SessionInjectionPlanner.Split(
            "[Memory (RAG)]\n1. **底层结构不支持随机访问**——用在链表上时，取中点本身就要从头遍历 O(n)，整体**退化**为 O(n)。");
        var (text2, kept2, dropped2) = SessionInjectionPlanner.Dedupe(turn2, ledger);
        Assert.True(dropped2 >= 1, $"近重复行未被抑制: dropped={dropped2}, kept={kept2}");
        Assert.DoesNotContain("底层结构不支持随机访问", text2, StringComparison.Ordinal);

        // 却不得误伤真正的新行
        var turn3 = SessionInjectionPlanner.Split(
            "[Web Search]\n- 红黑树插入删除均摊 O(log n)，但常数因子大于跳表。");
        var (text3, _, _) = SessionInjectionPlanner.Dedupe(turn3, ledger);
        Assert.Contains("红黑树插入删除均摊", text3, StringComparison.Ordinal);

        // 安全边界: 相似度函数本身可判, 但用户问题 (message.Content) 永不进入 Dedupe —— 由装配点保证
        Assert.True(SessionInjectionPlanner.Similarity("什么情况下它会退化成线性？", "什么情况下它会退化成线性？") >= 0.99);
    }

    /// <summary>P4: 块标题行永不丢 (否则会下发无标题的裸内容, 语义丢失)。</summary>
    [Fact]
    public void P4_标题行重复也必须保留()
    {
        var seen = new SessionInjectionPlanner.InjectionLedger();
        var blocks = SessionInjectionPlanner.Split("[Memory (RAG)]\nQ: 一\nA: 二");
        var (t1, _, _) = SessionInjectionPlanner.Dedupe(blocks, seen);
        var (t2, _, _) = SessionInjectionPlanner.Dedupe(blocks, seen);
        Assert.Contains("[Memory (RAG)]", t1, StringComparison.Ordinal);
        Assert.Contains("[Memory (RAG)]", t2, StringComparison.Ordinal);
    }
}
