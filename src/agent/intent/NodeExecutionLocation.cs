namespace agent.intent;


/// <summary>
/// 节点执行位置 (v0.22.0 exp9 D1)。用户口径: "查看哪个步骤可以直接本地跑, 哪个任务需要远程生成,
/// 远程生成后如果是文本处理任务就可以本地先跑起来等待其他远端任务执行 (如果没有依赖的话)"。
///
/// Remote: 必须远程生成 (LLM) —— 本地无生成能力。
/// Local : 本地确定性执行器可独立完成 —— 零 LLM 调用 / 零 token。
/// Hybrid: 远程生成 + 本地立即跑/验 (同一节点两段; 第二段不新增 LLM 调用)。
///
/// 判定归 PlanRoutePolicy (确定性表, 非 LLM 自述); 字段由路由写回, 不许上游手填。
/// </summary>
public enum NodeExecutionLocation
{
    /// <summary>远程生成 (模型)</summary>
    Remote = 0,

    /// <summary>本地执行 (零 token)</summary>
    Local = 1,

    /// <summary>远程生成 + 本地立即处理 (零 token 第二段)</summary>
    Hybrid = 2,
}
