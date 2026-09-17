namespace agent.registry;


/// <summary>
/// v0.23.0-exp12 · S1(M4): 形式化断言契约 —— 执行链第 ② 段「计划 → 节点化 + 逐节点断言」的契约层。
///
/// 设计铁律(可证伪):
///  1) <b>缺失 ≠ 错误</b>: 节点未提供形式化断言 ⇒ NoFormal("absent"), 放行, 且<b>绝不为此追问 LLM</b>
///     (不要求 LLM 返回形式化数据 —— 插件/契约缺失时链必须能继续)。
///  2) <b>显式声明优先</b>: 节点以 no_formal 标记声明「本节点无可判定片段」⇒ NoFormal("declared")。
///  3) <b>残缺不放行</b>: 有断言意图但 premise/goal 不齐、裸关键字、或与 no_formal 自相矛盾 ⇒ Malformed,
///     不放行、不静默吞、不追问(模型不能靠"写坏断言"绕过闸门)。
///  4) <b>零 token / 零 shell / 零反射</b>: 本层只做语法与义务判定, 数学裁决交 agent.rover 内核
///     (`agent.rover check <file.assert>`), 语法与之严格同构。
///  5) 任何分支都不得触发 LLM 重试(<see cref="FormalContractResult.RequiresLlmRetry"/> 恒为 false)。
/// </summary>
public enum FormalContractDecision
{
    /// <summary>premise/goal 齐备 ⇒ 交 agent.rover 内核裁决(本地, 零 token)。</summary>
    Assertion = 0,

    /// <summary>本次不提供形式化断言(缺失或显式声明) ⇒ 放行; 不追问 LLM。</summary>
    NoFormal = 1,

    /// <summary>有断言意图但残缺/自相矛盾 ⇒ 不放行(不静默吞), 亦不追问 LLM。</summary>
    Malformed = 2,
}
