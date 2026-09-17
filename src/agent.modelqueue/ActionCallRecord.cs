using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;


/// <summary>动作环审计记录 (每工具调用一条; 由执行面填充)。</summary>
public sealed class ActionCallRecord
{
    public int Step { get; set; }
    public string Tool { get; set; } = string.Empty;
    public bool Ok { get; set; }
    public int ExitCode { get; set; }
    public long ElapsedMs { get; set; }
    public int OutputBytes { get; set; }
    public string ArgsSha8 { get; set; } = string.Empty;
}
