# R618 报告 · RF0004.2 · M3 **第二刀 = 执行面接线**（`accepted` 采纳集 ⇒ 执行面）

轮次：R618 ｜ 协议：`docs/plans/RF0005-completion-protocol.md` §2 固定环 0–9 ｜ 窗集：**w208..w210**（与历史窗集 w184..w207 不相交）
被测件：`$HOME/.agentframework/artifacts/pub_r618/agenthost`（sha256 `886db888d744a6196dbdefd6aa482c8fc0b966eaab16fac7e6c3add44a0f3ca6`，19,834,064 B；`bin_sha_stable=true`）
判据器：`eval/rover/r618/judge_r618.py`（影子自检 `selftest_judge_r618.py` 五态 rc=0）｜ 预注册：`eval/rover/r618/prereg-r618.json`（先写后跑，v2 起臂前修订）｜ DAG：`eval/rover/r618/dag-r618.md`
臂：T×9 / C×9 / C1(codex 真值)×3 = 21 跑次 ｜ 题集 sha16 `e0c667c2a313c04b`（与 R600–R617 逐字节同）
单变量：`AGENTFRAMEWORK_R1_ACTION_EXEC`（产品缺省 **off**）——T 显式 `=1`，C `unset`

## 0. 一句话

**机制面 PASS**（执行面确实被采纳集驱动：T 9/9 `exec_source=candidates`、守恒违例 0、两臂可区分、前缀与 R617 **逐位同**）；**能力面负向不达**（整题全对 T **4/9** vs C **6/9** vs 真值 2/3；逐窗 +0.33/−0.67/−0.33 **翻号**，J5 方向不一致 ⇒ 该轴在能力面**非承重**）；**铁律 11 rc=1 ⇒ 一切质量/成本读数标「参考（未可验收）」**；轴保持**默认 off、未放行**。

## 1. 起手闸与前置

| 条目 | 读数 |
|---|---|
| `roundcheck preflight --round R618 --min-avail-mb 2775` | **rc=0**（P1 key / P2 weights / P3 mem 2,815MB / P4 disk 4GB / P5 无在飞执行体 / P6 轮号未占 / P7 R618 空闲 / P8 PUSH_PAUSED=yes）。起手前先清 VBCSCompiler（−534MB）与 pyright（−323MB）⇒ 2,244 → 2,824MB（协议 §2 起手清场条款） |
| 起手闸条款（`gate-margin-r618.json`） | `ceiling=2814 / prev_swing=125 / margin=104 / REQ=2754`，**`cap_binding=true`**（顶棚封顶使振幅项退化到 104 < 125；承 R590 已登记形态）|
| 起手闸 A1/A2 | PASS（mem 2,919 / 2,905MB ≥ REQ） |
| 判别力成对控制 | rc=0（内存带内：基础门槛 PASS ∧ 条款 GATE_BLOCKED）|
| 起手闸 B leak-selfcheck / 同输入硬门 / 臂身份 | rc=0 ｜ 两侧题集逐字节同（sha16 `e0c667c2a313c04b`）｜ 全臂同一枚二进制 + 运行期 `bin_sha_stable=true` |
| 影子自检（判据器上线前） | `selftest_judge_r618.py` **5 态**（正常 / 两臂不可区分 / 真空 / 守恒违例 / 跨轮锚不成立）逐态断言 **rc=0**，负控有牙 |

## 2. 本轮做了什么（产品侧最小改动 + 器具）

| # | 改动 | 位置 | 性质 |
|---|---|---|---|
| 1 | 新记录 `AcceptedAction`（id/工具/args 原文/理由）作**采纳集载体**；`ActionCandidates.Selection` 增 `AcceptedActions` | `src/agent/r1/AcceptedAction.cs` · `ActionCandidates.cs` | **被测单变量的一半**（载体） |
| 2 | 新映射器 `ActionExecPlan`：采纳候选 ⇒ 执行面节点（窄腰 `write_file`/`run`）；**不另立工具表**（同源 `ActionToolDecl`）；窄腰外工具计 `unmapped`；自述期望由 `plan` 里 (工具,参数) 逐字命中节点**继承** | `src/agent/r1/ActionExecPlan.cs` | **被测单变量** |
| 3 | 接线点（唯一）：`execPlan = map.Steps` 取代 `sem.Plan` 传入 `PlanExecutor`；轴关时 `execPlan == sem.Plan` 逐位等价；空执行面文案两臂可区分 | `src/agent/r1/R1Pipeline.cs` | **被测单变量** |
| 4 | 台账四字段 `exec_source` / `_executed` / `_unmapped` / `_expect_inherited`；**轴关 ⇒ 字段缺席**（逐字节同旧） | `src/agent/r1/R1Transcript.cs` · `R1RunResult.cs` | 器具（可机检面） |
| 5 | 单测 `ActionExecPlanTests`（9 条：零回归逐位 / 映射守恒 / 坏参数不静默 / 期望继承 / 空候选 / 轴档解析 / 真实落盘副作用 / 早退语义） | `src/agent.tests/ActionExecPlanTests.cs` | 器具 |
| 6 | 判据器 J0/J1 重写 + 读取契约并入新键 + 五态影子自检 | `eval/rover/r618/*` | 器具 |

**前缀零改动**：`tools/r1gen` 未动 ⇒ T/C 两档 `prefix_sha256` **均为 `25c97bef…`**（= R617 T 档 pin 逐位同）⇒ 跨轮锚成立（`claims_violated = []`）。API 基线重钉 20 行（全属本轮新增成员）。

## 3. 真机读数（w208..w210，21 跑次）

### 3.1 J0 臂轴生效（fail-closed 器具闸）——**PASS**

| 臂 | 跑次 | `exec_source` | 新字段出现跑次 | prefix_sha256 | 缺席 |
|---|---|---|---|---|---|
| T | 9 | 全 `candidates`（9/9） | 9/9 | `25c97bef…` | 0 |
| C | 9 | 全缺席（9/9） | **0** | `25c97bef…`（同源） | 0 |
| C1 | 3 | 无本仓台账（codex 臂，不入本判据） | — | — | — |

`A ∧ B ∧ C ∧ E` 全真；跨轮前缀锚 `D` 亦真 ⇒ 「轴关 = 旧行为逐位等价」由**逐跑次缺席**钉住（不是靠叙述）。

### 3.2 J1 执行面消费面（**主判据**）——**PASS**

| 量 | 读数 |
|---|---|
| T `exec_source=candidates` | **9/9** |
| T `executed>0` 跑次 | **8/9** |
| T 四字段齐备跑次 | 8/9（1 跑次键未到达 ⇒ 字段集不全，单列） |
| 守恒违例（`unmapped<=accepted ∧ executed<=accepted−unmapped ∧ inherited<=accepted−unmapped`） | **0** |
| `unmapped` 合计 / 自述期望继承合计 | 0 / 26 |
| J1c 两臂可区分 | True |

⇒ 第一刀「`accepted` 无消费者」缺口在**执行面**闭合（闭合由读数判，不由代码行判）。
**诊断列（不作判据）**：`steps_executed` 中位 T **6** / C **10**（`plan_steps_total` 中位 T 10 / C 11）⇒ 治疗档更早触发 `expect_stdout` 早退；T 跑次 `plan_steps_total` 仍报 `plan` 全量（口径未变）。

### 3.3 J2b 裁选守恒 —— **PASS** ｜ J2 修复收敛 —— 不达（继承面）

J2b：T 8/9 跑次有声明，`accepted+rejected==declared` 违例 **0**（declared 7–23 / accepted 6–22 / rejected 0–2）。
J2（修复收敛）：converged T **2/9** vs C **5/9**（unmet_after T 6 vs C 4）⇒ 治疗档在「自检未达成 ⇒ 收敛」这一面上更差（并列读数）。

### 3.4 J3 成本面（**参考，未可验收**）

| 量 | T | C |
|---|---|---|
| 调用 Σ（中继 dump 时间轴） | 16 | 16 |
| 新算 prompt Σ | 12,138 | 12,054 |
| 单位调用新算 prompt | **758.6** | 753.4 |
| completion Σ | **59,803**（中位 7,029） | **58,603**（中位 6,702）；Δ **+2.0%** |
| 命中率 v_all 逐跑次 | 0.9035–0.9709 | 0.9071–0.9709 |
| bad_dumps | 0 | 0 |

J3 v1（`max_calls`）= PASS；**J3 v2 = FAIL**（`a2_per_window_calls:w209` ∧ `b1_unit_new_prompt`）⇒ 无降幅可宣称。

### 3.5 J4/J5 能力面（并列，欠功率）—— **负向**

| 臂 | 整题全对 | 池化率（Wilson95） | 逐窗 | 用例中位 |
|---|---|---|---|---|
| T | **4/9** | 0.4444 [0.189, 0.733] | w208 **3/3** · w209 1/3 · w210 0/3 | 49 |
| C | **6/9** | 0.6667 [0.354, 0.879] | w208 2/3 · w209 3/3 · w210 1/3 | 58 |
| C1（真值） | 2/3 | 0.6667 [0.208, 0.939] | w208 0/1（52/58）· w209 1/1 · w210 1/1 | 58 |

逐窗配对差 `T−C`：**+0.333 / −0.667 / −0.333**；`T−C1`：+1.0 / −0.667 / −1.0 ⇒ **J5 跨窗集方向不一致**（R617 池化 +0.3334 vs 本轮 −0.2223）⇒ 按「摆动 ≥ 效应 ⇒ 非承重」判：**该轴在能力面不构成提升**。
任务面 v3：有效窗 **2**（w208 真值自败 52/58 ⇒ 剔出配对、单列我方 58）⇒ 判据行使，label **不达**（D_list [−11,−15]，中位 −13；我方 47/43 vs 真值 58/58）。

### 3.6 铁律 11 前置器（收口前必跑）

`exec_precondition.py --round r618` ⇒ **rc=1（未可验收）**：21 臂独立物化实跑，**blocked 9**（T 5 / C 3 / codex 1）；两枚 **0/58** 跑次（`w209/agentT-r1` 探针未达成、`w210/agentT-r1` 零步执行面）；codex 真值亦有 1 臂 52/58。
**首跑 `BLOCKED=missing_case_script`（器具面缺 `eval/rover/r618/cases/`）⇒ 从 r610 逐字节补齐（`run_cases_r521.py` sha16 `d9aecf4d397550b8` · `cases-r521.json` sha16 `270128eb85c7afc0`，与 r615 同值）后**只重跑后处理**、不重测**（承 R617 同形处置）。
⇒ 本轮一切降幅/质量声明一律标 **「参考（未可验收）」**。

## 4. 失败定因（逐条可机检，不作超出证据的归因）

| # | 形态 | 台账证据 | 定级 |
|---|---|---|---|
| D1 | **无候选 ⇒ 空执行面 ⇒ 零步执行** | `w210/agentT-r1`：`declared/accepted` 缺席（键未到达）∧ `exec_source=candidates` ∧ `executed=0` ∧ `plan_steps_total=10` ⇒ 该跑次**什么都没跑**（对照档在同一题面会跑 plan 的 10 步） | **轴引入的新失败形态**（能力面负向的直接来源之一）；修法候选 = 空候选/键未到达时回退 `plan`（第三刀） |
| D2 | **候选序 ⇒ 早退更早** | T 6/9 跑次 `executed=6 < mapped`（早退于 `expect_stdout` 不符）；同题对照档 `executed=15/15`。`w210/agentT-r2` reason = `step a7 stdout 与 expect_stdout 不符` | 待定因（候选序 vs plan 序差异**未证**，禁无证据归因）；第三刀靶点 = 依赖/序面 |
| D3 | 一跑次 `rc=8 public_probe_unmet`（`w209/agentT-r1`，6/8 步，0/58） | 与 D1 不同：有执行但产物不可用 ⇒ 归「产物未成型」族 | 既有族（非本轮新形态） |

**摆动 vs 效应**：同臂逐窗全对率摆动（T 3/3→1/3→0/3；C 2/3→3/3→1/3）**大于**池化效应（−0.2223）⇒ 按 R587/§3 纪律，**单窗集读数不得作能力结论**。

## 5. 收口五件

| 件 | 路径/读数 |
|---|---|
| 轮工件 | `eval/rover/r618/{dag,prereg,report,verdict,kpi-table,bins,gate-margin,selftest_judge,judge,run_r618.sh}` + `snapshots/w208..w210/` |
| 证据文档 | 本文件 + `evidence/windows/w208..w210/{report.json,artifacts.json}` |
| registry 行 | `docs/verification-registry.json` → `r618.exec-face-wiring`（L3，含 negative_control/covers/owner_round） |
| kpi 行 | `eval/capability/kpi.jsonl`（带 `baselines` id 列表） |
| 提交 | 逐名列名（禁 `git add -A`） |

`status_gen.py --check` / 形式门禁（`VerificationForm|SkillGeneralization|DevPlanDocRef`）/ 全量定向测试读数见 §6 与提交信息。

## 6. 诚实边界

1. **机制 PASS ≠ 能力收益**：J1 只证「执行面被采纳集驱动 + 条目守恒」；能力面**负向**，且受欠功率与摆动支配 ⇒ 不得宣称任何提升。
2. 第二刀只接**动作面**（`write_file` / `run_command`）；`read_file` / `list_dir` / `delete_file` 在 R1 窄腰无节点（本轮 `unmapped` 实测 0，因声明面本就只出现动作类工具）⇒ 信息类工具属**第三刀**。
3. 自述期望继承数 26 ≠ 0 ⇒ 换载体未丢自检面（可机检）；继承率受 `plan` 与声明重叠度支配，非能力指标。
4. 轴**默认 off、未放行**：本轮不改产品缺省行为；关闭态逐跑次四字段缺席 + 单测逐位等价双钉。
5. M3 出口闸（调用数按 `request_id` 去重 ≤ 旧臂 50%）**本轮只作读数不作验收**：R1 链每任务 1–2 次调用，旧「自由文本动作环」为跨轮形态 ⇒ 分母不同源，禁跨形态相减。
6. `cap_binding=true`（起手闸振幅项退化为 104MB < 125MB）与 `preflight 2775MB` 的差值 21MB 已在 `gate-margin-r618.json` 落盘。
7. 一跑次 0/58 由 D1 造成、另一 0/58 由 D3 造成 ⇒ 两个 0 不同源，不得合并叙述。

## 7. 下轮候选（第三刀，待用户裁定是否继续此路径）

| 候选 | 动作 | KPI 影响 | 前置 | 判据 |
|---|---|---|---|---|
| C1 | 空候选/键未到达 ⇒ **回退 `plan`**（消除 D1 形态） | 质量（↑，回溯 R618 两枚 0/58 之一） | 轴仍默认 off | 同窗对照 ∧ 逐跑次 `exec_source` 取值三态（`candidates`/`plan`/`plan_fallback`）∧ 零回归（轴关逐位） |
| C2 | 候选**序/依赖**面（写盘先于执行、窄腰依赖排序） | 质量（↑，D2 靶点） | C1 落定（禁双自由度） | 同窗 reps≥3 ∧ 逐窗 + 中位 + 极差 ∧ 早期退出步次可见 |
| C3 | 信息类工具（`read_file`/`list_dir`）的**回执走尾部载体** | 质量 / 轮数 | C1/C2 落定 | 回执行面接线 ∧ 冷/热成本分解 |
