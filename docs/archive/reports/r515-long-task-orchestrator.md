# R515 · 长任务编排器 V1（TaskOrchestrator）— 实现 + 同窗对照

> 起因（用户裁定）：R511 已机检「长任务失败第一主因 = 单次动作环步数封顶（默认 6 / 硬顶 32）」；本轮把**节点 = 一次真实执行单元**落地，使总步数 = 节点数 × 单节点预算。
> 轮号说明：本侧原用 R514，但 10:29:38 兄弟会话（cron 30 分节拍）已提交 `be8e74c`「R514: 夹具自检器具化」占用该号 ⇒ 按撞号纪律改号 **R515**。

## 1. 交付物（全部真入仓）

| 件 | 说明 |
| --- | --- |
| `src/agent/intent/TaskOrchestrator.cs` | 编排器：节点=一次真实执行单元；每节点独立步数预算；同层本地/远端并发；逐节点墙钟遥测（`ElapsedMs`/`OverlapMs`）与预算上界 `BudgetCeiling`；检查点复用 `TaskPlanExecutor` |
| `src/agent/intent/TaskPlanFile.cs` | 计划文件 DSL（`id \| 依赖 \| 位置 \| 执行器 \| 文本`，只切前 4 个 `\|`）+ 层级机算 + fail-closed 校验（字段数/id 唯一/依赖存在/成环/local 无执行器/remote 带执行器/空计划）+ `.json` 走既有零反射上下文 |
| `src/agent.host/OrchestrateCommand.cs` | `--orchestrate <计划>`（`--node-steps/--max-nodes/--workspace/--session/--report`）；节点提示词注入上游产出 + 工作区根 + 本节点预算；**逐节点产物归属**（快照差分）；`report.json`；rc 0/1/2 |
| `src/agent.tests/TaskOrchestratorTests.cs` | 21 用例全绿 |
| `eval/rover/r515/{plan-p4.txt, plan-p4-v2.txt, plan-p3p4.txt, run_orchestrator_e2e.sh, run_scale_e2e.sh, summarize_r515.py, prereg-r515.json, register_r515.py}` | 器具（预注册在起臂前落盘） |

质量门：全量单测 **1684/1684**（R511 1663 + 21）；AOT `PUB_RC=0` · `IL_warnings=0` · 15,555,120 B · sha12 `a32116b4d373b8c0` · `VERSION_RC=0`。

## 2. 修掉的两个真实缺陷（本轮新铁律）

1. **远端节点必须先 `InitializeAsync`**（与 CLI/one-shot 同源）：否则一律 `Failed — Agent is not in ready state. Current state: Initial`。首跑即此因（0/12），修后 4/4 Completed。
2. **节点状态必须绑产物证据**：12 步跑次 `n3` **5 ms 完成、0 产物、仍记 Completed** ⇒ 假绿。现版本状态由 `AgentResponse` 成功判定，未绑磁盘证据（已列入下轮必修）。

## 3. 同窗对照读数（p4 题面 v2 逐字节，同一 adapter 真值，`deepseek-chat`）

| 时刻 | 臂 | 用例 | 调用 | tokens | 编排器节点 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| 10:43 | single 6 步 | **12/12** | 6 | 69,070 | — | 单轮满分 ⇒ 4 节点计划**不可判别** |
| 10:43 | orch v1（n1∥n2 全契约） | 3/12 | 57 | 280,083 | 4/4 Completed | 同层两写者各实现整包、互相覆盖（`n1` 写 3 文件 / `n2` 写 4 文件） |
| 10:48 | single 6 步 | **4/12** | 6 | 70,052 | — | **同输入 20 分钟后同臂 12/12→4/12** ⇒ 单跑次不可判优劣 |
| 10:48 | orch v2（串行+硬文件范围+契约按规则切分） | **9/12** | 16 | 331,586 | 4/4 Completed，归属干净（n1→2 文件/n2→model.py/n3→cli.py/n4→本地自测） | **同窗内 9/12 > 4/12** |
| 10:52 | single 12 步 | 4/12 | 12 | 253,809 | — | 抬单轮预算**不改善** |
| 10:52 | orch v2（每节点 12 步） | 0/12 | 23 | 454,208 | 4/4 "Completed"（`n3` 5 ms/0 产物 = **假绿**） | 节点假绿污染整包 |

判据机检：**C1 PASS · C3 PASS（仅 10:48 窗）· C4 PASS（85/127/178 ms）· C5 PASS（18/36 步 > 6）· C6 PASS（v2 三节点各有产物）· C2 FAIL（最好 9/12，非 12/12 ⇒ 铁律 11 前置未满足）**。

## 4. 诚实边界

1. **每臂 n=1 跑次**；同臂跨跑次摆动极大（single 6 步 12/12 vs 4/12）⇒ C3 只作**该窗内**对照，禁外推；跨窗（R511/R512/R513）题面版本不同 ⇒ **禁相减**。
2. C2 未过：9/12 的 3 项失败集中在**集成面**（`done_unknown_id` 退出码、`bad_request_exit2`、`no_temp_residue` 原子写），产物**不是**可验收状态。
3. v2 计划（串行 + 硬文件范围 + 契约切分）是**看到 v1 失败后**的修正，属器具修订而非预注册；v1 读数原样保留。
4. 12 步跑次暴露的节点假绿 ⇒ 该跑次读数不作为机制证据。
5. 规模臂（双包 p3+p4 / 24 用例 / 7 节点 / `run_scale_e2e.sh`）**本轮未跑**（时间与内存闸约束），禁按未跑充当读数。
6. 内存闸：首跑 `GATE_BLOCKED`（`mem_available_mb=2610 < 2650`）已作废；后续两次连续 2×PASS（2929 / 2782）。

## 5. 下轮候选（全候选并轮）

1. **节点成功判据绑证据**（写节点须 `files[]` 非空或调用数>0，否则 Failed）——修 5 ms 假绿。
2. **每节点写范围机制化**（action 策略白名单，而非仅提示词）——把 v2 的提示词约束升级为 fail-closed 机制。
3. **规模臂**：`run_scale_e2e.sh`（p3+p4，24 用例，预算上界 42 步）——单轮 6 步必败的题面才可判别。
4. **题面规模曲线**：{4,7,12,20} 节点 × {6,12} 步 × n≥3，出「节点数—规模」曲线。
5. `pollInjections` 审批/澄清注入通道端到端实测（当前透传未测）。
6. 跨轮续作：`seedRun` 入口已留，接调度器（无人值守 outer driver）。
