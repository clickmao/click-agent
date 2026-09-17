namespace agent.frontendapi;


/// <summary>approval.respond 的消费面 (R510; 由 FrontendPromptService 实现)。</summary>
public interface IApprovalReplySink
{
    ApprovalReplyOutcome CompleteApproval(string approvalId, bool approved, string? reason);
}
