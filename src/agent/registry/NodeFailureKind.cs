using agent.intent;
using agent.core;

namespace agent.registry;


/// <summary>单个节点的执行结果</summary>
/// <summary>失败种类 (v7.15 重试策略): 决定节点失败是否值得重试。</summary>
public enum NodeFailureKind
{
    /// <summary>未失败</summary>
    None,

    /// <summary>瞬态失败 (网络/超时/LLM 5xx) — 可重试 (默认保守分类)</summary>
    Transient,

    /// <summary>永久失败 (参数校验/敏感拒绝/逻辑错误) — 重试无意义</summary>
    Permanent,
}
