using System.Text;
using System.Linq;

namespace agent.intent;


/// <summary>
/// 出站文本扣减结果 (v0.22.0 exp9 D4b)。
/// Failure 分支一律**返回原文**: 宁可多发一点给模型, 绝不改坏用户原话。
/// </summary>
public sealed record AblationResult(
    bool Applied,
    string Text,
    int RemovedChars,
    IReadOnlyList<string> RemovedClauses,
    string? AbortReason)
{
    public static AblationResult NotApplied(string text, string reason, IReadOnlyList<string>? clauses = null) =>
        new(false, text, 0, clauses ?? [], reason);
}
