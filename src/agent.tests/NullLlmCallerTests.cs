using agent;
using agent.templates;
using Xunit;

namespace agent.tests;

/// <summary>
/// NullLLMCaller 契约测试: 无 Key 环境下 LLM 失败必须携带明确错误信息,
/// 且错误文本可透传到 AgentResponse.Error (v7.4 修复的响应间错误丢失问题)。
/// </summary>
public class NullLlmCallerTests
{
    [Fact]
    public async Task CallAsync_ReturnsFailure_WithExplicitError()
    {
        var caller = new NullLLMCaller();
        var prompt = new Prompt { UserMessage = "hello" };

        var response = await caller.CallAsync(prompt);

        Assert.False(response.Success);
        Assert.Equal(string.Empty, response.Content);
        Assert.False(string.IsNullOrEmpty(response.Error));
        Assert.Equal("none", response.Model);
    }

    [Fact]
    public async Task CallAsync_Error_IsActionable()
    {
        // 错误信息必须可行动: 指出配置途径, 而非空串或 "error"
        var caller = new NullLLMCaller();
        var response = await caller.CallAsync(new Prompt { UserMessage = "x" });

        Assert.Contains("AGENT_OPENAI_KEY", response.Error);
    }
}
