using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;


/// <summary>Responses 输入项种类 (协议层 typed item; 不把一切塞进一段文本)。</summary>
public enum ResponsesItemKind
{
    /// <summary>对话消息 (role + content[])。用户输入 = 独立字段, 不与本地指示混写。</summary>
    Message,

    /// <summary>工具执行结果回灌 (call_id + output), 独立 item。</summary>
    FunctionCallOutput,
}
