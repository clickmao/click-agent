using System.Collections.Generic;

namespace agent.contract;

/// <summary>R1 结构化契约 · 歧义项：原文片段 + 问题 + 2-4 个互斥选项。非空 ⇒ 管道必须停下要澄清。</summary>
public sealed record Ambiguity(string Span, string Issue, IReadOnlyList<string> Options);
