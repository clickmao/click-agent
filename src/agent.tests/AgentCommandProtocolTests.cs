using System;
using System.IO;
using System.Threading.Tasks;
using agent.io;
using Xunit;

namespace agent.tests;

/// <summary>
/// v0.11.0 统一命令协议契约 (用户定案):
///   ① AgentCommand 编解码对称 (转义: 空格/=/百分号/换行)
///   ② AgentCommandWriter/Reader 组合 (基于 WriterBase/ReaderBase 工具类) — @cmd 行协议
///   ③ 三种传输对命令层透明: Console.IO (Text) / 共享内存 (MMF 环形) / Socket (TCP 回环)
/// </summary>
public class AgentCommandProtocolTests
{
    [Fact]
    public void Command_EncodeDecode_RoundTrip()
    {
        var cmd = new AgentCommand(AgentCommandNames.BalanceInsufficient, new System.Collections.Generic.Dictionary<string, string>
        {
            ["model"] = "deepseek-chat",
            ["from"] = "gpt 4o=pro",       // 含空格 + 等号
            ["remaining"] = "75%额度\n第二行", // 含 % 与换行
        });
        var line = cmd.Encode();
        Assert.StartsWith("@cmd balance_insufficient ", line);

        var decoded = AgentCommand.Decode(line);
        Assert.NotNull(decoded);
        Assert.Equal(AgentCommandNames.BalanceInsufficient, decoded!.Name);
        Assert.Equal("deepseek-chat", decoded.Get("model"));
        Assert.Equal("gpt 4o=pro", decoded.Get("from"));
        Assert.Equal("75%额度\n第二行", decoded.Get("remaining"));
    }

    [Fact]
    public void Command_Decode_Malformed_ReturnsNull()
    {
        Assert.Null(AgentCommand.Decode("普通文本行"));
        Assert.Null(AgentCommand.Decode("@chatbox:{\"type\":\"x\"}")); // 非 @cmd 前缀
        Assert.Null(AgentCommand.Decode("@cmd ")); // 空命令名
    }

    [Fact]
    public void CommandWriter_Reader_TextTransport_RoundTrip()
    {
        // Console.IO 传输 (StringWriter/StringReader 模拟)
        var sw = new StringWriter();
        var commands = new AgentCommandWriter(new AgentRequestWriter(sw));
        commands.Send(AgentCommandNames.ThinkingPageSwitch, ("seq", "3"), ("session", "s1"));
        commands.Send(AgentCommandNames.ModelSwitch, ("from", "glm-4-flash"), ("to", "deepseek-chat"));

        var reader = new AgentCommandReader(new TextReportReader(new StringReader(sw.ToString())));
        var first = reader.ReadCommand();
        Assert.NotNull(first);
        Assert.Equal(AgentCommandNames.ThinkingPageSwitch, first!.Name);
        Assert.Equal("3", first.Get("seq"));

        var second = reader.ReadCommand();
        Assert.NotNull(second);
        Assert.Equal("deepseek-chat", second!.Get("to"));

        // 非命令行透传 (skipped 回调)
        var sw2 = new StringWriter();
        sw2.WriteLine("普通回复文本");
        sw2.WriteLine(new AgentCommand(AgentCommandNames.OutputAppend).Encode());
        var skipped = new System.Collections.Generic.List<ReportEvent>();
        var reader2 = new AgentCommandReader(new TextReportReader(new StringReader(sw2.ToString())));
        var cmd2 = reader2.ReadCommand(ev => skipped.Add(ev));
        Assert.NotNull(cmd2);
        Assert.Single(skipped);
        Assert.Equal(ReportEventKind.Text, skipped[0].Kind);
    }

    [Fact]
    public void CommandReader_SkipsMixedEvents()
    {
        // 流式块 + JSON + 命令混合 — 只取命令
        var sw = new StringWriter();
        var w = new AgentRequestWriter(sw);
        w.WriteStreamBlock("多行", "块内容");
        sw.WriteLine("{\"status\":\"ok\"}");
        new AgentCommandWriter(w).Send(AgentCommandNames.SkillDone, ("skill", "git-helper"), ("exit", "0"));

        var reader = new AgentCommandReader(new TextReportReader(new StringReader(sw.ToString())));
        var cmd = reader.ReadCommand();
        Assert.NotNull(cmd);
        Assert.Equal(AgentCommandNames.SkillDone, cmd!.Name);
        Assert.Equal("git-helper", cmd.Get("skill"));
        Assert.Equal("0", cmd.Get("exit"));
    }

    [Fact]
    public void SharedMemoryTransport_CommandRoundTrip()
    {
        // 共享内存传输 (同进程两视图模拟 agent ↔ 前端)
        const int dataCap = 64 * 1024;
        var mapPath = Path.Combine(Path.GetTempPath(), $"click-agent-test-{Guid.NewGuid():N}.shm");
        if (File.Exists(mapPath)) File.Delete(mapPath);
        try {{
        using var mmf = SharedMemoryChannel.OpenOrCreate(mapPath, dataCap);
        using var writer = new SharedMemoryRequestWriter(mmf, dataCap, ownsFile: false);
        using var reader = new SharedMemoryReportReader(mmf, dataCap, ownsFile: false);

        var commands = new AgentCommandWriter(writer);
        commands.Send(AgentCommandNames.BalanceInsufficient, ("model", "glm-4-flash"), ("remaining", "$1.24"));
        commands.Send(AgentCommandNames.ThinkingEnd, ("summary_length", "42"));

        var cmdReader = new AgentCommandReader(reader);
        var first = cmdReader.ReadCommand();
        Assert.NotNull(first);
        Assert.Equal(AgentCommandNames.BalanceInsufficient, first!.Name);
        Assert.Equal("$1.24", first.Get("remaining"));

        var second = cmdReader.ReadCommand();
        Assert.NotNull(second);
        Assert.Equal("42", second!.Get("summary_length"));
        }}
        finally
        {
            if (File.Exists(mapPath)) File.Delete(mapPath);
        }
    }

    [Fact]
    public async Task SocketTransport_CommandRoundTrip()
    {
        // Socket 传输 (TCP 回环 — 服务端 agent 写, 客户端前端读)
        var port = 47810 + System.Threading.Thread.CurrentThread.ManagedThreadId % 1000;
        using var server = new SocketChannelServer(port);

        var clientTask = Task.Run(() => SocketChannel.Connect("127.0.0.1", port));
        var (sWriter, _) = server.AcceptFrontend();
        var (cWriter, cReader) = await clientTask;

        var commands = new AgentCommandWriter(sWriter);
        commands.Send(AgentCommandNames.ModelSwitch, ("from", "gpt-4o"), ("to", "deepseek-reasoner"), ("reason", "余额不足"));

        var cmdReader = new AgentCommandReader(cReader);
        var cmd = cmdReader.ReadCommand();
        Assert.NotNull(cmd);
        Assert.Equal(AgentCommandNames.ModelSwitch, cmd!.Name);
        Assert.Equal("deepseek-reasoner", cmd.Get("to"));
        Assert.Equal("余额不足", cmd.Get("reason"));

        sWriter.Dispose();
        cWriter.Dispose();
        cReader.Dispose();
    }
}
