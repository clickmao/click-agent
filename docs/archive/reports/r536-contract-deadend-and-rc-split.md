# R536 — R1 契约**死路分支**闭合 + rc 域「自测期望 vs 执行器实测」分离（同窗同题复跑）

> 轮次 R536（2026-09-18）· 轮志 · 预注册 `eval/rover/r536/prereg-r536.json`（含 A1 增补）·
> 跑盘 `eval/rover/r536/run-w1/`、`eval/rover/r536/run-reps/{r2,r3}/` ·
> 产品改动：`src/agent/contract/*`（生成物）+ `src/agent/r1/{R1Pipeline,R1Transcript,R1RunResult}.cs` + `tools/r1gen/*`（生成器入仓）·
> 二进制 `/tmp/pub_r536/agenthost` sha256 `e0c9fe041db1d481…` · 15,745,856 B · **IL 警告 0**

## 1 因果链（一句话）

R535 的挂 role 臂 `0/30` **不是 role 的负作用**，而是契约**自身**有一条**死路分支**：
`有 missing_slots 或 ambiguities ⇒ plan 必空` 与 `intent=code_task ⇒ plan 非空` **同时成立**
⇒ `code_task ∧ 任一歧义` 在原理上不可满足；role 里的 `prefer_clarify_first: true` 只是把模型推上这条路。
本例修法 = 契约语义按「**缺信息 vs 多义**」二分（缺信息停链、多义给 `chosen` 后继续），并把
「**模型自述的 expect_stdout**」与「**执行器实测**」在 rc 域分离（新增 rc=8 `self_test_unmet`）。
同窗复跑：挂 role 臂 **3 窗中 2 窗 30/30**（w1 0/30 系**摆动**）；rc=8 在 r3 真机出现且**产物 30/30**。

## 2 产品/仪器改动（本轮产出）

| # | 改动 | 位置 | 为什么 |
|---|---|---|---|
| ① | 契约语义二分：`ambiguities` 每条**必给 `chosen`（∈options）**、**不再清空 plan**；`missing_slots` 才是停链澄清 | `tools/r1gen/contract.py`（SCHEMA 渲染 + 校验器）→ 机械重生成 `src/agent/contract/{StructuredContract,SemanticsPipeline,Ambiguity}.cs` | 死路分支：模型按旧规则「有歧义 ⇒ plan 空」⇒ 校验器按「code_task ⇒ plan 非空」杀 ⇒ rc=4 空转（R535 实测两次补全皆 `plan:[]`） |
| ② | 准入闸只对 `missing_slots` 停链（rc=2）；`ambiguities` 放行 | `SemanticsPipeline.Gate`（生成物） | 同上：闸与校验器两处都按旧语义判死 |
| ③ | rc 域新增 **8=`self_test_unmet`**（计划**已跑完** ∧ 仅 `expect_stdout` 不符 ⇒ 产物在盘、仅模型自述期望未达成）；执行 rc≠0 或**计划没跑完**仍 rc=5 | `src/agent/r1/R1Pipeline.cs`、`R1RunResult.cs` | R535 缺陷②：rc=5 与「产物 30/30」并存 ⇒ 「链是否达成」与「自测期望」两件事被压在一个码里 |
| ④ | 台账新增 `plan_steps_total` / `steps_executed` / `self_test_unmet` / `ambiguities_chosen[]`（逐条 `span => chosen`） | `src/agent/r1/R1Transcript.cs` | 多义不再停链 ⇒ **采用的解读必须有痕**；自测未达成不得靠 rc 数字猜 |
| ⑤ | **生成器入仓**（原只在 `/tmp/fable-r1`）+ 新增**同源闸** `--check`：生成器 vs 现盘字节逐件比对，rc 0/1 + `R1GEN_EXIT` 显式标记 | `tools/r1gen/{contract.py,r1prompt.py,gen_csharp.py}` | 仓关键产物不得只存 `/tmp`；见 §3 的真缺陷 |
| ⑥ | 生成期 **fail-closed**：前缀里每个 `<good_response>` 必须自己过契约（否则拒发） | `tools/r1gen/gen_csharp.py` | 实测抓到前缀示例 #2 的 JSON 里内嵌未转义引号 ⇒ **根本不是合法 JSON**（见 §5 缺陷 B） |
| ⑦ | 契约**差分语料**（由 `contract.py` 单一真源生成，C# 侧逐条比对裁决 + 错误子串） | `src/agent.tests/fixtures/r1-contract-cases.json` + `src/agent.tests/R1ContractSemanticsTests.cs` | 契约规则有两处实现（Python 生成器 / C# 产品）⇒ 必须有绑定闸，否则静默漂移（R468 同族纪律） |

pin 上移（声明式，由重生成产出，非手改）：`3,970` 字符 / `03215758…` → **`5,140` 字符 / `936c315d…`**。

## 3 真缺陷（本轮自捕，非本轮引入）

- **生成器与现盘工件不同源**：`python3 tools/r1gen/gen_csharp.py --check` 对**修前工作区**判红
  `R1GEN_EXIT=1 / R1GEN_DRIFT_FILES=2`：`StructuredPrompt.cs` 前缀段序与钉值（现盘 3970/`03215758` vs 生成器 3972/`c40809b3`）
  + `StructuredContractTests.cs` 块序表 ⇒ **c7453d3 的「`<hard_gates>` 前移到 `<role>` 之后」是手改生成物、未回写生成器** ⇒
  下次任何人跑一次生成器就会**静默回退**该安全前置。本轮把生成器与现盘**逐字节对齐**（`--check` rc=0）后才做语义改动。
- **前缀示例 #2 不是合法 JSON**（新闸 ⑥ 抓到）：`"missing_slots":["缺"它"的指代对象…"]` 内嵌未转义引号 ⇒
  模型被教一个非法形态。修法 = 内引号改 `「」`（示例语义不变），并把「示例自过契约」做成生成期 fail-closed + C# 侧回归测试（带负控）。

## 4 真机读数（同窗同题 t1 = F2 toolkit 30 隐藏用例；同题面 sha `9fbfaeb3a17b`）

**w1（主跑，臂布局 `run-w1/<臂>/t1/`）**

| 臂 | 调用 | prompt | 命中 | **新算 prompt** | completion | 总 token | R1 rc / stage | 质量 |
|---|---|---|---|---|---|---|---|---|
| `A1-on-t1`（基线） | 4 | 41,444 | 35,968 | 5,476 | 3,649 | 45,093 | — | **30/30** |
| `R1nr-t1`（不挂 role，非交付面） | 1 | 2,950 | 2,816 | 134 | 3,571 | 6,521 | 0 / done | **30/30** |
| `R1r-t1`（**挂 role**，判据主位） | 2 | 6,299 | 5,760 | 539 | 6,550 | 12,849 | **8 / self_test_unmet** | **0/30** ⚠ |

**reps（A1 增补：同臂同题各再跑 2 轮，**不进验收面**，只分离摆动与效应）**

| 复跑 | 臂 | 调用 | 新算 prompt | completion | R1 rc / stage | `self_test_unmet` | 质量 |
|---|---|---|---|---|---|---|---|
| r2 | `R1nr` | 1 | 134 | 7,329 | 0 / done | 0 | 30/30 |
| r2 | `R1r` | 1 | 134 | 3,982 | 0 / done | 0 | **30/30** |
| r3 | `R1nr` | 3 | 497 | 10,402 | **8 / self_test_unmet** | **1** | **30/30** |
| r3 | `R1r` | 3 | 489 | 10,378 | 0 / done | 0 | **30/30** |

**挂载证明（实发 prompt，非法自证）**：`dump#3` 线上 system **5,140 字符 sha `936c315d…` 逐字节 == 产品 pin**
（`==True`）、纪律尾块**不在场**、`tools_n=0`、`msgs=2`；`role in user tail only = true`
（`R1r` user 1,702 字符含 `<role_profile>`、`R1nr` 1,343 不含；**两臂 system sha 相同**）；`wired_clean_prefix_ok=true`。
**负控**：同一机检对 R535 时点的 pin（3,970/`03215758`）判假 ⇒ 判据非恒真。

## 5 预注册裁决（照原样判，不改阈值；证伪的单列）

| 项 | 预注册 | 实测 | 裁决 |
|---|---|---|---|
| **J1** 挂 role 臂「可推进 ∧ 30/30」 | 两者同时 | 可推进 **成立**（契约过、plan 5 步、role 只进 user 尾块）；质量 w1 **0/30** | **证伪**（按字面）；post-hoc：同臂 r2/r3 **30/30** ⇒ 摆动 |
| **J2** 挂载证明（system == pin ∧ 两臂 system 同） | — | 全过（见 §4） | **成立** |
| **J3** 不挂 role 臂 rc==8 ∧ 30/30 | rc 恰为 8 | w1 **rc=0**（本窗自测即相符，无冲突）；r3 复跑 **rc=8 ∧ 30/30** | **w1 字面证伪**；机制在 r3 实证（post-hoc 单列） |
| **J4** 若 J1 证伪 ⇒ 只写收窄 | — | 已按此写：**不宣称 role 轴恢复**，只宣称「死路分支闭合」（有 r2/r3 + 单测双证据） | 遵守 |
| **J5** 成本读数 | 单窗 n=1 只作参考 | 铁律 11 前置器 **rc=1**（`BLOCKED = w1/agentR1r-t1/t1 0/30`） | **全部成本读数标「参考（未可验收）」** |
| **J6** 生成器同源闸 | 修后 rc=0 ∧ 修前 rc=1 | 修前 `R1GEN_EXIT=1 / DRIFT=2`；修后 `R1GEN_EXIT=0 / DRIFT=0`（pin 0140/`936c315d`） | **成立** |

**死路分支已闭的机检证据（比真机读数更硬）**：`R1ContractSemanticsTests` 用**R535 真机 raw**（挂 role 臂那条
`plan:[] ∧ ambiguities 无 chosen`）作反事实控制 —— 旧规则下它「合法」（模型照规则做），新规则下判红且修复消息可操作；
同一形态补 `chosen` + plan ⇒ **valid**。差分语料 14 条（含缺子字段/取值越界/refusal 互斥/缺必填）在 C# 侧逐条一致；
全量 **1837/1837 绿**；API 面基线显式重生 **+1/-0**（`Ambiguity.Chosen`，纯增项）。

## 6 诚实边界

1. **J1/J3 均按预注册字面证伪**（w1 单窗），成立的部分全部是 post-hoc（reps 窗 / 单测）；本轮**不宣称**「role 轴有恢复、有增益」。
2. **rc=8 不可作产物正确性证据**：w1 的 `R1r` 正是 rc=8 **且** 0/30 —— 该码只声明「模型自述的自测期望未达成」，产物对错由外部门禁/隐藏用例判。措辞已在 `R1RunResult` / `R1Pipeline` 头部写明。
3. **w1 的 `R1r` 0/30 定因（已取证，非同源 oracle 判定）**：产物 `toolkit/jsonmini.py` 第 3 行是模型自己写的
   `import unicodedata_placeholder  # noqa`（**原始输出** `adapter/side-agent-004.json` 里就是这个串）⇒ `ModuleNotFoundError` 30/30 全败；
   同一窗前缀机检全过、同题同判分脚本下 `R1nr` 30/30 ⇒ **非夹具缺陷、非仪器缺陷**，是模型侧自造模块名。
   该臂的自测步骤 `s5`（期望 `7`、实测空）**正确地把这次失败指出来了** ⇒ rc=8 与产物状态本轮**一致**。
4. **每臂 n=1（w1）/ n=2（reps）** ⇒ 摆动幅度（同臂 calls 1↔3 = 3.0×、质量 0/30↔30/30）**大于**任何臂间差 ⇒ 不作稳定结论（R523）。
5. **codex 外部真值臂未跑** ⇒ 主线四硬条件的「外侧对照」本窗仍缺。
6. **前置器 rc=1** ⇒ §4 全部调用/token 数只能当参考读数（不写进任何「降幅」结论）。
7. **本轮过程缺陷（如实登记）**：写 `prereg-r536.json` 的 A1 增补时，脚本的「序列化器逐字节复现原文件」断言返回
   `False`，我**没有中止**仍写盘 ⇒ 该文件被重排（内容不变、格式由内联改为分块展开；`made_before_run` 与 A1「起臂前落盘」性质不受影响）。
   纪律本应是「断言失败即改用文本插入」。已在 R537 候选里加一条：**增补脚本断言失败必须 fail-closed 退出**。
8. 同机有一个兄弟 cron 会话在 02:20 跑过 LLM A/B 探针（`/tmp/ab_contract.py`，读同一个 `StructuredPrompt.cs`）；
   起臂前已确认其退出（~80 s）并在 02:24 起臂 ⇒ 读数窗口干净，但该会话**仍在**（LSP 在）⇒ 归属需注意。

## 7 下轮候选（R537）

① **role 轴复跑升到 n≥3 独立窗**（现有 3 窗：0/30、30/30、30/30 ⇒ 摆动主导）＋ 补 **codex 外侧对照臂**（主线四硬条件缺项）；
② **rc=8 措辞与判据再收窄**：把「自测未达成」与「产物可疑」成对报（例如 rc=8 时同时输出失败步骤的 stdout 尾 + `done_when` 命中情况），
   并在预注册里写明「rc=8 不作产物正确性证据」的机检（防被读成「链成功」）；
③ **`missing_slots` 停链路径首测**（新语义下的 rc=2 分支尚无真机读数）；
④ 生成器 `--check` 挂进提交钩子（声明==现盘字节这类缺陷不该靠下一轮偶然抓到）；
⑤ 增补脚本 fail-closed（§6.7）。
