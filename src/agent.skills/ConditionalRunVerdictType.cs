using System;
using System.Threading;
using System.Threading.Tasks;

namespace agent.skills;


/// <summary>v0.17.2-c: 条件定时判定结果类型。</summary>
public enum ConditionalRunVerdictType
{
    Executed,       // 到期且空闲 → 脚本已执行 (Completed)
    Failed,         // 到期且空闲 → 脚本执行失败 (error 事件/超时/协议违例)
    RefusedBusy,    // 到期后仍有其他 agent 忙, give-up
    RejectedInvalid,// py_compile 拒绝 (未执行)
    Cancelled,
}
