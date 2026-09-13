using System;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R373 机检: **首轮预算策略** —— D1(空正文)/D7(半正文) 同源根因(推理与正文共享 max_tokens) 的正解。
/// 真机铁证(R372 探针 3 连跑, 每轮都触发恢复):
///   `llm_call_recover: first_content_len=0 / first_reasoning_len=26752~28306`(首轮 8192 被推理独占)
///   `llm_call_continue: reason=truncated / before_len=2735`(首轮预算耗尽, 正文被切在半行)
/// 契约: ① 大产物意图(General + code/script/game/...)首轮就给足 32768 → 同题 1 次调用;
///       ② 非大产物意图(闲聊/压缩/标注)保持 8192 → **不得**无条件抬预算(成本纪律);
///       ③ 预算抬升不改变恢复链兜底语义(截断仍会被检出并续写)。
/// </summary>
public sealed class FirstCallBudgetTests
{
    [Theory]
    [InlineData(TaskKindHint.General, "code_generation", 32768)]
    [InlineData(TaskKindHint.General, "coding", 32768)]
    [InlineData(TaskKindHint.General, "CODE_EDIT", 32768)]
    [InlineData(TaskKindHint.General, "写一个 python 游戏并自测", 8192)]   // 不做用户文本关键词猜测
    [InlineData(TaskKindHint.General, "chat", 8192)]
    [InlineData(TaskKindHint.General, "", 8192)]
    [InlineData(TaskKindHint.ContextCompression, "code_generation", 8192)] // 压缩任务产物短
    [InlineData(TaskKindHint.KeywordTagging, "code_generation", 8192)]
    public void 首轮预算_按任务类型给足_非大产物不抬(TaskKindHint kind, string intent, int expect)
    {
        Assert.Equal(expect, ModelQueueRouter.InitialMaxTokens(kind, intent));
    }

    [Fact]
    public async Task 大产物意图_首轮即带32768_且完整回复只花一次调用()
    {
        using var fake = new FakeLlmEndpoint(new[]
        {
            FakeLlmEndpoint.Reply("```python\nprint(\"ok\")\n```", 1234),
        });
        var router = Router(fake);
        var resp = await router.CallAsync(Prompt(), TaskKindHint.General, "code_generation");

        Assert.True(resp.Success);
        Assert.Equal(1, fake.Hits);                                   // 无恢复链 → 同题 1 次调用
        Assert.Contains("\"max_tokens\":32768", fake.Bodies[0]);      // 首轮就给足
    }

    [Fact]
    public async Task 非大产物意图_首轮保持8192()
    {
        using var fake = new FakeLlmEndpoint(new[]
        {
            FakeLlmEndpoint.Reply("好的, 我来解释一下这个原理。", 42),
        });
        var router = Router(fake);
        await router.CallAsync(Prompt(), TaskKindHint.General, "chat");

        Assert.Equal(1, fake.Hits);
        Assert.Contains("\"max_tokens\":8192", fake.Bodies[0]);
    }

    [Fact]
    public async Task 预算抬升不取消恢复兜底_截断仍被续写()
    {
        // 首轮 32768 仍被截断 (极端: 推理极长) → D7 链必须照旧生效
        using var fake = new FakeLlmEndpoint(new[]
        {
            FakeLlmEndpoint.Reply("def f():\n    x = 1\n    return x\n\nif __name__ == \"__main__\":\n    print(", 32768, "冗长推理"),
            FakeLlmEndpoint.Reply("print(\"ok\")\n", 100),
        });
        var router = Router(fake);
        var resp = await router.CallAsync(Prompt(), TaskKindHint.General, "code_generation");

        Assert.Equal(2, fake.Hits);
        Assert.EndsWith("print(\"ok\")\n", resp.Content);
        Assert.DoesNotContain("print(print(", resp.Content);   // 去重重拼, 不重复断点
    }

    private const string KeyEnv = "R373_FAKE_KEY";

    /// <summary>路由只挑 ApiKeyEnv 已设置的模型 → 测试进程内一次性注入假 key (名字唯一, 不污染他测)。</summary>
    static FirstCallBudgetTests() => Environment.SetEnvironmentVariable(KeyEnv, "k");

    /// <summary>R373 真链缺口回归 (本轮真机暴露): 适配器曾把 intent 硬编码成 "general"
    /// → 策略在主链上永不触发 (真机首轮仍 completion_tokens=8192)。本测锁死
    /// 「Prompt.Intent → 适配器 → 路由首轮预算」这条链, 防再次退化成死代码。</summary>
    [Fact]
    public async Task 真链适配器_意图透传_代码任务首轮即32768()
    {
        using var fake = new FakeLlmEndpoint(new[]
        {
            FakeLlmEndpoint.Reply("```python\nprint(1)\n```", 999),
        });
        var adapter = new agent.ModelQueueAdapter(Router(fake));
        var prompt = new agent.templates.Prompt
        {
            SystemPrompt = "s", UserMessage = "用 python 写一个贪吃蛇", Intent = "code_generation", EstimatedTokens = 100,
        };

        var resp = await adapter.CallAsync(prompt);

        Assert.True(resp.Success);
        Assert.Contains("\"max_tokens\":32768", fake.Bodies[0]);
        Assert.Equal(1, fake.Hits);
    }

    private static QueuePrompt Prompt()
        => new() { UserMessage = "用 python 写一个贪吃蛇", EstimatedTokens = 500 };

    private static ModelQueueRouter Router(FakeLlmEndpoint fake)
        => new(Catalog(fake.Endpoint), new StubHttpClientFactory(),
            Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance);

    private static ModelCatalog Catalog(string endpoint) => new()
    {
        Models =
        {
            new ModelCatalogEntry
            {
                Id = "r373-coder", Provider = "deepseek", Endpoint = endpoint, ApiKeyEnv = KeyEnv,
                PriceInPerM = 0, PriceOutPerM = 0, ReasoningScore = 5, CodingScore = 9, ContextWindow = 64000,
                SuitedFor = { "coding" },
            },
        },
    };
}
