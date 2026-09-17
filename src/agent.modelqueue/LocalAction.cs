using System;
using System.Collections.Generic;

namespace agent.modelqueue;


/// <summary>
/// R479: **本地该做什么** (精准语义) —— 由上游返回校准出的动作类别。
/// 这是「LLM 返回 → 本地动作」的标准化出口; 本地 LLM 与远端 LLM **同用这一个函数**
/// (协议同形 ⇒ 语义同一), 不为本地另立一套判据。
/// </summary>
public enum LocalAction
{
    /// <summary>直接交付正文。</summary>
    Answer,

    /// <summary>执行工具调用 (声明面白名单内) 并回灌。</summary>
    RunTools,

    /// <summary>同一请求值得重发 (输出预算类失效)。</summary>
    Retry,

    /// <summary>不可用但可解释: 必须给用户可见文案, 禁静默空回复。</summary>
    VisibleFailure,

    /// <summary>传输/解析失败: 上层按通道失败处理 (不计入上游判据)。</summary>
    Fatal,
}
