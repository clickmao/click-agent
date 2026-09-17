namespace agent.llamacpp;


/// <summary>模型侧身份与特殊 token（闸门规则的数据来源，来自 GET /props；不硬编码任何模型字面量）。</summary>
public sealed record ModelProps(string? BosToken, string? EosToken, int ChatTemplateLength, string? ModelPath);
