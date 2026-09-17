namespace agent.exploration;


/// <summary>思考链收敛原因 (打点 think_converge.reason)。</summary>
public enum ConvergeReason
{
    MultiSourceAgreement,   // 多源一致
    BudgetExhausted,        // 预算/时限耗尽
    NoNewDiscoveries,       // 连续无新发现
    LlmSelfAssessed,        // LLM 自评依据充分
}
