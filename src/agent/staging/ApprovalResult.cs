using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace agent.staging;


/// <summary>审批应用结果 (结构化, 供指令渲染与前端)。</summary>
public sealed class ApprovalResult
{
    public string BatchId { get; init; } = "";
    public bool FullyApplied { get; init; }
    public string? Note { get; init; }
    public int AppliedCount { get; init; }
    public int ConflictCount { get; init; }
    public List<string> Conflicts { get; init; } = new(); // 冲突文件 (用户已改 → 未覆盖)
    public List<string> Applied { get; init; } = new();

    public string Render()
    {
        if (Note is not null) return Note;
        var sb = new StringBuilder();
        if (AppliedCount > 0) sb.Append($"✓ 已应用 {AppliedCount} 项: {string.Join(", ", Applied.Select(p => Path.GetFileName(p)))}");
        if (ConflictCount > 0)
        {
            if (sb.Length > 0) sb.Append("; ");
            sb.Append($"⚠ {ConflictCount} 项冲突未覆盖 (目标已被修改, 为保护你的编辑): {string.Join(", ", Conflicts.Select(Path.GetFileName))}");
            sb.Append(" → 请人工合并后 /reject 本批 或 /staged diff 查看内容");
        }
        if (AppliedCount == 0 && ConflictCount == 0) sb.Append("(无变更)");
        return sb.ToString();
    }
}
