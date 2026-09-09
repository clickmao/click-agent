using agent.exploration;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.13.3 R276 — 关键文档激活链 (LinkRegistry) 单测。
/// 三信号预判: 锚定/结构/递进; 激活阈值 ≥3; 激活链保护 (父链 URL 一并保留)。
/// 背景: LinkDoc 压缩实证 (keys 14%) — 深层链接入口必须可激活可保护。
/// </summary>
public class LinkRegistryTests
{
    [Fact]
    public void Register_Dedupes_And_Tracks_Depth()
    {
        var reg = new LinkRegistry();
        var e1 = reg.Register("https://x.example/entry", null);
        var e2 = reg.Register("https://x.example/entry", null);
        Assert.Same(e1, e2);
        Assert.Equal(0, e1.Depth);
        var e3 = reg.Register("https://x.example/critical-doc-42", "https://x.example/entry");
        Assert.Equal(1, e3.Depth);
        Assert.Equal(2, reg.Count);
    }

    [Fact]
    public void PreJudge_Anchor_In_Query_Is_Strong()
    {
        var reg = new LinkRegistry();
        var url = "https://x.example/internal/critical-doc-42";
        reg.Register(url, "https://x.example/internal/entry");
        // URL 全文出现在任务 query → 锚定 2 分
        var s = reg.PreJudge(url, $"请阅读 {url} 总结要点", Array.Empty<string>(), inThinkMemory: false);
        Assert.True(s >= 2, $"锚定信号应贡献 2 分, 实得 {s}");
    }

    [Fact]
    public void PreJudge_Scarce_OutLinks_And_Path_Convergence_Raise_Score()
    {
        var reg = new LinkRegistry();
        var entry = "https://x.example/internal/entry";
        var url = "https://x.example/internal/critical-doc-42";
        reg.Register(url, entry);
        // 结构: 同父只此 1 条出链 (+2); 递进: 同域同 /internal/ 前缀 (+2)
        var s = reg.PreJudge(url, "核实苹果颜色", new[] { url, "https://y.example/other" }, inThinkMemory: false);
        // (y.example 不同域 → 递进 0 分; 结构 +2 = 总 2)
        Assert.Equal(2, s);
        // 加同域同路径前缀 sibling → 递进 +2 = 总 4
        var s2 = reg.PreJudge(url, "核实苹果颜色", new[] { url, "https://x.example/internal/critical-doc-43", "https://y.example/z" }, inThinkMemory: false);
        // 结构: 同父出链 2 条 (≤3 → +1); 递进: 同域同目录前缀 (+2) → 总 3 = 激活阈值
        Assert.True(s2 >= 3, $"结构+递进应 ≥3, 实得 {s2}");
    }

    [Fact]
    public void ActivateIfWorthy_Marks_Protected_Parent_Chain()
    {
        var reg = new LinkRegistry();
        var root = "https://x.example/entry";
        var mid = "https://x.example/internal/entry";
        var leaf = "https://x.example/internal/critical-doc-42";
        reg.Register(root, null);
        reg.Register(mid, root);
        var leafEntry = reg.Register(leaf, mid);
        // 锚定 2 + 稀缺 2 + 递进 2 = 6 ≥ 3 → 激活, 父链 root+mid 保护
        var protectedUrls = reg.ActivateIfWorthy(leafEntry, 6, "query", new[] { leaf, mid }, inThinkMemory: false);
        Assert.True(leafEntry.Activated);
        Assert.Contains(leaf, protectedUrls);
        Assert.Contains(mid, protectedUrls);
        Assert.Contains(root, protectedUrls);
    }

    [Fact]
    public void ActivateIfWorthy_LowScore_Not_Activated()
    {
        var reg = new LinkRegistry();
        var url = "https://x.example/random-link";
        var e = reg.Register(url, null);
        var protectedUrls = reg.ActivateIfWorthy(e, 1, "无关任务", new[] { url, "a", "b", "c", "d" }, inThinkMemory: false);
        Assert.False(e.Activated);
        Assert.Empty(protectedUrls);
    }
}
