using System;
using System.IO;
using System.Text;

namespace agent.io
{
    /// <summary>TextWriter 实现 (stdout / 文件 / StringWriter)。</summary>
    public sealed class AgentRequestWriter : AgentRequestWriterBase
    {
    private readonly TextWriter _writer;

    public AgentRequestWriter(TextWriter writer) => _writer = writer;

    protected override void WriteLineCore(string line) => _writer.WriteLine(line);
    }
}
