using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.logging;


/// <summary>前端协议指令 (L.2.2 — JSON 推送, 与 /status 同构)</summary>
public sealed class FrontendDirective
{
    /// <summary>thinking_page_switch / thinking_end</summary>
    public string Type { get; set; } = string.Empty;

    public string? SessionId { get; set; }

    /// <summary>thinking_page_switch: 当前分片 seq; thinking_end: 思考内容总长</summary>
    public int Seq { get; set; }

    /// <summary>thinking_end: 思考摘要长度 (前端折叠展示用)</summary>
    public int SummaryLength { get; set; }
}
