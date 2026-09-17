using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace agent.io
{
    /// <summary>TextReader 数据源实现 (stdin / 文件 / StringReader 均可)。</summary>
    public sealed class TextReportReader : AgentReportReaderBase
    {
    private readonly TextReader _reader;

    public TextReportReader(TextReader reader) => _reader = reader;

    protected override string? ReadLineCore() => _reader.ReadLine();
    }
}
