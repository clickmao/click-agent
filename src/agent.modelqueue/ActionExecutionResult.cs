using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;


/// <summary>执行面结果 (有界文本回灌)。</summary>
public sealed class ActionExecutionResult
{
    public bool Ok { get; set; }
    public string Output { get; set; } = string.Empty;
    public int ExitCode { get; set; }
    public long ElapsedMs { get; set; }

    /// <summary>回灌给模型的**有界**文本 (始终非空 —— 空回灌会让模型误判「无结果」而重复调用)。</summary>
    public string Render(int maxBytes)
    {
        var head = Ok ? "ok" : "error";
        var body = Output ?? string.Empty;
        if (body.Length > maxBytes) body = body.Substring(0, maxBytes) + "\n...[truncated]";
        var sb = new StringBuilder();
        sb.Append('[').Append(head).Append(" rc=").Append(ExitCode).Append(" ms=").Append(ElapsedMs).Append("]\n");
        sb.Append(body.Length == 0 ? "(empty output)" : body);
        return sb.ToString();
    }
}
