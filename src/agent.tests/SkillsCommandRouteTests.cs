
using agent.registry;
using Xunit;

namespace agentframework.tests;

public class SkillsCommandRouteTests
{
    [Fact]
    public void Skills_IsKnownCommand()
    {
        var r = LocalCommandRouter.TryRoute("/skills");
        Assert.True(r.Handled, "/skills 应被本地指令拦截");
        Assert.Equal("skills", r.Command);
    }

    [Fact]
    public void SkillsOnly_WithArgs_Parsed()
    {
        var r = LocalCommandRouter.TryRoute("/skills-only critic-rules,git-commit-helper");
        Assert.True(r.Handled);
        Assert.Equal("skills-only", r.Command);
        Assert.Equal("critic-rules,git-commit-helper", r.Argument);
    }
}
