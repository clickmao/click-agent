using System;
using System.Collections.Generic;
using System.Text.Json;

namespace agent.skills;


/// <summary>
/// v0.17.2-b (R337, 用户钦定): 脚本插件事件类型 — 插件脚本 stdout **JSON Lines 事件流**的 type 字段。
/// 权威协议: docs/plans/v0.17.2-activity-script-plan.md §2。
/// </summary>
public enum ScriptPluginEventType
{
    Progress,
    Checkpoint,
    Heartbeat,
    Done,
    Error,
}
