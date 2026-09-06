using Xunit;
using agent;

public class ExtractConstraintsTests
{
    [Fact]
    public void ExtractsExplicitConstraintSegment()
    {
        var c = IndustrialAgentV2.ExtractConstraints("帮我写个爬虫项目，约束：只能用标准库，不许用第三方框架");
        Assert.Contains(c, x => x.Contains("标准库"));
    }

    [Fact]
    public void ExtractsAuxiliaryConstraint()
    {
        var c = IndustrialAgentV2.ExtractConstraints("做一个API服务，必须用PostgreSQL。性能要好");
        Assert.Contains(c, x => x.Contains("必须用PostgreSQL"));
    }

    [Fact]
    public void EmptyForNoConstraints()
    {
        Assert.Empty(IndustrialAgentV2.ExtractConstraints("你好"));
    }
}
