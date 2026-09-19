namespace agent.nlp;

/// <summary>闸族系的输入特征 — 全部来自成熟 NLP 库输出 (语言标签 + 多语言分词), 无任何词表。</summary>
public readonly record struct GateFeatures(string Language, int TokenCount, string Signature);
