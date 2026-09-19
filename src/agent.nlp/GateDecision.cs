namespace agent.nlp;

/// <summary>闸判定结果。AllowLocal=true ⇒ 本地消化, 不起远端; false ⇒ 升级 LLM (codex 流程)。</summary>
public readonly record struct GateDecision(bool AllowLocal, string Basis, string Signature);
