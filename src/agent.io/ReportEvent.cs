using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace agent.io
{
    /// <summary>读出的事件 (kind + 原文载荷)</summary>
    public sealed class ReportEvent
    {
    public ReportEventKind Kind { get; set; }

    /// <summary>载荷: Text=整行 / ChatboxDirective=去前缀后的 json / StreamChunk=块内一行 / Json=整行</summary>
    public string Payload { get; set; } = string.Empty;
    }
}
