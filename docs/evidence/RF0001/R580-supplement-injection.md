# R580 · 用户补充的「合理时机插入」（长任务运行中）

**口径**：用户令「长自动任务应该在 llm 返回后补充用户提供的相关信息；不一定要用召回系统做，可以请求 llm，但涉及到上下文精排别破坏了缓存」+「做到在合理的时机插入」。

## 1) 落点（时机锚 = 远端返回后收割 / 下一次调用前插入）

| 面 | 文件 | 时机 | 落点 |
|---|---|---|---|
| 契约面（R1 结构化调用） | `src/agent/r1/R1Pipeline.cs:77-82, 86-87, 107-109` | 每次远端**返回后** `Harvest()`；**下一次调用前** `SelectFor()` | user 轮**可变区**：`<task>…</task>` → `<supplement>…</supplement>` → `<repair>…</repair>` |
| 长任务面（节点提示） | `src/agent.host/OrchestrateCommand.cs:190-202, 340` | 上一个节点返回后（下一个节点边界） | 节点提示**尾部** `【用户补充】` 块（公共头 preamble+全计划+纪律之后） |
| 投递面 | `supplementsPath`（缺省 `<计划文件>.supplements.txt`，可 `--supplements`） | 运行中追加一行即投递 | —— |

**台账**：`src/agent/r1/SupplementInbox.cs` — 去重投递 / 按步骤文本打分挑选（复用既有 `agent.rag.IRerankScorer` + `RerankStage.OrderIndices`，打分实现可换 llm 或本地模型）/ 低于阈值**不插且不丢** / 一次性消费记账（`Pending`/`Consumed` 可读可报）。
**块渲染**：`src/agent/r1/SupplementBlock.cs`（只追加尾部；无补充 ⇒ 空串，逐字节等于旧行为）。
**引擎同源**：契约面模板在 `tools/r1gen/gen_csharp.py`（禁手改生成物）⇒ `--check` 同源闸 `R1GEN_DRIFT_FILES=0`，前缀口径不变 `chars=15291 sha=f1280f71…d4a`。

## 2) 真机首验（同计划 / 同配置 / 单变量 = 投递文件有无）

```
agenthost --orchestrate /tmp/r580supp/plan.txt --workspace <ws> --node-steps 1 --max-nodes 1
```
| 臂 | 投递文件 | prompt 构建 tokens | 注入落点台账 | 远端调用 | 节点 |
|---|---|---|---|---|---|
| A | 有 1 行 | **7011** | `n1 \| injected=1` | 1 | Completed（48.9 s） |
| B | 无（对照） | **6954** | 无 csv（未注入） | 1 | Completed（106.5 s） |

读数：Δ = **+57 tokens**（= 补充块的 token 增量）⇒ 补充**确真进入了发往模型的 prompt**；**远端调用数 1 : 1 不增**；前缀/公共头不变（块只在尾部）。

## 3) 机检与闸

- build `agent.sln` Release：**0 error**；全量 `agentframework.tests`：**1920/1920 绿**（本轮 +10：7 手写 + 3 生成）。
- 形式门禁：**14/14**；API 基线重生：**+17/−2 行**（差异仅本轮成员），重生后 API 面测试绿。
- 缓存安全判据（生成测试）：`Supplements_Do_Not_Touch_Pinned_Prefix`（前缀 chars/sha 逐位不变）+ `No_Supplements_Keeps_Legacy_User_Message`（零回归）。

## 4) 诚实边界

1. 真机 A/B 各 **n=1**（单窗），token 差是因果信号；**未跑 reps≥3**，未核 host_sha 同窗。
2. 阈值缺省 0.05（词法 bigram 粗门槛，`AGENTFRAMEWORK_ORCH_SUPPLEMENT_MIN_SCORE` / `…_R1_SUPPLEMENT_MIN_SCORE` 可覆盖）；**未**接本地/远端 llm 打分实现（接口已留：`IRerankScorer`）。
3. 补充分发粒度 = **一次性消费（插到投递后第一个匹配的步骤/节点）**；「同一条分发给多个未开始节点」**未实现**。
4. 契约面（R1Pipeline）只有单测 + 前缀钉子，**无真机端到端**（需要 R1 调用面）。
5. 运行中插入仍是「节点/调用边界」粒度，**不在单次模型调用内部**（由产品形态决定，非本次改动）。
