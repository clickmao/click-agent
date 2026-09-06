using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 ① 本地模型真接入混合调度: Router 本地通道优先实跑 (桥接协议, 不依赖 LLamaSharp)。
/// </summary>
public class LocalChannelTests
{
    private sealed class FakeLocalInference : ILocalInference
    {
        public int CallCount;
        public bool Available { get; set; } = true;
        public bool FailWithException { get; set; }
        public bool IsAvailable => Available;
        public string ModelName => "local:test-gguf";

        public Task<QueueResponse> CallAsync(QueuePrompt prompt, CancellationToken ct = default)
        {
            CallCount++;
            if (FailWithException)
                throw new InvalidOperationException("vulkan_off");
            return Task.FromResult(new QueueResponse
            {
                Success = true,
                Content = "LOCAL_ANSWER",
                Model = ModelName,
            });
        }
    }

    private static ModelCatalog CatalogWithRemote()
    {
        // 单远端模型 (deepseek 假端点, key env 不存在 → 调用会失败 — 用于断言"没走远端")
        return new ModelCatalog
        {
            Models =
            {
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
    }

    private static ModelCatalog CatalogWithFallback()
    {
        // 手动覆盖测试用: 目录里有一个可被 /model <id> 命中的模型
        return CatalogWithRemote();
    }

    private sealed class StubHttpClientFactory : IHttpClientFactory
    {
        public HttpClient CreateClient(string name) => new();
    }

    [Fact]
    public async Task Local_Channel_Is_First_Choice_When_Available()
    {
        var local = new FakeLocalInference();
        var router = new ModelQueueRouter(CatalogWithRemote(), new StubHttpClientFactory(),
            new Microsoft.Extensions.Logging.Abstractions.NullLogger<ModelQueueRouter>(),
            localInference: local);

        var resp = await router.CallAsync(new QueuePrompt { UserMessage = "hi" },
            TaskKindHint.General, "general");
        Assert.True(resp.Success);
        Assert.Equal("LOCAL_ANSWER", resp.Content);
        Assert.Equal(1, local.CallCount);
        Assert.Contains("channel:local:", router.LastSelectionBasis);
        // 槽已释放 (可继续接)
        var state = router.Scheduler.Snapshot().First(s => s.Channel == ModelChannel.Local);
        Assert.Equal(0, state.Running);
    }

    [Fact]
    public async Task Local_Unavailable_Falls_To_Remote_Catalog()
    {
        var local = new FakeLocalInference { Available = false };
        var router = new ModelQueueRouter(CatalogWithRemote(), new StubHttpClientFactory(),
            new Microsoft.Extensions.Logging.Abstractions.NullLogger<ModelQueueRouter>(),
            localInference: local);

        // 远端目录空 (no_dir) → 失败响应 (证明没走本地)
        var resp = await router.CallAsync(new QueuePrompt { UserMessage = "hi" },
            TaskKindHint.General, "general");
        Assert.False(resp.Success);
        Assert.Equal(0, local.CallCount);
    }

    [Fact]
    public async Task Manual_Override_Bypasses_Local_Channel()
    {
        var local = new FakeLocalInference();
        var catalog = CatalogWithFallback();
        var router = new ModelQueueRouter(catalog, new StubHttpClientFactory(),
            new Microsoft.Extensions.Logging.Abstractions.NullLogger<ModelQueueRouter>(),
            localInference: local);

        Assert.NotEmpty(catalog.Models);
        router.SetManualOverride(catalog.Models[0].Id);
        var resp = await router.CallAsync(new QueuePrompt { UserMessage = "hi" },
            TaskKindHint.General, "general");
        // 手动指定 = 远端假端点路径 (非本地)
        Assert.Equal(0, local.CallCount);
        Assert.StartsWith("manual:", router.LastSelectionBasis);
    }

    [Fact]
    public async Task Local_Failure_Does_Not_Trigger_Failover_Switch()
    {
        var local = new FakeLocalInference { FailWithException = true };
        var router = new ModelQueueRouter(CatalogWithRemote(), new StubHttpClientFactory(),
            new Microsoft.Extensions.Logging.Abstractions.NullLogger<ModelQueueRouter>(),
            localInference: local);

        var resp = await router.CallAsync(new QueuePrompt { UserMessage = "hi" },
            TaskKindHint.General, "general");
        Assert.False(resp.Success);
        Assert.Contains("本地模型调用失败", resp.Error);
        // 无切换审计 (本地失败语义 = 单次失败, 不切备)
        Assert.Empty(router.Switches);
    }
}
