using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace agent.io
{

/// <summary>
/// Agent 输出事件类型 (读侧分类)。
/// </summary>
public enum ReportEventKind
{
    /// <summary>普通文本行 (agent 回复/CLI 提示)</summary>
    Text,

    /// <summary>chatbox 前端指令行 (@chatbox:{json} — thinking_page_switch/分片/thinking_end/output_append)</summary>
    ChatboxDirective,

    /// <summary>流式块开始 (@stream begin …)</summary>
    StreamBegin,

    /// <summary>流式块数据行 (块内多行原文 — 逐行原样透传)</summary>
    StreamChunk,

    /// <summary>流式块结束 (@stream end)</summary>
    StreamEnd,

    /// <summary>JSON 结构化结果行 (以 { 开头且解析成功的单行 — /status /balance /plan 等)</summary>
    Json,

    /// <summary>输入流结束 (stdin EOF / agent 退出)</summary>
    Eof,
}

/// <summary>读出的事件 (kind + 原文载荷)</summary>
public sealed class ReportEvent
{
    public ReportEventKind Kind { get; set; }

    /// <summary>载荷: Text=整行 / ChatboxDirective=去前缀后的 json / StreamChunk=块内一行 / Json=整行</summary>
    public string Payload { get; set; } = string.Empty;
}

/// <summary>
/// Agent 输出读取基类 (需求2): 前端每次 Console.ReadLine() 拿 agent 一行输出,
/// 本基类把"一行"聚合为语义事件 — 单行协议 (指令/JSON) 与多行流式块 (定界符包裹)。
///
/// 行协议 (与 agent.logging.ConsoleChatboxSink 及 host 输出契约一致):
///   @chatbox:{json}          → ChatboxDirective (单行)
///   @stream begin            → StreamBegin (其后进入块模式)
///   块内任意行               → StreamChunk (逐行原样)
///   @stream end              → StreamEnd
///   { 开头且单行合法 JSON    → Json (快速解析: 仅查首字符 + 尾字符配对, 不引 JSON 库)
///   其他                     → Text
///
/// 实现子类只需覆盖数据来源 (TextReader / 内存行列表 / 网络流), 解析逻辑全部在本基类
/// (ReadEvent 状态机) — 满足"多写一个完善的 AgentReportReaderBase 基类并实现不同内容读取"。
/// </summary>
public abstract class AgentReportReaderBase
{
    /// <summary>chatbox 指令行前缀 (与 ConsoleChatboxSink 写侧一致)</summary>
    public const string ChatboxPrefix = "@chatbox:";

    public const string StreamBeginMarker = "@stream begin";
    public const string StreamEndMarker = "@stream end";

    private bool _inStreamBlock;

    /// <summary>数据源: 读一行 (不含行尾)。null = 流结束。</summary>
    protected abstract string? ReadLineCore();

    /// <summary>读下一个语义事件 (阻塞直到拿到一个完整事件或流结束)。</summary>
    public ReportEvent? ReadEvent()
    {
        var line = ReadLineCore();
        if (line is null)
            return new ReportEvent { Kind = ReportEventKind.Eof, Payload = string.Empty };

        // 流式块状态机 (跨行状态)
        if (_inStreamBlock)
        {
            if (line.Equals(StreamEndMarker, StringComparison.Ordinal))
            {
                _inStreamBlock = false;
                return new ReportEvent { Kind = ReportEventKind.StreamEnd, Payload = string.Empty };
            }
            return new ReportEvent { Kind = ReportEventKind.StreamChunk, Payload = line };
        }

        if (line.Equals(StreamBeginMarker, StringComparison.Ordinal))
        {
            _inStreamBlock = true;
            return new ReportEvent { Kind = ReportEventKind.StreamBegin, Payload = string.Empty };
        }

        // chatbox 指令 (单行 JSON)
        if (line.StartsWith(ChatboxPrefix, StringComparison.Ordinal))
            return new ReportEvent
            {
                Kind = ReportEventKind.ChatboxDirective,
                Payload = line.Substring(ChatboxPrefix.Length),
            };

        // 单行 JSON (快速启发: 首尾大括号配对 — 不引 JSON 库, 零依赖 + 快速解析)
        if (IsLikelySingleLineJson(line))
            return new ReportEvent { Kind = ReportEventKind.Json, Payload = line };

        return new ReportEvent { Kind = ReportEventKind.Text, Payload = line };
    }

    /// <summary>读到流结束, 返回全部事件。</summary>
    public List<ReportEvent> ReadAll()
    {
        var events = new List<ReportEvent>();
        ReportEvent? e;
        while ((e = ReadEvent()) != null && e.Kind != ReportEventKind.Eof)
            events.Add(e);
        return events;
    }

    /// <summary>聚合下一个流式块 (从 StreamBegin 到 StreamEnd 的全部行)。非块事件返回 null。</summary>
    public List<string>? ReadStreamBlock()
    {
        var e = ReadEvent();
        if (e is null || e.Kind != ReportEventKind.StreamBegin)
            return null;
        var lines = new List<string>();
        while (true)
        {
            var chunk = ReadEvent();
            if (chunk is null || chunk.Kind == ReportEventKind.Eof)
                break;
            if (chunk.Kind == ReportEventKind.StreamEnd)
                break;
            if (chunk.Kind == ReportEventKind.StreamChunk)
                lines.Add(chunk.Payload);
        }
        return lines;
    }

    /// <summary>快速单行 JSON 判定: { 开头 } 结尾且长度 ≥2 (前端 fast-path — 完整校验交给 JSON 库)。</summary>
    protected static bool IsLikelySingleLineJson(string line)
    {
        var trimmed = line.Trim();
        return trimmed.Length >= 2 && trimmed[0] == '{' && trimmed[trimmed.Length - 1] == '}';
    }
}

/// <summary>TextReader 数据源实现 (stdin / 文件 / StringReader 均可)。</summary>
public sealed class TextReportReader : AgentReportReaderBase
{
    private readonly TextReader _reader;

    public TextReportReader(TextReader reader) => _reader = reader;

    protected override string? ReadLineCore() => _reader.ReadLine();
}
}
