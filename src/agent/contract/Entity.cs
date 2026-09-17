namespace agent.contract;

/// <summary>R1 结构化契约 · 实体项（请求原文里出现的具体路径/符号/命令/取值/语言）。</summary>
public sealed record Entity(string Kind, string Value);
