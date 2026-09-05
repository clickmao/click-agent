using System.IO;
using System.Linq;
using agent.io;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 需求2 测试: agent.io 行协议读写 — 单行指令/chatbox 指令/流式块/JSON 快速解析。
/// </summary>
public class AgentIoTests
{
    [Fact]
    public void Reader_Classifies_Text_Chatbox_Json_Events()
    {
        var input = string.Join("\n", new[]
        {
            "普通文本回复",
            "@chatbox:{\"Event\":\"thinking_page_switch\",\"Page\":2}",
            "{\"Command\":\"status\",\"Ok\":true}",
        });
        var reader = new TextReportReader(new StringReader(input));
        var events = reader.ReadAll();

        Assert.Equal(ReportEventKind.Text, events[0].Kind);
        Assert.Equal(ReportEventKind.ChatboxDirective, events[1].Kind);
        Assert.Equal("{\"Event\":\"thinking_page_switch\",\"Page\":2}", events[1].Payload);
        Assert.Equal(ReportEventKind.Json, events[2].Kind);
    }

    [Fact]
    public void Reader_Aggregates_Stream_Block()
    {
        var input = string.Join("\n", new[]
        {
            "@stream begin",
            "第一行 流式内容",
            "第二行 {不是json",
            "@stream end",
            "块后文本",
        });
        var reader = new TextReportReader(new StringReader(input));
        var block = reader.ReadStreamBlock();

        Assert.NotNull(block);
        Assert.Equal(2, block.Count);
        Assert.Equal("第二行 {不是json", block[1]); // 块内不误判 JSON
        var after = reader.ReadEvent();
        Assert.Equal(ReportEventKind.Text, after!.Kind);
    }

    [Fact]
    public void Writer_Single_Line_And_Stream_Block_Roundtrip()
    {
        var sb = new System.Text.StringBuilder();
        var writer = new AgentRequestWriter(new StringWriter(sb));
        writer.WriteRequest("/status");
        writer.WriteRequest("多行\n内容"); // 含换行 → 自动流式块

        var reader = new TextReportReader(new StringReader(sb.ToString()));
        var first = reader.ReadEvent();
        Assert.Equal(ReportEventKind.Text, first!.Kind);
        Assert.Equal("/status", first.Payload);

        var block = reader.ReadStreamBlock();
        Assert.NotNull(block);
        Assert.Equal(new[] { "多行", "内容" }, block!.ToArray());
    }

    [Fact]
    public void Eof_Is_Reported()
    {
        var reader = new TextReportReader(new StringReader(""));
        Assert.Equal(ReportEventKind.Eof, reader.ReadEvent()!.Kind);
    }
}
