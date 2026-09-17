namespace agent.output;


/// <summary>底层消息种类: 一切出口内容 (LLM 结果/问询/日志/审批/错误) 的统一分类</summary>
public enum AgentOutputKind
{
    /// <summary>LLM 最终回答 (经区段管道处理后)</summary>
    Answer,

    /// <summary>问询 (批量澄清/证据补充 — 内部含结构化问题列表)</summary>
    Question,

    /// <summary>执行日志/步骤明细</summary>
    Log,

    /// <summary>敏感操作审批请求</summary>
    Approval,

    /// <summary>错误 (诚实上报, 不伪装成回答)</summary>
    Error,

    /// <summary>状态面板 (/status 等)</summary>
    Status,
}
