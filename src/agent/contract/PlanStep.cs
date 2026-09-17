using System.Collections.Generic;

namespace agent.contract;

/// <summary>R1 结构化契约 · 计划步骤（DAG 节点）。write_file 用 Path/Content；run 用 Cmd/ExpectStdout。</summary>
public sealed record PlanStep(
    string Id,
    string Tool,
    string Path,
    string Content,
    string Cmd,
    string ExpectStdout,
    IReadOnlyList<string> DependsOn);
