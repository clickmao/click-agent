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

    /// <summary>统一命令行 (@cmd name key=value … — v0.11.0 统一命令协议)</summary>
    Command,

    /// <summary>输入流结束 (stdin EOF / agent 退出)</summary>
    Eof,
    }
}
