# R1 抽取与落地：Fable 5.1 → 结构化 prompt ⇄ 结构化结果 → 精准语义 → 管道

来源 `DESIGN-RATIONALE.md`（机检七条动因）。本文件的数字全部来自真实执行，无估算。

## 一、推翻什么（旧流程 → R1）

| 旧（R413–R531 主线） | R1 |
|---|---|
| 自由文本动作环 + 工具 schema 全量常驻 | 单次结构化调用：prompt 内声明契约，返回 JSON，**无多轮工具环** |
| 语义藏在自然语言里靠后处理猜 | 语义是**一等字段**（intent/entities/constraints/missing_slots/ambiguities/plan/done_when/refusal） |
| 缺信息就猜着往下做 | 缺信息/有歧义 ⇒ 管道**停下要澄清**（rc=2），禁猜 |
| 判据靠事后 grep 锚 | 判据 = 契约校验器 + 闸返回码（rc 0/2/3/4），机检 |
| 系统提示词随轮次膨胀、中段混入易变材料 | 恒定前缀（3,889 字符 / sha `58e2df67…`）+ 易变项全部下沉到 user 轮 |
| 器具/登记/文档轮次 | 封存（用户令） |

## 二、R1 四段链

```
结构化 prompt（恒定前缀 + 任务尾）
   → 远程 LLM（json_object，deepseek-flash）
   → 契约校验（缺子字段/越界/悬空依赖/语义冲突 ⇒ 修复环）
   → 精准语义（强类型字段）
   → 确定性管道（闸序固定、fail-closed）
```

## 三、仓内落地（已编译/已测）

`src/agent/contract/`（namespace `agent.contract`，单类型单文件，铁律 13）:
`Entity.cs` `Ambiguity.cs` `PlanStep.cs` `RefusalInfo.cs` `Semantics.cs` `PipelineOutcome.cs`
`StructuredPrompt.cs`（前缀字面量**由原型机械生成**，`PrefixChars`/`PrefixSha256Pinned` 为钉子）
`StructuredContract.cs`（`SchemaText` 一处定义 ⇒ 同时进 prompt 与校验器）
`SemanticsPipeline.cs`（闸：硬门→语义完整→非执行→计划合法性）

测试 `src/agent.tests/StructuredContractTests.cs`：8 用例
（前缀逐字节钉死 / 块序 / 前缀无易变项 / 契约与 prompt 同源 / 真实形态通过 /
6 类负控必红 / 闸 rc 分支 / 改一字 sha 必变）。

## 四、真实读数

**远程（4 次真实调用，同前缀 sha `58e2df67…`）**

| 用例 | rc / stage | prompt | 命中 | 新算 | completion | 修复轮 |
|---|---|---|---|---|---|---|
| kadane（真写文件+真跑） | 0 / done | 1,753 | 256 | 1,497 | 345 | 0 |
| ambiguous（"把它改好"） | **2 / semantics_incomplete** | 1,693 | 1,536 | 157 | 117 | 0 |
| refusal（要求外传 key） | **3 / hard_gate** | 1,723 | 1,536 | 187 | 177 | 0 |
| informational | 2 / semantics_incomplete | 1,696 | 1,536 | 160 | 100 | 0 |
| **合计** | 0 修复轮 | 6,865 | 4,864 (70.9%) | 2,001 | 739 | 0 |

非冷启调用命中稳定 = **1,536/1,7xx ≈ 90%**；冷启首次仅 256（跨轮已预热）。这是「恒定前缀 + 易变下沉」动因的直接兑现。
kadane 产物 `sandbox/sols/kadane.py`（289 B）独立复跑 stdout = `6`（期望 6）⇒ 管道真执行。

**仓内**

| 面 | 读数 |
|---|---|
| 构建 | 0 错误（76 警告全为既有 xUnit1030） |
| 全测 | **1769/1769 通过**（含 R1 新增 8），0 失败 |
| 负控 | 契约 6 类红 + 闸 2 类红（scope 逃逸 / 禁用命令），rc=4 |
| AOT | 见 `aot-publish.log`（本轮发布 `/tmp/pub_rn1`） |

## 五、与旧链的关系

旧动作环**不立刻拆**：留作对照臂。切换标准 = 新链在同一组真实任务上给出可验收读数
（质量不降 + 调用数/新算 token 下降），否则只算并行候选。禁止「拆了再证明」。
