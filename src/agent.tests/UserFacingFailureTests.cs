using System;
using System.IO;
using System.Threading.Tasks;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R414: 失败轮「可见性 vs 内部信息外泄」裁定 (真缺陷闭合)。
///
/// 事故链: ModelQueueRouter 在「空正文重试后仍失败」时写入**面向用户的降级文案** + Success=false;
/// 而 IndustrialAgentV2 的失败分支一律 `response.Content = string.Empty` ⇒ 文案被丢弃、用户看到空白。
/// 真机证据 (eval/rover/r371d7, empty_always 臂): 轮 1 reply_len=0 / loop_turn.reply_chars=0, 轮 2 才见文案。
///
/// 判据:
///   ① router 侧: 降级文案必须带 ContentIsUserFacing=true (否则链侧无从区分「可展示」与「内部片段」);
///   ② 链侧裁定: 只有标记位为真才透出;
///   ③ 未标记的失败 Content **不得**外泄 (原始报错/内部片段);
///   ④ 源级钉死: 失败分支不得回落 string.Empty; 可见降级文案不得拼接 ex.Message。
/// </summary>
public class UserFacingFailureTests
{
    private const string KeyEnv = "R414_USER_FACING_KEY";

    private static ModelCatalog Catalog(string endpoint) => new()
    {
        Models =
        {
            new ModelCatalogEntry
            {
                Id = "r414-reasoner", Provider = "deepseek", Endpoint = endpoint, ApiKeyEnv = KeyEnv,
                PriceInPerM = 0, PriceOutPerM = 0, ReasoningScore = 9, CodingScore = 8, ContextWindow = 64000,
                SuitedFor = { "general", "coding", "reasoning" },
            },
        },
    };

    private static string EmptyContentWithReasoning()
        => "{\"id\":\"r\",\"choices\":[{\"message\":{\"role\":\"assistant\",\"content\":\"\",\"reasoning_content\":\""
           + new string('思', 400)
           + "\"}}],\"usage\":{\"prompt_tokens\":100,\"completion_tokens\":8192}}";

    private static string WithContent(string content)
        => "{\"id\":\"r\",\"choices\":[{\"message\":{\"role\":\"assistant\",\"content\":\"" + content
           + "\"}}],\"usage\":{\"prompt_tokens\":100,\"completion_tokens\":40}}";

    private static async Task<QueueResponse> CallAsync(FakeLlmEndpoint fake)
        => await new ModelQueueRouter(Catalog(fake.Endpoint), new StubHttpClientFactory(),
                Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance)
            .CallAsync(new QueuePrompt { UserMessage = "用 Python 写一个贪吃蛇" }, TaskKindHint.General, "coding");

    [Fact]
    public async Task 判据1_两次都空_降级文案必须标记为面向用户()
    {
        using var fake = new FakeLlmEndpoint(new[] { EmptyContentWithReasoning(), EmptyContentWithReasoning() });
        Environment.SetEnvironmentVariable(KeyEnv, "k");
        try
        {
            var resp = await CallAsync(fake);

            Assert.False(resp.Success);                          // 不假装成功
            Assert.Equal("empty_content_after_retry", resp.Error);
            Assert.Contains("未产出正文", resp.Content);          // 文案仍在
            Assert.True(resp.ContentIsUserFacing);               // ★ 且被显式标记 ⇒ 链侧才可能透出
        }
        finally { Environment.SetEnvironmentVariable(KeyEnv, null); }
    }

    [Fact]
    public async Task 判据2_正常正文_不得被标记为降级文案()
    {
        using var fake = new FakeLlmEndpoint(new[] { WithContent("ok") });
        Environment.SetEnvironmentVariable(KeyEnv, "k");
        try
        {
            var resp = await CallAsync(fake);

            Assert.True(resp.Success);
            Assert.Equal("ok", resp.Content);
            Assert.False(resp.ContentIsUserFacing);              // 标记位不得滥标 (否则失败文案语义被稀释)
        }
        finally { Environment.SetEnvironmentVariable(KeyEnv, null); }
    }

    [Fact]
    public void 判据3_裁定函数_只透出被标记的失败正文()
    {
        var marked = new LLMResponse
        { Success = false, Error = "empty_content_after_retry", ContentIsUserFacing = true, Content = "⚠ 模型未产出正文 — 请重试或切换模型。" };
        Assert.Equal(marked.Content, agent.IndustrialAgentV2.UserFacingFailureContent(marked));

        var unmarked = new LLMResponse
        { Success = false, Error = "upstream_500", ContentIsUserFacing = false, Content = "{\"error\":{\"message\":\"invalid api key sk-abcd\"}}" };
        Assert.Equal(string.Empty, agent.IndustrialAgentV2.UserFacingFailureContent(unmarked));   // 内部报错不外泄

        var markedEmpty = new LLMResponse { Success = false, ContentIsUserFacing = true, Content = string.Empty };
        Assert.Equal(string.Empty, agent.IndustrialAgentV2.UserFacingFailureContent(markedEmpty)); // 不凭空造文案

        var markedNull = new LLMResponse { Success = false, ContentIsUserFacing = true, Content = null! };
        Assert.Equal(string.Empty, agent.IndustrialAgentV2.UserFacingFailureContent(markedNull));
    }

    // ---------- 判据 4: 源级钉死 (防回落) ----------
    private static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln"))) dir = dir.Parent;
        return dir?.FullName ?? ".";
    }

    private static string Flat(string relative)
        => string.Join(' ', File.ReadAllText(Path.Combine(RepoRoot(), relative))
            .Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));

    [Fact]
    public void 判据4a_链侧失败分支必须经裁定函数_不得回落空白()
    {
        var flat = Flat(Path.Combine("src", "agent", "IndustrialAgentV2.cs"));
        Assert.Contains("response.Content = UserFacingFailureContent(llmResponse)", flat);
        Assert.DoesNotContain("response.Content = string.Empty", flat);   // 事故原形: 一律丢弃
        Assert.Contains("internal static string UserFacingFailureContent", flat);
    }

    [Fact]
    public void 判据4b_降级文案必须被标记且不得拼接异常原文()
    {
        var flat = Flat(Path.Combine("src", "agent.modelqueue", "ModelQueueRouter.cs"));
        Assert.Contains("retried.ContentIsUserFacing = true;", flat);     // 两次都空 (正常路径)
        Assert.Contains("first.ContentIsUserFacing = true;", flat);       // 重试抛异常路径
        Assert.Contains("\"⚠ 模型未产出正文, 且自动重试失败 — 请重试或切换模型。\"", flat);
        Assert.DoesNotContain("\"⚠ 模型未产出正文, 且自动重试失败: \" + ex.Message", flat);  // 凭据/内部信息卫生

        var adapter = Flat(Path.Combine("src", "agent", "modelqueue", "ModelQueueAdapter.cs"));
        Assert.Contains("ContentIsUserFacing = r.ContentIsUserFacing,", adapter);            // 契约位必须透传
    }
}
