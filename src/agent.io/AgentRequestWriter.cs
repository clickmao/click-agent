using System;
using System.IO;
using System.Text;

namespace agent.io
{

/// <summary>
/// Agent 请求写入基类 (需求2: "将其他给 agent 输入的部分抽象成 AgentRequestWriterBase"):
/// 面向 agent 的单行指令/消息写入 — 前端每次输入一整行, writer 负责按协议写出。
/// 写侧协议与读侧对称: 普通行直写; 流式内容用 @stream begin/end 定界包裹。
/// </summary>
public abstract class AgentRequestWriterBase
{
    /// <summary>写一行 (含行尾)。</summary>
    protected abstract void WriteLineCore(string line);

    /// <summary>写一条用户指令/消息 (单行直写 — 契约: 载荷内不得含换行; 有换行时转流式块)。</summary>
    public void WriteRequest(string message)
    {
        if (message is null)
            return;
        if (message.IndexOf('\n') >= 0)
        {
            // 多行载荷 → 流式块包裹 (读侧 ReadStreamBlock 聚合)
            WriteStreamBlock(message.Split('\n'));
            return;
        }
        WriteLineCore(message);
    }

    /// <summary>写一个流式块 (多行原文 — agent/前端间传递多行内容的标准通道)。</summary>
    public void WriteStreamBlock(params string[] lines)
    {
        WriteLineCore(AgentReportReaderBase.StreamBeginMarker);
        foreach (var line in lines ?? Array.Empty<string>())
            WriteLineCore(line ?? string.Empty);
        WriteLineCore(AgentReportReaderBase.StreamEndMarker);
    }

    /// <summary>写一条 chatbox 事件 (agent → 前端方向; 供测试/回放使用对称写法)。</summary>
    public void WriteChatboxDirective(string json) =>
        WriteLineCore(AgentReportReaderBase.ChatboxPrefix + json);
}

/// <summary>TextWriter 实现 (stdout / 文件 / StringWriter)。</summary>
public sealed class AgentRequestWriter : AgentRequestWriterBase
{
    private readonly TextWriter _writer;

    public AgentRequestWriter(TextWriter writer) => _writer = writer;

    protected override void WriteLineCore(string line) => _writer.WriteLine(line);
}
}
