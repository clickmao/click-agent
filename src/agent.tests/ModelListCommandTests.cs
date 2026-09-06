using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// v0.10.0 /model list 与序号指定:
///   ① /model list 返回目录模型序号化列表 (1-N, Index=目录顺序, IsActive 标注当前)
///   ② /model &lt;序号&gt; 等价 /model &lt;id&gt; (manual 模式); 序号越界诚实报错
///   ③ /model auto 恢复自动模式 (Mode: auto/manual 载荷字段)
/// </summary>
public class ModelListCommandTests
{
    private static ModelCatalog TestCatalog() => new()
    {
        Models =
        {
            new ModelCatalogEntry
            {
                Id = "gpt-4o", Provider = "openai",
                Endpoint = "https://api.openai.com/v1/chat/completions",
                ApiKeyEnv = "AGENT_OPENAI_KEY",
                PriceInPerM = 2.5, PriceOutPerM = 10.0,
                ReasoningScore = 8, CodingScore = 8, ContextWindow = 128000,
                SuitedFor = { "general", "coding", "reasoning", "planning" },
            },
            new ModelCatalogEntry
            {
                Id = "glm-4-flash", Provider = "zhipu",
                Endpoint = "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                ApiKeyEnv = "ZHIPU_KEY",
                PriceInPerM = 0.07, PriceOutPerM = 0.28,
                ReasoningScore = 5, CodingScore = 5, ContextWindow = 128000,
                SuitedFor = { "general", "compression" },
            },
            new ModelCatalogEntry
            {
                Id = "deepseek-chat", Provider = "deepseek",
                Endpoint = "https://api.deepseek.com/chat/completions",
                ApiKeyEnv = "AGENT_DEEPSEEK_KEY",
                PriceInPerM = 0.14, PriceOutPerM = 0.28,
                ReasoningScore = 7, CodingScore = 7, ContextWindow = 64000,
                SuitedFor = { "general", "coding" },
            },
        },
    };

    private sealed class StubHttpClientFactory : IHttpClientFactory
    {
        public HttpClient CreateClient(string name) => new();
    }

    private static ModelQueueRouter NewRouter() => new(
        TestCatalog(), new StubHttpClientFactory(),
        Microsoft.Extensions.Logging.Abstractions.NullLogger<ModelQueueRouter>.Instance);

    [Fact]
    public void Catalog_Order_Defines_List_Index()
    {
        // /model list 序号 = models.yaml 目录顺序 (1-N) — 载荷在 V2 指令层,
        // 这里锁定 Router 侧的数据源语义: Catalog 暴露 + ManualOverride 初始为 null (auto)
        var router = NewRouter();
        Assert.Equal(3, router.Catalog.Models.Count);
        Assert.Null(router.ManualOverride);

        // 第 N 个模型 = 序号 N
        Assert.Equal("gpt-4o", router.Catalog.Models[0].Id);
        Assert.Equal("glm-4-flash", router.Catalog.Models[1].Id);
        Assert.Equal("deepseek-chat", router.Catalog.Models[2].Id);
    }

    [Fact]
    public void Index_Selection_Equals_Id_Selection()
    {
        // /model 3 ≡ /model deepseek-chat: 目录第 3 项
        var router = NewRouter();
        var chosen = router.Catalog.Models[2];

        Assert.True(router.SetManualOverride(chosen.Id));
        Assert.Equal("deepseek-chat", router.ManualOverride);
        Assert.Equal("deepseek-chat", router.ActiveModel?.Id);
        Assert.Equal("manual:deepseek-chat", router.LastSelectionBasis);
    }

    [Fact]
    public void Auto_Clears_Manual_Override()
    {
        var router = NewRouter();
        Assert.True(router.SetManualOverride("glm-4-flash"));
        Assert.NotNull(router.ManualOverride);

        // /model auto → 回到 auto 模式
        Assert.True(router.SetManualOverride("auto"));
        Assert.Null(router.ManualOverride);
    }

    [Fact]
    public void Unknown_Id_Returns_False()
    {
        var router = NewRouter();
        Assert.False(router.SetManualOverride("no-such-model"));
        // 未知 id 不改变状态
        Assert.Null(router.ManualOverride);
    }
}
