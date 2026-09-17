namespace agent.frontendapi;


/// <summary>approval.respond 的结果 (Applied=已投递到等待中的审批; 未知/重复 = 显式拒绝, 不静默)。</summary>
public enum ApprovalReplyOutcome
{
    Applied,
    UnknownApproval,
    AlreadyAnswered,
}
