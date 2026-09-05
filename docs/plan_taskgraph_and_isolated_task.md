# 子模块开发计划: 依赖拓扑任务图 × 隔离任务

> 独立计划文档 — 阅读本文件即可开发, 不需加载全部项目上下文。
> 状态: 待开发 (v7.15 候选) · 前置基线: v7.14 (`953efef`)

---

## 模块 A: TaskPlanBuilder 依赖拓扑图 (Level 分层 + ParallelGroup 并行组)

### A.1 需求 (一句话)
`TaskPlanBuilder.Build` 拆出子任务后, 依据 `SubTask.Dependencies` 把平面任务列表
重组为**依赖拓扑图**: 同层无依赖关系的子任务构成 `ParallelGroup` 可并发执行,
跨层按 `Level` 顺序执行并等待上游完成。

### A.2 数据模型 (落点: `src/agent/intent/TaskPlanModel.cs`)
```csharp
// TaskPlan 新增:
public IReadOnlyList<PlanLevel> Levels { get; }        // Level 分层结果
public int MaxParallelism { get; }                      // 并行上限 (默认 4)

// PlanLevel:
public sealed record PlanLevel(
    int Level,                          // 0 = 无依赖入口层
    IReadOnlyList<PlanNode> Nodes);     // 同层节点 (ParallelGroup)

// PlanNode 新增 (已有 Dependencies 基础上):
public int Level { get; }               // 拓扑层号
public bool IsInParallelGroup { get; }  // 同层节点数 > 1 时为 true
```

### A.3 拓扑分层算法 (TaskPlanBuilder 内新私有方法)
```
输入: List<SubTask> (含 Dependencies: 子任务索引列表)
1. Kahn 入度计算 → 每轮收集入度=0 的节点 = 同一 Level
2. 层号 = max(上游层号)+1
3. 环检测: 分层结束后仍有剩余节点 → 抛 PlanTopologyException (带环路径)
4. 同层节点数 > 1 → 标记 IsInParallelGroup
```
纯规则、零 LLM、微秒级; 复杂度 O(V+E)。

### A.4 执行语义 (落点: `TaskPlanExecutor.ExecuteAsync`)
```
for level in plan.Levels (顺序):
    并发组 (IsInParallelGroup):
        按节点并行触发 (同层互不依赖), 上层全部完成才开始本层
        单节点失败策略: 沿用现有 (skip 下游 / 计划级失败)
    串行节点: 现有逐节点逻辑不变
等待原语: Task.WhenAll (并行组), 现有节点间依赖检查 (串行)
```

### A.5 验收标准
- [ ] 拓扑分层测试: 线性链 → 全串行; 扇出/扇入 → 正确分组; 环 → PlanTopologyException
- [ ] 并行组执行测试: 同层两节点并发执行 (执行时间叠加 < 串行和), 上游失败 → 本层跳过
- [ ] MaxParallelism 截断: 并行度上限生效
- [ ] 既有 206+ 测试全绿, AOT 0 警 (无反射/无动态生成)

---

## 模块 B: 隔离任务 (Isolated Task — 无关新提问的隔离执行)

### B.1 需求 (一句话)
主 agent 执行任务循环中, 用户插入**与当前任务无关的新提问**
(例: 主任务=开发计算器项目, 用户从入口问"帮我查天气"),
判定为无关后**额外开一个隔离边界的子 agent 执行该新任务, 完成后销毁**;
主 agent 的任务计划、会话记忆、agent 画像均不被污染。

### B.2 无关性判定 (纯规则优先, 落点: `src/agent/intent/`)
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

### B.3 隔离子 agent 生命周期 (落点: `src/agent/subagent/`)
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

### B.4 隔离边界清单 (验收核心)
| 边界 | 要求 |
|---|---|
| 会话 | 独立 SessionId, 主会话历史不进入隔离 agent 上下文 |
| 记忆 | 隔离任务轮次不写主 SessionMemory; 主目标不被改写 |
| 画像 | 隔离任务结果不记入主 agent AgentProfile (用一次性 Uid) |
| 问询 | 隔离任务内问询走静默通道 (SilentInterAgent), 不打断用户主任务交互 |
| 输出 | 结果返回主对话 (带 `IsolatedTask` 标记的 AgentOutputMessage), 不混入主任务计划 |
| 资源 | 结束即销毁: 会话 End + 内存态清空 + 数据目录清理 |

### B.5 验收标准
- [ ] 无关判定测试: 计算器任务中"查天气"→IsolatedTask; "把计算器改成十进制"→相关
- [ ] 隔离测试: 隔离执行后主会话 Memory/Goal/Plan 无变化 (快照对比)
- [ ] 销毁测试: 任务完成 → 会话不存在, 画像无新 Uid 残留
- [ ] 并发上限: 第 3 个隔离任务排队
- [ ] 既有测试全绿 + AOT 0 警

---

## 开发顺序建议
1. 模块 A (拓扑图) — 纯算法, 无外部依赖, 先行
2. 模块 B (隔离任务) — 依赖 B.2 的实体锚 (③ GoalProfile), 后行
3. 两模块共用: TaskPlanBuilder 变更集中在一个 PR; docs/task_loop.md 同步执行语义

## 不做 (明确排除)
- 隔离 agent 不做持久化画像学习 (一次性 Uid, 防 profile 污染)
- 拓扑图不做运行时动态重排 (拆解时静态分层; 动态重排列入远期)
