using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using agent.config;
using agent.registry;
using agent.skills;

namespace agent.intent;


/// <summary>
/// 计划事件名 (v0.22.0 exp9 D5) —— 前端按事件名订阅; 载荷是手写 JSON (零反射, AOT 安全)。
/// </summary>
public static class PlanEvents
{
    /// <summary>计划已创建 (意图进入即公告: 子任务细分 + 每步位置, 不等模型生成完)</summary>
    public const string Created = "plan.created";

    /// <summary>单节点落终态 (位置/执行器/耗时/token/产物)</summary>
    public const string Node = "plan.node";

    /// <summary>计划收口 (本地先行/重叠/汇总计数)</summary>
    public const string Finished = "plan.finished";
}
