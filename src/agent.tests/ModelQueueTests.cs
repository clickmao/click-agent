using agent.modelqueue;
using agent.config;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 模型队列测试 (plan_model_queue.md C.4 验收):
/// 目录解析、三策略选模、主/备切换、手动覆盖、/balance 与 /model verify 服务、取消不切换。
/// </summary>
public class ModelQueueTests
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
                PriceInPerM = 0.1, PriceOutPerM = 0.1,
                ReasoningScore = 5, CodingScore = 5, ContextWindow = 128000,
                SuitedFor = { "chat", "summary", "classify" },
            },
            new ModelCatalogEntry
            {
                Id = "deepseek-reasoner", Provider = "deepseek",
                Endpoint = "https://api.deepseek.com/v1/chat/completions",
                ApiKeyEnv = "DEEPSEEK_KEY",
                PriceInPerM = 0.55, PriceOutPerM = 2.19,
                ReasoningScore = 9, CodingScore = 8, ContextWindow = 64000,
                SuitedFor = { "reasoning", "planning", "debug" },
            },
        },
        BalanceSchemes =
        {
            ["openai"] = new BalanceScheme
            {
                Endpoint = "https://api.openai.com/v1/dashboard/billing/subscription",
                Note = "hard_limit_usd 作额度上界",
            },
            ["deepseek"] = new BalanceScheme
            {
                Endpoint = "https://api.deepseek.com/user/balance",
                Note = "balance_infos[0].balance",
            },
        },
    };

    // ── C.6 目录与策略 ──

    [Fact]
    public void Manual_Override_Wins()
    {
        var policy = new ModelSelectionPolicy();
        var picked = policy.Select("glm-4-flash", TaskKindHint.General, "coding", 1000, 500, TestCatalog());
        Assert.Equal("glm-4-flash", picked?.Id);
    }

    [Fact]
    public void Cost_Routing_Picks_Cheapest_For_Compression()
    {
        var policy = new ModelSelectionPolicy();
        var picked = policy.Select(null, TaskKindHint.ContextCompression, "general", 100_000, 20_000, TestCatalog());
        // 压缩 = 性能不敏感 → 最便宜 (glm-4-flash)
        Assert.Equal("glm-4-flash", picked?.Id);
    }

    [Fact]
    public void Auto_Planning_Intent_Prefers_Reasoning()
    {
        var policy = new ModelSelectionPolicy();
        var picked = policy.Select(null, TaskKindHint.General, "planning", 5_000, 2_000, TestCatalog());
        // planning 重推理 → deepseek-reasoner (9 分) 或 gpt-4o (8 分) 胜过 flash
        Assert.Contains(picked?.Id, new[] { "deepseek-reasoner", "gpt-4o" });
    }

    [Fact]
    public void Auto_Chat_Intent_Prefers_Cheap()
    {
        var policy = new ModelSelectionPolicy();
        var picked = policy.Select(null, TaskKindHint.General, "chat", 2_000, 500, TestCatalog());
        // chat 轻意图 + 费用惩罚 → flash
        Assert.Equal("glm-4-flash", picked?.Id);
    }

    [Fact]
    public void Estimated_Cost_Math()
    {
        var m = TestCatalog().Models[0]; // gpt-4o: in 2.5 out 10
        var cost = ModelSelectionPolicy.EstimatedCost(m, 1_000_000, 1_000_000);
        Assert.Equal(12.5, cost, precision: 6);
    }

    // ── C.3.3 路由器: 手动/切换审计/取消 ──

    [Fact]
    public void Router_Manual_Set_And_Auto_Restore()
    {
        var router = new ModelQueueRouter(TestCatalog(), new HttpClientFactoryStub(),
            Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance);
        Assert.True(router.SetManualOverride("deepseek-reasoner"));
        Assert.Equal("deepseek-reasoner", router.ActiveModel?.Id);
        Assert.True(router.SetManualOverride("auto"));
        Assert.Equal("gpt-4o", router.ActiveModel?.Id); // 目录第一个
        // 未知 id 拒绝
        Assert.False(router.SetManualOverride("nonexistent-model"));
    }

    [Fact]
    public async Task Router_Consecutive_Failures_Switch_With_Audit()
    {
        // 本地假端点: 主模型 (openai) 恒 500 → 3 败后切备
        using var listener = new System.Net.HttpListener();
        var port = FreeTcpPort();
        listener.Prefixes.Add($"http://127.0.0.1:{port}/v1/");
        listener.Start();
        var hitCount = 0;
        var serverTask = Task.Run(async () =>
        {
            while (listener.IsListening)
            {
                try
                {
                    var ctx = await listener.GetContextAsync();
                    var n = System.Threading.Interlocked.Increment(ref hitCount);
                    if (n <= 3)
                    {
                        // 主模型: 首次 + 请求内重试 2 次 = 3 个 500 (v0.11.0 R23 语义)
                        ctx.Response.StatusCode = 500;
                        ctx.Response.Close();
                    }
                    else
                    {
                        // 备模型 (切备后): 返回合法 chat 响应
                        var body = "{\"id\":\"1\",\"choices\":[{\"message\":{\"role\":\"assistant\",\"content\":\"ok\"}}],\"usage\":{\"prompt_tokens\":1,\"completion_tokens\":1}}";
                        var bytes = System.Text.Encoding.UTF8.GetBytes(body);
                        ctx.Response.StatusCode = 200;
                        ctx.Response.ContentType = "application/json";
                        ctx.Response.ContentLength64 = bytes.Length;
                        ctx.Response.OutputStream.Write(bytes, 0, bytes.Length);
                        ctx.Response.Close();
                    }
                }
                catch (Exception) { break; }
            }
        });
        try
        {
            var catalog = TestCatalog();
            catalog.Models[0].Endpoint = $"http://127.0.0.1:{port}/v1/chat/completions";
            catalog.Models[0].ApiKeyEnv = "MQ_TEST_KEY";
            catalog.Models[1].ApiKeyEnv = "MQ_TEST_BACKUP"; // v0.11.0 R23: 备选需 key 可用 (过滤规则), 给备 key 才能切
            catalog.Models[1].Endpoint = $"http://127.0.0.1:{port}/v1/chat/completions"; // 备模型同端点: 前 3 次 500 后成功
            Environment.SetEnvironmentVariable("MQ_TEST_KEY", "k");
            Environment.SetEnvironmentVariable("MQ_TEST_BACKUP", "k2");
            try
            {
                var router = new ModelQueueRouter(catalog, new HttpClientFactoryStub(),
                    Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance);
                // 主模型瞬态失败 → 请求内重试后切备 (v0.11.0 R23 failover 增强)
                await router.CallAsync(new QueuePrompt { UserMessage = "hi" }, TaskKindHint.General, "general");
                Assert.Contains(router.Switches, s => s.Reason == "transient_failover");
                Assert.NotEqual("gpt-4o", router.ActiveModel?.Id);
            }
            finally
            {
                Environment.SetEnvironmentVariable("MQ_TEST_KEY", null);
                Environment.SetEnvironmentVariable("MQ_TEST_BACKUP", null);
            }
        }
        finally
        {
            listener.Stop();
            await serverTask;
        }
    }

    private static int FreeTcpPort()
    {
        var l = new System.Net.Sockets.TcpListener(System.Net.IPAddress.Loopback, 0);
        l.Start();
        var port = ((System.Net.IPEndPoint)l.LocalEndpoint).Port;
        l.Stop();
        return port;
    }

    // ── C.6.5 校验服务 (真实网络: 假 key 探测 openai 官方端点) ──

    [Fact]
    public async Task Verify_Real_OpenAI_Endpoint_With_Fake_Key()
    {
        var svc = new ModelVerifyService(TestCatalog(), new HttpClientFactoryStub());
        var result = await svc.VerifyAsync("gpt-4o");
        // 网络可达时: 401/403 = 合法; 网络不可达 (CI 离线) 时跳过断言 — 但要有诚实 Error
        if (result.HttpStatusCode > 0)
        {
            Assert.True(result.Ok, $"verdict={result.Verdict}");
        }
        else
        {
            Assert.False(result.Ok);
            Assert.NotNull(result.Error);
        }
    }

    // ── C.3.5 余额 (无 key 场景诚实报错) ──

    [Fact]
    public async Task Balance_Without_Key_Honest_Error()
    {
        Environment.SetEnvironmentVariable("AGENT_OPENAI_KEY", null);
        var svc = new BalanceQueryService(TestCatalog(), new HttpClientFactoryStub());
        var result = await svc.QueryAsync("gpt-4o");
        Assert.False(result.Ok);
        Assert.Contains("AGENT_OPENAI_KEY", result.Error);
    }

    [Fact]
    public async Task Balance_Unknown_Provider_Honest()
    {
        var catalog = TestCatalog();
        catalog.BalanceSchemes.Clear(); // zhipu 本就无 scheme; 清空确保
        var svc = new BalanceQueryService(catalog, new HttpClientFactoryStub());
        Environment.SetEnvironmentVariable("ZHIPU_KEY", "fake");
        try
        {
            var result = await svc.QueryAsync("glm-4-flash");
            Assert.False(result.Ok);
            Assert.Equal("provider_not_supported", result.Error);
        }
        finally
        {
            Environment.SetEnvironmentVariable("ZHIPU_KEY", null);
        }
    }

    private sealed class HttpClientFactoryStub : IHttpClientFactory
    {
        public HttpClient CreateClient(string name) => new();
    }
}
