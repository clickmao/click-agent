namespace agent.core;


/// <summary>操作审批结果</summary>
public class OperationApprovalResult
{
    public bool Approved { get; init; }
    public PromptAnswerSource AnsweredBy { get; init; }
    public string? Reason { get; init; }
}
