using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Text;
using System.Threading.Tasks;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R371 空正文恢复机检 (真缺陷): 推理模型把输出预算全花在思维链 → content 为空却被判 success=true
/// (E2E 铁证: completion 8192/8192, content_len=0, reasoning_len=22633, loop_turn reply_chars=0)。
/// 断言:
///   ① 首次空正文 → 自动**升级输出预算 + 抑制推理**重试一次, 成功后返回正文;
///   ② 两次都空 → **可见降级文案 + Success=false** (绝不静默返回空白);
///   ③ 正常正文 → 不触发重试 (零额外成本)。
/// </summary>
public class EmptyContentRecoveryTests
{
    private const string KeyEnv = "R371_EMPTY_CONTENT_KEY";

    private static ModelCatalog Catalog(string endpoint) => new()
    {
        Models =
        {
            new ModelCatalogEntry
            {
                Id = "r371-reasoner", Provider = "deepseek", Endpoint = endpoint, ApiKeyEnv = KeyEnv,
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

    private static int RoleCount(string body, string role)
    {
        var needle = "\"role\":\"" + role + "\"";
        var n = 0;
        for (var i = body.IndexOf(needle, StringComparison.Ordinal); i >= 0; i = body.IndexOf(needle, i + 1, StringComparison.Ordinal)) n++;
        return n;
    }

    [Fact]
    public async Task 空正文_推理吃满预算_自动升级预算并抑制推理后恢复()
    {
        using var fake = new FakeEndpoint(new[] { EmptyContentWithReasoning(), WithContent("print('snake')") });
        Environment.SetEnvironmentVariable(KeyEnv, "k");
        try
        {
            var router = new ModelQueueRouter(Catalog(fake.Endpoint),
                new StubFactory(), Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance);

            var resp = await router.CallAsync(
                new QueuePrompt { UserMessage = "用 Python 写一个贪吃蛇", ReasoningEffort = "high" },
                TaskKindHint.General, "coding");

            Assert.Equal(2, fake.Hits);                       // 首次空 → 恰好重试一次
            Assert.True(resp.Success);
            Assert.Contains("print('snake')", resp.Content);
            Assert.Null(resp.Error);

            var bodies = fake.Bodies;
            Assert.Contains("\"max_tokens\":32768", bodies[1]);          // 预算升级
            Assert.Equal(0, RoleCount(bodies[0], "system"));             // 首次无抑制提示
            Assert.True(RoleCount(bodies[1], "system") >= 1);            // 重试追加抑制推理提示
        }
        finally
        {
            Environment.SetEnvironmentVariable(KeyEnv, null);
        }
    }

    [Fact]
    public async Task 两次都空正文_可见降级且success为假_绝不静默返回空白()
    {
        using var fake = new FakeEndpoint(new[] { EmptyContentWithReasoning(), EmptyContentWithReasoning() });
        Environment.SetEnvironmentVariable(KeyEnv, "k");
        try
        {
            var router = new ModelQueueRouter(Catalog(fake.Endpoint),
                new StubFactory(), Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance);

            var resp = await router.CallAsync(
                new QueuePrompt { UserMessage = "用 Python 写一个贪吃蛇" }, TaskKindHint.General, "coding");

            Assert.Equal(2, fake.Hits);
            Assert.False(resp.Success);
            Assert.Equal("empty_content_after_retry", resp.Error);
            Assert.Contains("未产出正文", resp.Content);                  // 用户可见, 不是空白
            Assert.NotEqual(string.Empty, resp.Content);
        }
        finally
        {
            Environment.SetEnvironmentVariable(KeyEnv, null);
        }
    }

    [Fact]
    public async Task 正常正文_不触发重试_零额外成本()
    {
        using var fake = new FakeEndpoint(new[] { WithContent("ok") });
        Environment.SetEnvironmentVariable(KeyEnv, "k");
        try
        {
            var router = new ModelQueueRouter(Catalog(fake.Endpoint),
                new StubFactory(), Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance);

            var resp = await router.CallAsync(new QueuePrompt { UserMessage = "hi" }, TaskKindHint.General, "general");

            Assert.Equal(1, fake.Hits);
            Assert.Equal("ok", resp.Content);
            Assert.True(resp.Success);
        }
        finally
        {
            Environment.SetEnvironmentVariable(KeyEnv, null);
        }
    }

    private sealed class StubFactory : IHttpClientFactory
    {
        public System.Net.Http.HttpClient CreateClient(string name) => new();
    }

    /// <summary>本地假端点: 按序返回预置响应体, 记录每次请求体 (零外部依赖, 真 HTTP 通路)。</summary>
    private sealed class FakeEndpoint : IDisposable
    {
        private readonly HttpListener _listener = new();
        private readonly List<string> _bodies = new();
        private readonly string[] _responses;
        private readonly Task _loop;
        private int _hits;

        public FakeEndpoint(string[] responses)
        {
            _responses = responses;
            var port = FreePort();
            Endpoint = $"http://127.0.0.1:{port}/v1/chat/completions";
            _listener.Prefixes.Add($"http://127.0.0.1:{port}/v1/");
            _listener.Start();
            _loop = Task.Run(LoopAsync);
        }

        public string Endpoint { get; }
        public int Hits => _hits;
        public List<string> Bodies => _bodies;

        private async Task LoopAsync()
        {
            while (_listener.IsListening)
            {
                HttpListenerContext ctx;
                try { ctx = await _listener.GetContextAsync(); }
                catch { return; }

                using (var reader = new StreamReader(ctx.Request.InputStream, Encoding.UTF8))
                    _bodies.Add(await reader.ReadToEndAsync());

                var idx = _hits++;
                var payload = _responses[Math.Min(idx, _responses.Length - 1)];
                var bytes = Encoding.UTF8.GetBytes(payload);
                ctx.Response.StatusCode = 200;
                ctx.Response.ContentType = "application/json";
                ctx.Response.ContentLength64 = bytes.Length;
                await ctx.Response.OutputStream.WriteAsync(bytes);
                ctx.Response.Close();
            }
        }

        private static int FreePort()
        {
            var l = new System.Net.Sockets.TcpListener(System.Net.IPAddress.Loopback, 0);
            l.Start();
            var port = ((System.Net.IPEndPoint)l.LocalEndpoint).Port;
            l.Stop();
            return port;
        }

        public void Dispose()
        {
            try { _listener.Stop(); } catch { /* 已停 */ }
        }
    }
}
