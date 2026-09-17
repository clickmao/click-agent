namespace agent.frontendapi;


public enum AskReplyOutcome
{
    /// <summary>答案已交给等待方 (含 cancel → null)。</summary>
    Answered,

    /// <summary>ask_id 未知 (过期/伪造/已被清理) —— 不静默接受。</summary>
    UnknownAsk,

    /// <summary>该 ask_id 已答过 (幂等重放) —— 不重复投递答案。</summary>
    AlreadyAnswered,
}
