using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.logging;


/// <summary>日志四位 flags (L.2.1 — 每条日志按 flags 一条路径路由, 不允许分叉实现)</summary>
public struct LogFlags
{
    /// <summary>显示到控制台</summary>
    public bool Console { get; set; }

    /// <summary>显示到 chatbox 思考页</summary>
    public bool ChatboxThinking { get; set; }

    /// <summary>显示到 chatbox 输出页</summary>
    public bool ChatboxOutput { get; set; }

    /// <summary>记录到日志 (缓存+存档文件)</summary>
    public bool File { get; set; }

    public static LogFlags All => new()
    {
        Console = true, ChatboxThinking = true, ChatboxOutput = true, File = true,
    };
}
