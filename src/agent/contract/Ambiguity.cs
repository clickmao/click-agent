using System.Collections.Generic;

namespace agent.contract;

/// <summary>R1 结构化契约 · 歧义项：原文片段 + 问题 + 2-4 个互斥选项 + 采用解读（chosen ∈ options）。
/// R536 起**不阻塞管道**：管道按 chosen 解读继续（缺信息走 missing_slots 才是停链路径）。</summary>
public sealed record Ambiguity(string Span, string Issue, IReadOnlyList<string> Options, string Chosen);
