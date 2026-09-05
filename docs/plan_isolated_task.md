# 子模块开发计划: 隔离任务 (Isolated Task)

> 独立计划文档 — 阅读本文件即可开发, 不需加载全部项目上下文。
> 状态: 待开发 (v7.15 候选) · 前置基线: v7.14 (`953efef`)

> 由原 plan_taskgraph_and_isolated_task.md 模块 B 独立而成 (用户指令: 每个开发计划隔离单文档)。
> 同源的任务计划执行端缺口见 plan_executor_parallel.md / plan_taskplan_consolidation.md。

---



### I.1 需求 (一句话)
主 agent 执行任务循环中, 用户插入**与当前任务无关的新提问**
(例: 主任务=开发计算器项目, 用户从入口问"帮我查天气"),
判定为无关后**额外开一个隔离边界的子 agent 执行该新任务, 完成后销毁**;
主 agent 的任务计划、会话记忆、agent 画像均不被污染。

### I.2 无关性判定 (纯规则优先, 落点: `src/agent/intent/`)
```
TaskRelevanceChecker.IsRelevant(currentGoalText, incomingMessage) → bool
信号 (打分制, 阈值可配):
- 实体重叠: 当前目标 KeyEntities ∩ 新消息实体 = 0 → 无关 +
- 意图类别: 当前主任务意图 vs 新消息意图, 类别不同且无共享参数 → 无关 +
- 指代依赖: 新消息含"它/这个/刚才/继续"等指代词 → 相关 − (强)
- 显式信号: 新消息含"顺便/另外/帮我查"且与目标无实体重叠 → 无关 +
判定: 无关分数 ≥ 阈值 且 无指代词 → IsolatedTask
```
KeyEntities 来自 SessionMemory.GoalProfile (v7.14 ③ 已就绪) — 这是隔离判定的锚。

### I.3 隔离子 agent 生命周期 (落点: `src/agent/subagent/`)
```csharp
public sealed class IsolatedTaskRunner
{
    // 新建: 独立 Session (独立 SessionId, 空 Memory, 不挂 GoalProfile)
    //        独立 AgentProfile 副本? 不 — 画像按 Uid 持久, 隔离 agent 用一次性 Uid
    // 执行: 复用 V2 处理管道 (意图→上下文→LLM), 数据源禁用 MainSession 关联源
    // 销毁: 任务结束 (成功/失败/取消) → EndSessionAsync + 清理内存态 + 审计日志
    // 上限: 并发隔离任务 ≤ 2 (可配), 超限排队或拒绝 (默认排队)
}
```

### I.4 隔离边界清单 (验收核心)
| 边界 | 要求 |
|---|---|
| 会话 | 独立 SessionId, 主会话历史不进入隔离 agent 上下文 |
| 记忆 | 隔离任务轮次不写主 SessionMemory; 主目标不被改写 |
| 画像 | 隔离任务结果不记入主 agent AgentProfile (用一次性 Uid) |
| 问询 | 隔离任务内问询走静默通道 (SilentInterAgent), 不打断用户主任务交互 |
| 输出 | 结果返回主对话 (带 `IsolatedTask` 标记的 AgentOutputMessage), 不混入主任务计划 |
| 资源 | 结束即销毁: 会话 End + 内存态清空 + 数据目录清理 |

### I.5 验收标准
- [ ] 无关判定测试: 计算器任务中"查天气"→IsolatedTask; "把计算器改成十进制"→相关
- [ ] 隔离测试: 隔离执行后主会话 Memory/Goal/Plan 无变化 (快照对比)
- [ ] 销毁测试: 任务完成 → 会话不存在, 画像无新 Uid 残留
- [ ] 并发上限: 第 3 个隔离任务排队
- [ ] 既有测试全绿 + AOT 0 警

---

---

## 补充 (2026-09-06 核实的新事实, 开发前必读)

- 隔离判定的锚 `SessionMemory.GoalProfile.KeyEntities`: v7.14 (3) 已落地, 但**实体抽取本身目前是规则版**
  (关键词/词性启发), 抽取质量直接决定判定质量 — 开发时如发现误判率高, 优先补实体抽取而非调阈值 [待确认]
- 隔离子 agent 复用 V2 管道: V2 是单例 DI 注册 (agent.host/Program.cs 231), 隔离执行**不能复用同一实例**
  (会话状态/记忆落盘共用会污染) — 需新建 V2 实例或抽无状态执行核心 [待确认] 开发时确认 DI 方案
- 上限排队策略与 InjectedInstruction 的交互: 隔离任务执行中用户再插指令, 归属主任务还是隔离任务?
  建议按消息内实体锚定, 开发时定 [待确认]
