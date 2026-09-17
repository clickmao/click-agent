# R532 — R1 结构化契约管道**接线**: 「1 次调用产出整包计划 → 机械执行」同窗迷你对照

**日期**: 2026-09-17 23:38–23:41 (同窗 `mini1`) · **二进制**: `/tmp/pub_r532c/agenthost` sha256 `47fbd7fc0f88d1e752a67602c44cf62f859865a4609380f88552c54f3f953448` · 15,729,408 B · **IL 警告 0**
**轮号归属**: 本轮 = R532（`eval/rover/r532/`）；兄弟主线 **R-N1 (`af8c15b`)** 的 `/tmp/pub_r532*` 构建目录名与本轮号无冲突（`git log --all` 无任何 `R532` 提交，`eval/rover/r532/` 本轮首建）。

## 0. 靶点来源（用户 2026-09-17 方向令 · 主线）

- 用户令（逐字）：「利用 r1 对真假信息判别(记得要挂载 role 的额外数据，管道里应该已经接了)来让用户一轮任务总数 tokens 使用量显著下降 30% 以上(主要是不必要的 llm api 请求少了)」＋ 2026-09-17 方向逆转：「重建为『结构化 prompt ⇄ 远程 LLM ⇄ 结构化结果 ⇒ 精准语义 ⇒ 管道』」。
- **R-N1 交接的未闭合项**（兄弟主线自报的诚实边界）：「宿主尚未调用该模块 ⇒ 有代码行 ≠ 生效（未接线）」。
- ⇒ 本轮靶点 = **把 R-N1 的 `src/agent/contract/*` 真正接进产品调用路径，并以实发 prompt 机检 + 同窗读数证明其生效**（不是再加器具）。

## 1. 机制（接线点与组件）

- **单一接线点**：`src/agent.host/Program.cs` 单条路径（`-q`）内，`env AGENTFRAMEWORK_R1_CONTRACT ∈ {1,on,true}` ⇒ 转 `src/agent.host/R1CliEntry.cs` ⇒ `agent.r1.R1Pipeline.RunAsync`。**缺省关（结构量开关，非文本判据）⇒ 宿主行为与既往一致，可回退**。
- **新增产品模块（`src/agent/r1/`，单类型单文件 / 单命名空间 `agent.r1`）**：
  `R1Pipeline`（总装：pin 自检 → 1 次结构化调用 → 契约校验 → 语义闸 → 执行 → 落盘）
  `PlanExecutor` + `PlanExecutorResult` + `StepOutcome`（白名单工具 `write_file`/`run`，路径逃逸 fail-closed，UTF8 **无 BOM**，`expect_stdout` 逐字比对，进程超时 `-9` 显式区分）
  `R1ContractMode` / `R1Options` / `R1RoleMount`（role 额外数据**只进 user 轮尾块**，禁入常量前缀 —— 与铁律 12 前缀恒定不冲突）
  `R1Hash` / `R1Json` / `R1Text` / `R1Transcript`（AOT 零反射手写 JSON 台账 + `R1_STATS` 单行标记）/ `R1CallStats` / `R1RunResult`
- **rc 域**：`0` 可推进 / `2` 缺信息澄清 / `3` 硬闸拒答 / `4` 契约或计划非法 / `5` 执行未达期望 / `6` pin 漂移或传输失败（fail-closed）。

## 2. 同窗读数（`mini1`，同 adapter、同题面、同二进制）

题面 = `t1`（`toolkit-multimodule-v1`，30 隐藏用例）；题面 sha256 `9fbfaeb3a17bea23` 硬门 PASS（自洽）；起手闸 2/2 PASS（mem 2652/2653 MB ≥ 2650）；输入物化 `evidence/mini1/task-t1-prompt.txt`。

| 臂 | 路径 | 调用 | prompt | 命中 | 新算 | completion | 总 token | 隐藏用例 | cli rc |
|---|---|---|---|---|---|---|---|---|---|
| **R1**（本轮接线） | 结构化契约管道 | **1** | 3,383 | 2,560 | **823** | 3,348 | **6,731** | **26/30** | 5 (`expect_stdout`) |
| **A1-on**（同窗基线） | 动作环（纪律开） | 19 | 267,934 | 261,632 | 6,302 | 9,595 | 277,529 | **30/30** | 0 |

比值（同窗、同题面）: 调用 **0.053×**（−94.7%）· 总 token **0.024×**（−97.6%）· 新算 prompt **0.131×**（−86.9%）。
R1 臂产物：`toolkit/{__init__.py(0B),vm.py(2691B),jsonmini.py(5883B),__main__.py(439B)}` —— **整包四文件由 1 次 completion 产出**，`R1_STATS` 台账落盘 `evidence/mini1/R1/t1/transcript.json`。
失败例（4 条，皆 `stdout_mismatch`）：`jsonmini#14/#18/#22/#26-hidden`（vm 11/11 全过）。

## 3. 挂载证明（实发 prompt 机检，非法自证）

`eval/rover/r532/analyze_r532.py --run-dir /tmp/r532_mini --window mini1`（只读 adapter FULL dump）：

- **M1（逐字节）**：R1 臂首个请求实发 system 的 **head = 3,889 字符，sha256 `58e2df67afe1923b…` == 产品侧台账 pin**（`transcript.prefix_sha256`，`prefix_pinned=True`）✅
- **M2（常量尾块）**：实发 system 剩余 **532 字符** = 宿主 R522 纪律块，**sha `16efa2f069698edd` 与同窗对侧臂（A1-on）该块逐字节相同** ⇒ 线上前缀 = 3,889 pin + 532 常量 = **4,423 字符，随调用不变** ✅
- **M3（形状）**：`msgs=2`（system+user）、`model=deepseek-chat`、`response` 为单个 JSON object；`wired_constant_prefix_ok=True`。
- **负控（同窗内在）**：同器具对 `A1-on` 臂判 **M1 假**（其 system 9,937 字符，非 R1 pin）⇒ 证明该判据对「未走 R1 路径」的臂会响，不是恒真。

## 4. 同轮发现的产品缺陷（未闭合，交下一轮）

1. **产品侧 completion 计数缺失**：台账 `completion_tokens=0`，而中继实报 **3,348** ⇒ 产品侧 usage 字段口径有漏（总 token 6,731 = 3,383 + 3,348）。
2. **R1 单条调用仍带 5 个工具定义**（`tools_n=5`）：R1 契约只要 JSON，工具面是纯浪费的 prompt 预算（3,383 prompt 中占比未分解）⇒ 下一轮关掉。
3. **`expect_stdout` 语义过强**：模型自检步骤 stdout 与期望文本不符（`stdout 'ERRrc=0'`）即整轮 `rc=5` 停机，而**产物已落盘且 26/30 通过** ⇒ 应降级为告警并继续（或把自检步骤排除出闸）。
4. **宿主尾块（R522 纪律）在 R1 面仍注入**：与「结构化前端」语义无关（该块教的是工具环礼仪）⇒ 下一轮按模式裁剪，或把 pin 扩到线上 4,423 字符。

## 5. 诚实边界

- **铁律 11 前置器 `python3 eval/rover/r507pre/exec_precondition.py --round r532` = rc 3（DISCOVER_FAIL：本轮无 codex 侧、题集未注册）⇒ 上表调用/token 降幅一律标「参考（未可验收）」，禁作验收依据**（原文 `evidence/mini1/logs/precond.txt`）。
- **单题 · 单窗 · 每臂 n=1**：按 R523 已立「单窗=噪声（同臂跨同输入窗摆动 4.25×）」⇒ 本轮**不宣称能力结论**，只宣称「接线生效 + 该窗成本形状」。
- **质量不等**：26/30 vs 30/30 ⇒ 判据「回复质量不降」在本题**未达成**，R1 臂未达「可验收」。
- 未测：role 额外数据挂载（`role_note_chars=0`，本轮未给 `AGENTFRAMEWORK_R1_ROLE_FILE`）· codex 外部真值同窗（只有本侧两臂）· R1 在 F1/F3 族的成本与质量 · 契约修复轮（`max_repair=1` 未被触发）。
- 测试：`R1PipelineTests` PASS 全绿；全量套件见 `docs/improvements.md` R532 条（1 例随机端口 flake = 既有 `FrontendHandshakeTests`，单跑 4/4 PASS）。

## 6. 候选台账（R531 下轮候选 ①–⑤ + 未闭合遗留，逐项）

| # | 候选 | 状态 | 原因/证据 |
|---|---|---|---|
| 0 | **R1 结构化管道接线**（本轮主线，来自用户方向令 + R-N1 未闭合） | **做**（已闭合） | 见 §1–§3：冒烟 rc=0 + 同窗实跑 + 实发 prompt 机检 |
| 1 | 补齐 w2/w3 并逐窗 + 极差重报 | 未做 | 单窗预算已被主线接线占满；R531 终局裁决已给出三窗极差，重报属复算 |
| 2 | 第 8 条纪律候选（着法/输出合法性自验） | 未做 | 属旧 R 轴（用户 2026-09-17 判「封存·没效果」）；本轮并入项优先 |
| 3 | 合批轴在 F2/F3 的成本符号单列 | 未做 | 同上；F2 已在本轮作 R1 对照题面（同窗 A1-on 读数可复用为锚） |
| 4 | codex token 计量接进 adapter | 未做 | 需改 harness（`eval/rover/r5xx`），非本轮产品面 |
| 5 | `EXP1-Q47` 登记行收口 | 未做 | 属兄弟侧登记表；R531 已回填轮节，收口由该侧执行（避免替对侧声明） |
| 6 | 产品缺陷 1–4（§4） | **未闭合** | 本轮已定因、未改码（改码须重出 AOT + 重跑同窗，超本轮预算） |

## 7. 下轮候选（R533）

1. **缺陷 2+3 同轮闭合**：R1 调用面关工具（`tools_n=0`）+ `expect_stdout` 降级为告警 ⇒ 预期 prompt token 再降、rc 语义变干净。
2. **质量补差**：对 `jsonmini` 4 条失败例做**契约→修复轮**（`max_repair` 生效路径首测）或把 `done_when` 自检命令由模型自选改为**执行器注入**（题面公开验收命令）。
3. **同窗 n=3 扩面**：R1 臂 × `t1` reps≥3，报逐窗 + 极差（R523 判据）。
4. **注册进前置器发现面**：`eval/rover/r532/{taskset,snapshots,evidence/windows/*/report.json}` 建齐 ⇒ `exec_precondition --round r532` 出 rc 0/1，把「参考（未可验收）」转成可验收。
5. **role 挂载首测**：`AGENTFRAMEWORK_R1_ROLE_FILE` + 台账 `role_note_chars`，验证尾块不影响 head pin。
