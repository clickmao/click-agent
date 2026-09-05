# 子模块开发计划: TaskPlan 体系归拢 (两套计划合一 + 执行链接线)

> 独立计划文档 — 阅读本文件即可开发, 不需加载全部项目上下文。
> 状态: 待开发 (v7.15 候选) · 前置基线: v7.14 (`953efef`)
>
> **本文档由来**: 用户指令"移除任务计划图 (TaskPlan) 全部归拢到下一步开发计划 (v7.15 候选) 内"。
> 归拢 = 拆散为独立模块文档 + 处置遗留双体系。本文件是**索引与现状裁定**, 各模块细节见 DocRef 链接。

---

## T.1 现状裁定 (2026-09-06 全量搜索核实, 结论可直接引用)

代码库存在**两套并行的任务计划体系**, 且现役主链一条都不跑:

| 体系 | 文件 | 被谁消费 | 裁定 |
|---|---|---|---|
| ① agent.planner (旧) | `src/agent.planner/`: TaskNode.cs (TaskGraph/TaskNode/ITaskPlanner)、TaskPlanner.cs、TaskExecutionEngine.cs | 仅遗留 V1 `IndustrialAgent` (412-422 行); V2 与宿主**零消费** (宿主只注册 IndustrialAgentV2) | **遗留死代码候选** |
| ② TaskPlan (新) | `src/agent/intent/`: TaskPlanBuilder.cs、TaskPlan.cs (PlanNode/TaskParameter/ClarificationItem)、TaskPlanRun.cs; `src/agent/registry/`: NodeExecutionResult.cs (TaskPlanExecutor) | V2 用 IntentDecomposer 拆 subTasks + RunEvidenceGateAsync 问询, 但**从不调 TaskPlanBuilder.Build**; TaskPlanExecutor 生产零构造 (**仅测试调用**) | **已建成未接线** |

补充事实 (同轮核实):
- `TaskPlanRunState.WaitingClarification` 枚举**零赋值** — 死状态 (实际用节点级 AwaitingClarification 表达)
- `TaskPlanRun` 无落盘、无面板消费 — 运行时状态只在执行器内存中
- `docs/plans/v715_dev_plan.taskplan.json` 只是文档, **无任何代码加载入口** (无 Deserialize→TaskPlan 调用点)
- V2 主链现状: `IntentDecomposer.Decompose` → `RunEvidenceGateAsync` (v7.14 步骤1.5) → `AssembleContextAsync` → LLM —
  计划图/执行器整段被跳过

## T.2 归拢决策 (待开发时确认的开放问题标 ⚠)

1. **agent.planner 去留** ⚠: 建议**删除项目** (V1 遗留 + V2 零引用 + 功能被 TaskPlan* 完全覆盖)。
   开发时先 `grep -rn "agent.planner"` 全量复核引用面, 确认测试无依赖后 `git rm -r src/agent.planner` +
   清 DI 注册 (extensions/ServiceCollectionExtensions.cs 168) + 清 V1 IndustrialAgent。
   若 V1 本身也判定遗留, 一并处置 (V1/V2 去留是独立决策, 见 T.4 ⚠)。
2. **TaskPlan* 为唯一计划体系**: 保留 intent/TaskPlan* + registry/TaskPlanExecutor, 删 planner 后双体系消失。
3. **TaskPlanRunState.WaitingClarification**: 删除枚举值或接线 (计划级暂停语义), 二选一, 开发时定 ⚠。
4. **执行链接线 V2 主链**: 现状 subTasks 直接进上下文装配; 接线 = V2 调 `TaskPlanBuilder.Build` 产出计划 →
   `TaskPlanExecutor.ExecuteAsync` 按图执行节点。这是行为变更, 分两步: 先 Build+Execute 并行跑 (影子模式, 只记录不采纳),
   对比结果一致后再切主路 (参考 v7.13.1 VulkanSupport 双判据的保守风格)。

## T.3 模块拆分索引 (本计划归拢后的独立文档)

| 模块 | 独立文档 | 依赖 |
|---|---|---|
| 执行器同层并发化 | [plan_executor_parallel.md](plan_executor_parallel.md) | T.2-4 接线完成后才有并发意义 |
| 节点级重试策略 | [plan_node_retry.md](plan_node_retry.md) | 同上 |
| V2 执行链接线 (影子模式→主路) | **本文 T.2-4 即计划** (不足以独立成文) | 依赖 T.2-1 planner 处置完成 |
| 模型队列 + /balance | [plan_model_queue.md](plan_model_queue.md) | 独立, 不依赖本链 |
| 隔离任务子 agent | [plan_isolated_task.md](plan_isolated_task.md) | 依赖 SessionMemory.GoalProfile (v7.14 ③ 已就绪) |

## T.4 开放问题 (下次开发时必须先确认, 否则上下文断裂)

1. ⚠ V1 IndustrialAgent 是否一并废弃? (宿主已只注册 V2; V1 若废弃, agent.planner 随之删, T.2-1 变简单)
2. ⚠ 影子模式的一致性判据: 计划执行结果与 V2 直连结果"一致"如何定义 (最终回答语义等价? 节点输出逐条对比?)
3. ⚠ 开发计划 JSON (`docs/plans/v715_dev_plan.taskplan.json`) 是否需要代码加载入口
   (如 `TaskPlanBuilder.FromDevPlanJson` → 开发任务也可以被 agent 自己执行)? 当前无入口, 纯文档。
4. ⚠ TaskPlanExecutor 接线后 `/plan` 命令从"回显固定文本"变为输出 TaskPlanRun JSON (面板全 JSON 惯例)。

## T.5 验收标准 (归拢本身)
- [ ] `grep -rn "agent.planner"` 零残留 (删除方案) 或引用边界明确 (保留方案)
- [ ] 单一计划体系: TaskPlan* 唯一, 双体系文档/注释清零
- [ ] WaitingClarification 死状态处置完毕 (删或接线)
- [ ] V2 主链影子模式跑通 1 个多子任务用例, Run 状态可观测 (/plan JSON)
- [ ] 全量测试绿 + AOT 0 警
