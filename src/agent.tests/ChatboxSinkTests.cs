using agent.logging;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 L.6 chatbox 推送通道测试: ConsoleChatboxSink 协议行格式 + LogRouter sink 双写 + 推送失败不打断主链。
/// </summary>
public class ChatboxSinkTests
{
    [Fact]
    public void Console_Sink_Emits_Single_Line_Json()
    {
        var sw = new StringWriter();
        var sink = new ConsoleChatboxSink(sw);
        sink.Push(new FrontendDirective { Type = "thinking_page_switch", SessionId = "s1", Seq = 3 });
        var line = sw.ToString().TrimEnd();
        Assert.StartsWith("@chatbox:", line); // 协议前缀
        Assert.DoesNotContain("\n", line.TrimEnd()); // 单行
        Assert.Contains("\"Type\":\"thinking_page_switch\"", line); // PascalCase 契约
        Assert.Contains("\"Seq\":3", line);
    }

    [Fact]
    public void Router_Pushes_To_Sink_And_Cache()
    {
        var sw = new StringWriter();
        var buffer = new MemoryLogBuffer(10);
        var router = new LogRouter(LogFlags.All, buffer, sessionId: "s1")
        {
            ChatboxSink = new ConsoleChatboxSink(sw),
        };
        router.Write("mod", "info", LogChannel.Thinking, "步骤一");
        router.EmitThinkingEnd(10);

        var output = sw.ToString();
        Assert.Contains("thinking_page_switch", output); // sink 收到
        Assert.Contains("thinking_end", output);
        Assert.Equal(2, router.Directives.Count);         // 缓存同步双写
    }

    [Fact]
    public void Router_Without_Sink_Still_Caches()
    {
        var router = new LogRouter(LogFlags.All, new MemoryLogBuffer(10), sessionId: "s1");
        router.Write("mod", "info", LogChannel.Output, "结果");
        Assert.Single(router.Directives); // 无 sink → 仅缓存 (P1 行为兼容)
    }

    private sealed class ThrowingSink : IChatboxSink
    {
        public void Push(FrontendDirective directive) => throw new InvalidOperationException("boom");
    }

    [Fact]
    public void Router_Sink_Failure_Does_Not_Break_Write()
    {
        var router = new LogRouter(LogFlags.All, new MemoryLogBuffer(10), sessionId: "s1")
        {
            ChatboxSink = new ThrowingSink(),
        };
        // 契约: 推送失败不得打断主链 — sink 自吞异常; router 侧写入正常
        router.Write("mod", "info", LogChannel.Thinking, "步骤");
        Assert.Single(router.Directives);
    }

    [Fact]
    public void Throwing_Sink_Swallows_Exception()
    {
        var sink = new ConsoleChatboxSink(new ThrowingWriter());
        sink.Push(new FrontendDirective { Type = "output_append" }); // 不抛
    }

    private sealed class ThrowingWriter : TextWriter
    {
        public override System.Text.Encoding Encoding => System.Text.Encoding.UTF8;
        public override void Write(char value) => throw new InvalidOperationException("io");
        public override void WriteLine(string? value) => throw new InvalidOperationException("io");
    }
}
