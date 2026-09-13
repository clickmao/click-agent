using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;

namespace agent.tests;

/// <summary>测试用 HTTP 客户端工厂 (不共享连接, 保证每次调用都是一次真实 HTTP 往返)。</summary>
internal sealed class StubHttpClientFactory : IHttpClientFactory
{
    public HttpClient CreateClient(string name) => new();
}

/// <summary>本地假 LLM 端点: 按序返回预置响应体, 记录每次请求体 (零外部依赖, 真 HTTP 通路)。</summary>
internal sealed class FakeLlmEndpoint : IDisposable
{
    private readonly HttpListener _listener = new();
    private readonly List<string> _bodies = new();
    private readonly string[] _responses;
    private readonly Task _loop;
    private int _hits;

    public FakeLlmEndpoint(string[] responses)
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

    /// <summary>构造一条 OpenAI 兼容响应体 (content 自动 JSON 转义)。</summary>
    public static string Reply(string content, int completionTokens = 40, string? reasoning = null)
    {
        var r = reasoning is null ? "" : ",\"reasoning_content\":" + System.Text.Json.JsonSerializer.Serialize(reasoning);
        return "{\"id\":\"r\",\"choices\":[{\"message\":{\"role\":\"assistant\",\"content\":"
               + System.Text.Json.JsonSerializer.Serialize(content) + r
               + "}}],\"usage\":{\"prompt_tokens\":100,\"completion_tokens\":" + completionTokens + "}}";
    }

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
