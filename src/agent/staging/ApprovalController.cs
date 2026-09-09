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

/// <summary>
/// v0.17.1 (R335): ApprovalController — 审批应用/拒绝/diff。apply = LockedFileWriter.WriteIf:
/// 锁内比对当前文件 sha256 == 批次基线 (用户未动过 → 原子写); 不等 → 冲突拒绝**绝不覆盖**
/// (Q1 VS Code 用户正在编辑场景的机械保证 — 基线在批次创建时固化, 应用时任何外部修改都显形)。
/// 多批次 (Q6): /approve all 按 CreatedUnixMs 升序逐批; 批 A 应用后 B 的基线过期 → B 冲突 → partial
/// (不静默覆盖, 报告人工合并)。冲突教训入 ExecutorLessonMemory (频率加权提示)。
/// </summary>
public sealed class ApprovalController
{
    private readonly StagedFileStore _store;

    public ApprovalController(StagedFileStore store) => _store = store;

    /// <summary>应用一批。返回结构化结果; 冲突项 Applied=false, 批次状态 → partial (全成 → approved)。</summary>
    public ApprovalResult Apply(string batchId)
    {
        var batch = _store.Find(batchId);
        if (batch is null) return new ApprovalResult { BatchId = batchId, FullyApplied = false, Note = $"批次 {batchId} 不存在 (/staged 查看)。" };
        if (!batch.IsPending) return new ApprovalResult { BatchId = batchId, FullyApplied = false, Note = $"批次 {batchId} 状态 {batch.Status}, 不可应用。" };

        var applied = new List<string>();
        var conflicts = new List<string>();
        foreach (var item in batch.Items.Where(i => !i.Applied))
        {
            var target = item.Path;
            var dir = Path.GetDirectoryName(Path.GetFullPath(target));
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);

            var nowSha = StagingSha.OfFile(target);
            var ok = agent.execution.LockedFileWriter.WriteIf(target,
                _store.ReadItemContent(item),
                existing =>
                {
                    // existing 可能为 null? WriteIf 只读已存在文件; 新建场景目标不存在 → existing null → 允许
                    var cur = StagingSha.OfFile(target); // 锁内重读哈希 (与 existing 同刻)
                    return item.BaselineSha.Length == 0 && cur.Length == 0 // 新建语义: 目标仍不存在
                           || item.BaselineSha.Length > 0 && cur == item.BaselineSha; // 覆盖语义: 未被外部改
                },
                TimeSpan.FromSeconds(5));

            if (ok.Success && !ok.Merged)
            {
                item.Applied = true;
                applied.Add(target);
            }
            else
            {
                conflicts.Add(target);
                agent.execution.ExecutorLessonMemory.Default.Record(
                    $"staging-conflict:{Path.GetFileName(target)}",
                    $"审批应用冲突: {target} 在批次创建后被外部修改 (VS Code 编辑等), 已拒绝覆盖",
                    "先人工合并该文件, 或 /reject 批次后重产出",
                    $"batch {batchId} apply conflict on {Path.GetFileName(target)}");
            }
        }

        var result = new ApprovalResult
        {
            BatchId = batchId,
            AppliedCount = applied.Count,
            ConflictCount = conflicts.Count,
            Conflicts = conflicts,
            Applied = applied,
            FullyApplied = conflicts.Count == 0 && applied.Count == batch.Items.Count,
        };
        _store.UpdateStatus(batchId, result.FullyApplied ? "approved"
            : applied.Count > 0 ? "partial" : "rejected");
        return result;
    }

    public void Reject(string batchId) => _store.UpdateStatus(batchId, "rejected");

    /// <summary>列出渲染 (指令 /staged)。includeJson: 输出 JSON 行供前端解析。</summary>
    public string ListPending(string? includeJson = null)
    {
        _store.ScanExpiry();
        var all = _store.All();
        var sb = new StringBuilder();
        if (includeJson == "--json")
        {
            // 单行 JSON: 前端直接取得批次+文件清单+staging 内容路径 (Q5)
            var sbj = new StringBuilder();
            sbj.Append("{\"batches\":[");
            var first = true;
            foreach (var b in all)
            {
                if (!first) sbj.Append(',');
                first = false;
                sbj.Append("{\"id\":\"").Append(b.Id)
                   .Append("\",\"status\":\"").Append(b.Status)
                   .Append("\",\"source\":\"").Append(b.Source)
                   .Append("\",\"created\":").Append(b.CreatedUnixMs)
                   .Append(",\"items\":[");
                var f2 = true;
                foreach (var it in b.Items)
                {
                    if (!f2) sbj.Append(',');
                    f2 = false;
                    sbj.Append("{\"path\":\"").Append(JsonEsc(it.Path))
                       .Append("\",\"content_file\":\"").Append(JsonEsc(it.ContentFile))
                       .Append("\",\"applied\":").Append(it.Applied ? "true" : "false").Append('}');
                }
                sbj.Append("]}");
            }
            sbj.Append("]}");
            return sbj.ToString();
        }
        var pending = all.Where(b => b.IsPending).ToList();
        if (pending.Count == 0)
        {
            var others = all.Where(b => !b.IsPending).ToList();
            return others.Count > 0
                ? $"无待审批批次 (历史: {string.Join(", ", others.Select(b => $"{b.Id}[{b.Status}]"))})"
                : "无变更批次。";
        }
        sb.Append($"📋 待审批变更批次 ({pending.Count}):\n");
        foreach (var b in pending)
        {
            var age = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() - b.CreatedUnixMs;
            sb.Append($"- {b.Id} [{b.Source}] {age / 3600000}h前, {b.Items.Count} 文件: ")
              .Append(string.Join(", ", b.Items.Select(i => System.IO.Path.GetFileName(i.Path))))
              .Append('\n');
        }
        sb.Append("→ /approve <id|all> 应用 · /reject <id> 丢弃 · /staged diff <id> 查看内容");
        return sb.ToString();
    }

    public string Diff(string batchId)
    {
        var b = _store.Find(batchId);
        if (b is null) return $"批次 {batchId} 不存在 (/staged 查看)。";
        var sb = new StringBuilder($"📄 批次 {b.Id} [{b.Status}] {b.Items.Count} 文件:\n");
        foreach (var it in b.Items)
        {
            sb.Append($"\n── {it.Path} (baseline {it.BaselineSha[..Math.Min(8, it.BaselineSha.Length)]}, {(it.Applied ? "已应用" : "待应用")}) ──\n");
            sb.Append(_store.ReadItemContent(it));
            sb.Append('\n');
        }
        return sb.ToString();
    }

    private static string JsonEsc(string s)
        => s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n").Replace("\r", "\\r");
}
