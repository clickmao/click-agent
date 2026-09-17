using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;



// ─────────────────────────────────────────────────────────────────────────────
// R413 前置门 (Local Turn Gate)
// 语义: 每轮先由本地 r1 判定「用户消息是否携带新增诉求」。
//   Pass = 有新增 ⇒ 照常走远端主调用。
//   Skip = 无新增 (纯认可/确认/寒暄/重复) ⇒ 本地消化, 不发远端主调用。
// 判据预注册: docs/plans/v0.35.0-r413-r1-local-verdict-token-budget.md §7 (分母=臂 A)。
// 反空心纪律: 无法解析/失败/记账违规/空回 **一律 Undecided** ⇒ 调用方必须降级远端;
//   「没测到」≠「假」—— 绝不因解析失败而静默跳过 (那是把增益建立在幻觉上)。
// ─────────────────────────────────────────────────────────────────────────────

/// <summary>R413 前置门结论 (真假判别的语义落点)。</summary>
public enum TurnGateVerdict
{
    /// <summary>携带新增诉求 ⇒ 走远端。</summary>
    Pass = 0,

    /// <summary>无新增诉求 ⇒ 本地消化 (跳过远端主调用)。</summary>
    Skip = 1,
}
