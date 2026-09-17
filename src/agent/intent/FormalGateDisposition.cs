using agent.config;
using agent.registry;

namespace agent.intent;


/// <summary>闸门处置 (DCR 台账的分类口径 —— 合规/违规/弃权/畸形 四态不可混算)。</summary>
public enum FormalGateDisposition
{
    /// <summary>放行 (未声明形式化义务, 或断言已证毕)。</summary>
    Proceed = 0,

    /// <summary>违规: 断言被反例反驳, 或前提空真(Vacuous) —— 节点不许执行。</summary>
    Violation = 1,

    /// <summary>正确弃权: 可判定片段之外(Unknown) —— 未证明不放行, 但**不计为违规**(外部口径待 T1–T4 对齐)。</summary>
    Abstained = 2,

    /// <summary>契约畸形: 断言残缺/自相矛盾 —— 阻断, 且不追问 LLM(模型不能靠写坏断言绕过闸门)。</summary>
    Malformed = 3,
}
