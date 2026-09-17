using System;
using System.Text.Json;
using System.Threading.Tasks;
using agent.contract;
using agent.modelqueue;
using agent.templates;
using Xunit;

namespace agent.tests;

/// <summary>
/// R533 机检: **结构化前端结构量轴** + **completion 台账透传**。
/// <para>轴: 结构化前端 (R1, <see cref="Prompt.StructuredSurface"/>=true) ⇒ 请求体不下发 tools、
/// system 逐字节 = 恒定前缀 pin (不加 R522 动作环纪律尾块)。判据只吃调用点显式置位的**结构量**,
/// 不是文本匹配 ⇒ 负控: 同环境变量下关掉结构量标记, 工具面/尾块必须复现 (否则本测空转)。</para>
/// </summary>
public sealed class R533StructuredSurfaceTests
{
    private const string KeyEnv = "R533_FAKE_KEY";

    static R533StructuredSurfaceTests() => Environment.SetEnvironmentVariable(KeyEnv, "k");

    /// <summary>R533-B: 适配器曾漏回填 completion ⇒ 台账恒 0 (中继实报 3,348)。按 provider 实报透传。</summary>
    [Fact]
    public async Task 适配器_completion按provider实报透传_不再恒零()
    {
        using var fake = new FakeLlmEndpoint(new[] { ProviderReply("ok", promptTokens: 100, completionTokens: 3348) });
        var adapter = new ModelQueueAdapter(Router(fake));

        var resp = await adapter.CallAsync(new Prompt
        {
            SystemPrompt = "s", UserMessage = "u", Intent = "code_task", EstimatedTokens = 100,
        });

        Assert.Equal(3348, resp.CompletionTokens);
        Assert.NotEqual(0, resp.CompletionTokens);
        Assert.Equal(100, resp.PromptTokens);
    }

    /// <summary>R533-A 正向: 结构化前端实发请求体 —— 无 tools 键、system 逐字节 = 前缀 pin。</summary>
    [Fact]
    public async Task 结构化前端_实发体无工具面_且system逐字节等于前缀pin()
    {
        using var env = SurfaceEnv.On();
        using var fake = new FakeLlmEndpoint(new[] { ProviderReply("{\"intent\":\"code_task\"}", 100, 10) });
        var adapter = new ModelQueueAdapter(Router(fake));

        // 用**门控会下发工具**的意图键 (code_generation) ⇒ tools 缺席只能归因于结构量轴
        var resp = await adapter.CallAsync(new Prompt
        {
            SystemPrompt = StructuredPrompt.Prefix,
            UserMessage = "task", Intent = "code_generation", EstimatedTokens = 100,
            StructuredSurface = true,
        });

        Assert.True(resp.Success);
        Assert.Equal(1, fake.Hits);                       // 单发: 不进动作环
        using var doc = JsonDocument.Parse(fake.Bodies[0]);
        var root = doc.RootElement;
        Assert.False(root.TryGetProperty("tools", out _));                                  // tools_n = 0
        Assert.Equal(StructuredPrompt.Prefix, root.GetProperty("messages")[0].GetProperty("content").GetString()); // 逐字节
    }

    /// <summary>负控: 同一环境变量下, 无结构量标记 ⇒ 工具面与纪律尾块必须出现 (证明上测非空转)。</summary>
    [Fact]
    public void 负控_同环境下无结构量标记_工具面与纪律尾块复现()
    {
        using var env = SurfaceEnv.On();

        var plain = new QueuePrompt { SystemPrompt = StructuredPrompt.Prefix };
        ModelQueueAdapter.ApplyRequestSurface(
            new Prompt { Intent = "code_generation", StructuredSurface = false }, plain);
        Assert.NotNull(plain.ToolsJson);
        Assert.NotEqual(StructuredPrompt.Prefix, plain.SystemPrompt);

        var structured = new QueuePrompt { SystemPrompt = StructuredPrompt.Prefix };
        ModelQueueAdapter.ApplyRequestSurface(
            new Prompt { Intent = "code_generation", StructuredSurface = true }, structured);
        Assert.Null(structured.ToolsJson);
        Assert.Equal(StructuredPrompt.Prefix, structured.SystemPrompt);
    }

    /// <summary>provider 形状的响应体 (含 usage.total_tokens; 缺它 ⇒ 路由器 TokensUsed=0 ⇒ completion 退化为 0)。</summary>
    private static string ProviderReply(string content, int promptTokens, int completionTokens)
        => "{\"id\":\"r533\",\"choices\":[{\"message\":{\"role\":\"assistant\",\"content\":"
           + JsonSerializer.Serialize(content) + "}}],\"usage\":{\"prompt_tokens\":" + promptTokens
           + ",\"completion_tokens\":" + completionTokens
           + ",\"total_tokens\":" + (promptTokens + completionTokens) + "}}";

    private static ModelQueueRouter Router(FakeLlmEndpoint fake)
        => new(Catalog(fake.Endpoint), new StubHttpClientFactory(),
            Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance);

    private static ModelCatalog Catalog(string endpoint) => new()
    {
        Models =
        {
            new ModelCatalogEntry
            {
                Id = "r533-coder", Provider = "deepseek", Endpoint = endpoint, ApiKeyEnv = KeyEnv,
                PriceInPerM = 0, PriceOutPerM = 0, ReasoningScore = 5, CodingScore = 9, ContextWindow = 64000,
                SuitedFor = { "coding" },
            },
        },
    };

    private sealed class StubHttpClientFactory : System.Net.Http.IHttpClientFactory
    {
        public System.Net.Http.HttpClient CreateClient(string name) => new();
    }

    /// <summary>动作环/工具面/纪律三轴开 (用完逐字节还原), 使结构量轴成为唯一自变量。</summary>
    private sealed class SurfaceEnv : IDisposable
    {
        private readonly (string Name, string? Old)[] _saved;
        private SurfaceEnv((string, string?)[] saved) => _saved = saved;

        public static SurfaceEnv On()
        {
            string[] names =
            {
                "AGENTFRAMEWORK_ACTION_LOOP", "AGENTFRAMEWORK_ACTION_DISCIPLINE",
                "AGENTFRAMEWORK_TOOL_DECL_GATE",
            };
            var saved = new (string, string?)[names.Length];
            for (var i = 0; i < names.Length; i++)
            {
                saved[i] = (names[i], Environment.GetEnvironmentVariable(names[i]));
                Environment.SetEnvironmentVariable(names[i], "1");
            }
            return new SurfaceEnv(saved);
        }

        public void Dispose()
        {
            foreach (var (name, old) in _saved) Environment.SetEnvironmentVariable(name, old);
        }
    }
}
