namespace agent.contextgradient;


/// <summary>梯度层级 (L0 全文 → L3 仅标题)</summary>
public enum GradientLevel
{
    /// <summary>L0: 全文保留 (相关性 ≥ 0.8)</summary>
    Full,

    /// <summary>L1: 首段+要点句保留 (0.5-0.8)</summary>
    SummarySentences,

    /// <summary>L2: 规则压缩 — 去空行/去重复/截断到预算 (0.3-0.5)</summary>
    RuleCompressed,

    /// <summary>L3: 仅保留首行标题/来源标识 (&lt; 0.3)</summary>
    TitleOnly,
}
