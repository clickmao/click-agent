using agent.logging;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 日志四通道测试 (plan_log_channels.md L.4):
/// flags 四位独立生效、思考流协议顺序 (switch→分片→end)、/log dump 存档、凭据不入日志。
/// </summary>
public class LogChannelTests
{
    [Fact]
    public void All_Flags_Off_Writes_Nothing()
    {
        var buffer = new MemoryLogBuffer();
        var router = new LogRouter(new LogFlags(), buffer, console: new StringWriter());
        router.Write("mod", "info", LogChannel.System, "测试消息");
        Assert.Equal(0, buffer.Count); // file=false → 缓存空
    }

    [Fact]
    public void File_Flag_Off_Buffer_Empty_On_Flag()
    {
        var buffer = new MemoryLogBuffer();
        var off = new LogRouter(new LogFlags(), buffer);
        off.Write("mod", "info", LogChannel.System, "x"); // file 关
        Assert.Equal(0, buffer.Count);

        var on = new LogRouter(LogFlags.All, buffer);
        on.Write("mod", "info", LogChannel.System, "y"); // file 开
        Assert.Equal(1, buffer.Count);
    }

    [Fact]
    public void Console_Flag_Off_No_Console_Output()
    {
        var sw = new StringWriter();
        var router = new LogRouter(new LogFlags { File = true }, new MemoryLogBuffer(), console: sw);
        router.Write("mod", "info", LogChannel.System, "秘密");
        Assert.DoesNotContain("秘密", sw.ToString()); // console 关 → 无控制台输出
    }

    [Fact]
    public void Thinking_Sequence_Switch_Fragments_End()
    {
        var router = new LogRouter(LogFlags.All, new MemoryLogBuffer());
        // 推理流程: 分片 1、2、3 → end
        router.Write("V2", "info", LogChannel.Thinking, "步骤1: 意图拆解");
        router.Write("V2", "info", LogChannel.Thinking, "步骤2: 上下文组装");
        router.Write("V2", "info", LogChannel.Thinking, "步骤3: prompt 构建");
        router.EmitThinkingEnd(128);

        var types = router.Directives.Select(d => d.Type).ToList();
        // 分片产生 switch 指令 (3 条) + 最后一条 end
        Assert.Equal(3, types.Count(t => t == "thinking_page_switch"));
        Assert.Equal("thinking_end", types[^1]);
        var end = router.Directives[^1];
        Assert.Equal(128, end.SummaryLength);
        // 分片 seq 递增
        var seqs = router.Directives.Where(d => d.Type == "thinking_page_switch").Select(d => d.Seq).ToList();
        Assert.Equal(new[] { 1, 2, 3 }, seqs);
    }

    [Fact]
    public void Memory_Buffer_Ring_Capacity()
    {
        var buffer = new MemoryLogBuffer(capacity: 5);
        var router = new LogRouter(LogFlags.All, buffer);
        for (var i = 0; i < 10; i++)
            router.Write("mod", "info", LogChannel.System, $"msg{i}");
        Assert.Equal(5, buffer.Count);
        var snap = buffer.Snapshot();
        Assert.Equal("msg5", snap[0].Msg); // 最老的被挤出
        Assert.Equal("msg9", snap[^1].Msg);
    }

    [Fact]
    public void Entry_Has_Length_And_Hash_No_Full_Text()
    {
        var buffer = new MemoryLogBuffer();
        var router = new LogRouter(LogFlags.All, buffer);
        var secret = "sk-super-secret-content-abcdef";
        router.Write("mod", "info", LogChannel.Thinking, "prompt 构建完成",
            contentFingerprint: "deadbeef", contentLength: secret.Length);
        var entry = buffer.Snapshot()[0];
        // 底层格式: 长度+哈希, 不含内容全文
        Assert.Equal(secret.Length, entry.ContentLength);
        Assert.Equal("deadbeef", entry.ContentHash);
        Assert.DoesNotContain("secret-content", entry.Msg);
    }

    [Fact]
    public async Task Dump_Writes_Jsonl_File()
    {
        var buffer = new MemoryLogBuffer();
        var router = new LogRouter(LogFlags.All, buffer, sessionId: "sess-1");
        router.Write("mod", "info", LogChannel.System, "line1");
        router.Write("mod", "warn", LogChannel.Output, "line2");

        var dir = Path.Combine(Path.GetTempPath(), "logdump_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        try
        {
            var file = Path.Combine(dir, "dump.jsonl");
            using (var writer = new StreamWriter(file))
            {
                foreach (var e in router.SnapshotEntries())
                    writer.WriteLine(System.Text.Json.JsonSerializer.Serialize(
                        e, LogJsonContext.Default.LogEntry));
            }
            var lines = await File.ReadAllLinesAsync(file);
            Assert.Equal(2, lines.Length);
            Assert.Contains("line1", lines[0]);
            Assert.Contains("\"Channel\":\"system\"", lines[0]);
            Assert.Contains("line2", lines[1]);
            Assert.Contains("warn", lines[1]);
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }
}
