using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;


/// <summary>Responses 输出项 (解析后; 只保留校准所需字段)。</summary>
public sealed class ResponsesOutputItem
{
    public string Type { get; set; } = string.Empty;

    public string Text { get; set; } = string.Empty;

    public string Name { get; set; } = string.Empty;

    public string ArgumentsJson { get; set; } = string.Empty;

    public string CallId { get; set; } = string.Empty;
}
