namespace agent.intent;


/// <summary>待澄清条目 — 问询请求的图内表达</summary>
public class ClarificationItem
{
    /// <summary>问询类型 flag (程序底层路由用; 与 CredentialRequestKind 语义对齐并扩展)</summary>
    public string Kind { get; set; } = ClarificationKinds.MissingParameter;

    /// <summary>哪个节点的哪个参数</summary>
    public string NodeId { get; set; } = string.Empty;

    public string ParameterName { get; set; } = string.Empty;

    /// <summary>给用户看的问题 (必须具体: 问什么、为什么需要、不填会怎样)</summary>
    public string Question { get; set; } = string.Empty;

    /// <summary>谁有权回答 (复用 agent.userinteraction 语义: RealUserOnly/MainAgentAllowed)</summary>
    public string Authority { get; set; } = "MainAgentAllowed";

    public List<string> SuggestedValues { get; set; } = new();

    /// <summary>答案数据类型约束 (v7.13): 回答必须通过 PromptDataValidator 校验</summary>
    public agent.core.PromptDataType DataType { get; set; } =
        agent.core.PromptDataType.String;

    /// <summary>Choice/MultiChoice 的完整选项列表 (选单选择必须给全所有选项)</summary>
    public List<string> Choices { get; set; } = new();

    /// <summary>批量分组键 (v7.13): 同组问询一次性打包给出, 不一条一条问</summary>
    public string GroupId { get; set; } = string.Empty;
}
