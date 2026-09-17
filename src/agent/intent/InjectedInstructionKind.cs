using System.Text.Json.Serialization;

namespace agent.intent;


/// <summary>插入指令语义分级</summary>
public enum InjectedInstructionKind
{
    /// <summary>停止/取消: 立即中断当前节点与计划 (敏感词判定 + 显式指令)</summary>
    Cancel,

    /// <summary>敏感暂停请求: 用户要求在危险步骤前停下确认</summary>
    RequestApproval,

    /// <summary>新子任务: 拆解后合并进运行中的图 (新节点 + 依赖接线)</summary>
    NewTask,

    /// <summary>参数补充: 直接答复等待中的问询节点</summary>
    ClarificationAnswer,

    /// <summary>约束修改: 改变未开始节点的执行方式 (如 "别用 npm 用 pnpm")</summary>
    ConstraintUpdate,
}
