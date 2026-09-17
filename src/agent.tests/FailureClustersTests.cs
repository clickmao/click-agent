using agent.roles;
using Xunit;

namespace agent.tests;


/// <summary>R364: 失败簇 — 推理中止赏罚。</summary>
public class FailureClustersTests : IDisposable
{
    private readonly string _dir = Path.Combine(Path.GetTempPath(), "fc_" + Guid.NewGuid().ToString("N"));
    public FailureClustersTests() { Directory.CreateDirectory(_dir); }
    public void Dispose() { if (Directory.Exists(_dir)) Directory.Delete(_dir, true); }

    [Fact]
    public void 罚分达阈值_注入警告()
    {
        var fc = new FailureClusters(_dir);
        for (var i = 0; i < 3; i++) fc.RecordAbort("timeout", "如何求解非线性偏微分方程组");
        var warn = fc.RenderWarning("如何求解非线性偏微分方程组");
        Assert.Contains("推理中止", warn);
    }

    [Fact]
    public void 罚分不足_无警告()
    {
        var fc = new FailureClusters(_dir);
        fc.RecordAbort("timeout", "冷门问题甲");
        Assert.Equal(string.Empty, fc.RenderWarning("冷门问题甲的解法"));
    }

    [Fact]
    public void 不同主题_不串簇()
    {
        var fc = new FailureClusters(_dir);
        for (var i = 0; i < 5; i++) fc.RecordAbort("stagnation", "docker 网络配置问题反复出现");
        Assert.Equal(string.Empty, fc.RenderWarning("git rebase 的正确流程是什么"));
    }

    [Fact]
    public void 落盘重载_簇保持()
    {
        var fc1 = new FailureClusters(_dir);
        for (var i = 0; i < 3; i++) fc1.RecordAbort("timeout", "复现某崩溃问题");
        var fc2 = new FailureClusters(_dir); // 新实例=重启
        Assert.Contains("推理中止", fc2.RenderWarning("复现某崩溃问题"));
    }

    [Fact]
    public void 停滞检测_重复回复判真_变化判假()
    {
        var same = new[] { "方案如下: 使用 A", "方案如下: 使用 A", "方案如下: 使用 A" };
        Assert.True(FailureClusters.IsStagnant(same));
        var diff = new[] { "方案如下: 使用 A", "方案如下: 使用 B", "方案如下: 使用 A" };
        Assert.False(FailureClusters.IsStagnant(diff));
    }

    [Fact]
    public void 簇键_进程间稳定()
    {
        // R365 审查修复: 原 string.GetHashCode() 每进程随机化 → 落盘键重启后失配 (同进程测试测不出)。
        // 硬编码期望值 = 跨进程/跨运行锁定算法; 若未来改 hash/sort 必须显式同步本断言。
        var actual = FailureClusters.ClusterKey("如何求解非线性偏微分方程组") + "|" +
                     FailureClusters.ClusterKey("复现某崩溃问题") + "|" +
                     FailureClusters.ClusterKey("git rebase 的正确流程是什么");
        // 期望值由独立实现 (Python FNV-1a/序数排序) 交叉验证得出 — 非"抄实现输出"。
        Assert.Equal("F04057D8|35C534E9|C837EB65", actual);
    }
}
