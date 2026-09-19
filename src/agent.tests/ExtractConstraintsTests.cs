using Xunit;
using agent;

namespace agent.tests;

public class ExtractConstraintsTests
{
    [Fact]
    public void ExtractsExplicitConstraintSegment()
    {
        var c = IndustrialAgentV2.ExtractConstraints("帮我写个爬虫项目，约束：只能用标准库，不许用第三方框架");
        Assert.Contains(c, x => x.Contains("标准库"));
    }

    [Fact]
    public void NoExplicitSlot_NoMechanicalConstraint()
    {
        // 词表移除后 (2026-09-19): 「必须用/不许用」助动词表已删 ⇒ 非显式槽位形式 (无短头+冒号)
        // 不再机械抽取; 该约束由 LLM 结构化槽位链承担, 机械面不凭词面猜。
        Assert.Empty(IndustrialAgentV2.ExtractConstraints("做一个API服务，必须用PostgreSQL。性能要好"));
    }

    [Fact]
    public void EmptyForNoConstraints()
    {
        Assert.Empty(IndustrialAgentV2.ExtractConstraints("你好"));
    }
}
