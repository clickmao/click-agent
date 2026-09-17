using System.Text;
using System.Text.Json;

namespace agent.frontendapi;


/// <summary>approval.respond 的解析结果 (approved=true 批准, false 拒绝; Cancel 仅用于语义封口)。</summary>
public sealed record ApprovalReply(string ApprovalId, bool Approved, string? Reason, bool Cancel);
