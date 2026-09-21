# R619 报告 · RF0004.2 · M3 **第三刀 = 空执行面回退**（采纳集映射出空执行面 ∧ plan 非空 ⇒ 回退读 plan + 原因码入台账）

- 轮次：**R619**（2026-09-21）｜协议：`docs/plans/RF0005-completion-protocol.md` §2 固定环 0–9
- 单变量：`AGENTFRAMEWORK_R1_ACTION_EXEC`（治疗档 =1 / 对照档 unset = 产品缺省）——**唯一自由度**
- 窗集：**w211..w213**（与历史窗集 w184..w210 **不相交**）｜臂：T×9 / C×9 / C1(codex真值)×3 = **21 跑次**
- 预注册：`eval/rover/r619/prereg-r619.json`（**先写后跑闸**在 runner 内机检：arms/require=7/criterion v3/windows）
- 判决件：`eval/rover/r619/verdict-r619.json`｜KPI 表：`eval/rover/r619/kpi-table-r619.json`｜前置器：`precond-r619.json`

## 0. 一句话

**机制面 PASS（rc=0 / mechanism_rc=0 / 判据全绿），但第三刀的回退分支本轮零行使（`J1e=NOT_EXERCISED`）⇒ 回退机制本身「未测到」，不得宣称有效**；能力面 T 6/9 vs C 5/9 vs 真值 3/3，逐窗 +0.333 / −0.667 / +0.667（极差 1.33 ⇒ 欠功率）；铁律 11 rc=1 ⇒ 一切质量/成本读数标 **参考（未可验收）**。

## 1. 起手闸与前置

| 项 | 读数 |
|---|---|
| 首试（18:45:34） | **RUN_EXIT=2 fail-closed**：ceiling 2687 − GATE 2650 = 37MB < 60MB 下限 ⇒ 窗口不可开；**零臂起跑、无任何测量读数**（该次不入对账） |
| 清场动作 | `dotnet build-server shutdown` + 释放本会话两个 LSP 进程（pyright 165MB / bash-ls 125MB）——**未拆共享编译服务、未杀对侧进程** |
| 余量条款（**runner 派生·唯一来源**） | ceiling(min of 3)=2888、prev_swing=125、**margin=125、REQ=2775**、cap=178、cap_binding=false、spread=0MB |
| 起手闸 A1 / A2 | PASS（2905MB / 2909MB ≥ REQ 2775） |
| 判别力成对控制 | rc=0（3 = 未行使，已如实登记） |
| 起手闸 B（leak-selfcheck） | rc=0 |
| 先写后跑闸 | prereg ok：`arms=['C','C1','T'] require=7 criterion=v3 windows=['w211','w212','w213']` |
| 臂身份 | 全臂共用同一枚二进制 `pub_r619/agenthost` sha256 `a184d7317b6e3c5e2190c792c88da265fdb86da594dde959a2a8389c546424af`（19,838,192 B）∧ **bin_sha_stable=true**；codex sha256 `61b0194f3bb6534439c8d26a3ed57d0805f84b8…` |
| 题集 | `taskset-r619.json` = r618 件**逐字节**复制（sha256 `e0c667c2a313c04b2d87ac06fcba9f50166a4a0be5d5162cabdbf520d9d3927a`） |
| AOT | `PUBLISH_RC=0 IL_WARNINGS=0 ERRORS=0`；**生产档装载冒烟两档**（轴 off / 轴 on）各 rc=0、out_bytes 1258 / 1430（轴 on 档可见 `exec_source":"candidates"` 且 `exec_fallback` **缺席** ⇒ 零回归不变式在冒烟面已成立） |

## 2. 本轮做了什么（产品侧最小改动 + 器具）

1. **回退判定抽成纯函数**（可单测、无副作用）：`ActionExecPlan.Decide(mapped, plan, present, accepted) → (Source, Fallback, UsePlan)`；三态原因码 = `candidates_absent` / `accepted_empty` / `unmapped_all`。
2. **唯一接线点** `R1Pipeline.cs`：`face.UsePlan ? sem.Plan : map.Steps`；轴关 ⇒ `execPlan == sem.Plan` 逐位等价（既有行为不变）。
3. **台账新增** `exec_fallback`（`R1RunResult` + `R1Transcript` 紧凑 JSON 与 pretty 台账两处）；**仅回退时落该字段** ⇒ 轴关或未回退时台账与 R618 **逐字节同**。
4. **单测** `src/agent.tests/ActionFallbackTests.cs` 7 条：三态正控（absent / empty / unmapped_all）+ 负控（有可执行节点 ⇒ 不回退）+ 边界（两侧皆空 ⇒ 不回退，走既有空面出口）+ 零回归条（轴关 ⇒ 两字段皆不出现）+ 台账渲染条。
5. **判据器** `judge_r619.py`：J1 增 **J1d**（D1 形态清零：`candidates ∧ executed==0` 跑次必须为 0）与 **J1e 三态**（`NOT_EXERCISED` / `EXERCISED_OK` / `EXERCISED_EMPTY`，**仅第三态判红**）；逐跑次行增 `fallback` 列。
6. **影子自检 8 态** `selftest_judge_r619.py`：新增 F（回退行使且真干活 ⇒ 绿）/ G（回退命中而执行面仍空 ⇒ **必须红**）/ H（D1 形态 ⇒ **必须红**），三态均保留 `rep1 = candidates ∧ executed>0` ⇒ 被隔离的是 J1d/J1e 本身。
7. **器具面自捕缺陷 I1（本轮最贵的一件，由影子自检当场抓到）**：新键 `exec_fallback` 只并入 `EXEC_FIELDS`（缺席检测面）而**未并入读取契约 `TR_FIELDS`** ⇒ 白名单外键静默读空 ⇒ F 态 `fallback_reason_set=[]` **假红**。修法 = 两处同时并入（承 R617/R618 同族缺陷教训）；修后 8 态 `checks_failed=[]`、rc=0。
8. 其余器具**逐字派生**（`derive_judge_r619.py` / `derive_selftest_r619.py` 头部逐条声明差异，锚点必须命中否则 fail-closed）：J2b/J2/J3v1/v2/J4/J5/W_floor/LD/C1-v3 阈值与判据**一字未改**。

## 3. 真机读数（w211..w213，21 跑次）

### 3.1 J0 臂轴生效（fail-closed 器具闸）——**PASS**

T 档面集合 `A_T_face_set=['candidates']`（⊆ 允许面）、C 档**五个受闸字段全缺席 9/9**、两臂 `prefix_sha256` **同源** `25c97bef…`（= R617 pin ⇒ r1gen 零改动，**跨轮锚成立**，`claims_violated=[]`）、遥测覆盖 T/C 各 9/9、`instrument_gap=[]`。两档**可区分** ⇒ 后续 J1 的任何差异可归因到该轴。

### 3.2 J1 执行面消费面（**主判据**）——**PASS**

| 读数 | T 档 | 说明 |
|---|---|---|
| 面 = candidates | **9/9** | J1a 成立 |
| `executed>0` | **9/9** | 执行面真被驱动 |
| 条目守恒（违例） | 9/9（**0**） | `unmapped<=accepted ∧ executed<=accepted−unmapped ∧ inherited<=accepted−unmapped` |
| `unmapped` 合计 / 期望继承合计 | 0 / **39** | 窄腰外工具未静默丢；换载体未丢自检面 |
| **J1d** 形态清零 | **True**（`candidates ∧ executed==0` 跑次 = **0/9**） | R618 实测该形态 1/9 ⇒ 本轮窗口集未复现 |
| **J1e** 回退三态 | **`NOT_EXERCISED`**（`plan_fallback` 跑次 **0/9**） | **回退分支本轮零行使 ⇒ 如实记「未测到」**；既**不判 PASS**（禁把未测读成通过）也**不判红** |

> **口径纪律**：J1e = NOT_EXERCISED 时，**不得**把「机制面 PASS」读成「回退机制有效」。本轮可宣称的只有「J1d ∧ J1a-J1c ∧ J2b」。

### 3.3 J2b 裁选守恒 —— **PASS** ｜ J2 修复收敛 —— 不达（继承面）

J2b：T 档有声明跑次 > 0 ∧ 逐跑次 `accepted+rejected==declared`（违例 0）。J2：T converged **3** vs C **2**（`T_converged >= C_converged + 1` 未达；继承面，非本轮单变量所改）。

### 3.4 J3 成本面（**参考，未可验收**）

- **J3 v1 PASS**（`T_max_calls <= C_max_calls`）；**J3 v2 FAIL**：`failed_clauses=[a2_per_window_calls:w212, b1_unit_new_prompt]`。
- 单位调用新算 prompt：**T 826.5 vs C 735.84**（T 更差）；池化调用 Σ T 18 vs C 19；新算 prompt Σ T 14,877 vs C 13,981。
- 结论：**成本面无收益**（不作降幅宣称；M3 出口闸「调用数去重 ≤ 旧臂 50%」本轮**只作读数**，分母跨形态不同源，禁相减）。

### 3.5 J4/J5 能力面（并列，**欠功率**）

| 臂 | 整题全对（逐窗） | 池化 | Wilson95 |
|---|---|---|---|
| T（轴开） | 3/3 · **0/3** · 3/3 | 6/9 = 0.6667 | [0.3542, 0.8794] |
| C（缺省） | 2/3 · 2/3 · 1/3 | 5/9 = 0.5556 | [0.2666, 0.8112] |
| **C1（codex 真值）** | 1/1 · 1/1 · 1/1 | **3/3 = 1.0000** | — |

逐窗配对差 `T−C` = **+0.3333 / −0.6667 / +0.6667**（极差 **1.333**）；`T−C1` = 0.0 / −1.0 / 0.0。
J5（跨窗集同方向）：池化 `T−C` 本轮 **+0.1111** vs R617 **+0.3334** ⇒ **同号 ⇒ pass**；但**极差 1.33 ≫ 效应 0.11** ⇒ 该轴在能力面**非承重**、窗口集依赖，**不作能力结论**。
**C1 任务面 v3：PASS**（`D_list=[0,−4,0]`、中位 **0**、有效窗 **3**）；LD 诊断列（wythoff#43/#57）两例 `v3_ex_LD` 也 PASS。
**W_floor**：有效窗 **3** ⇒ 判据行使（真值自败窗 0）。

### 3.6 铁律 11 前置器（收口前必跑）——**rc=1（未可验收）**

- `executable_and_correct=false`、`acceptable_scoped=false`；blocked 全局 **7** / 验收面 **28** 条（`UNDECLARED_SCOPE`）。
- 实质 blocked 例：`w211/agentC-r3 51/58 (expect 58) failed=wythoff#43-public,#44,#45-hidden,#47,#48,#49,#54-hidden` 等 **7 项** ⇒ 系**用例级失败**，非未执行。
- ⚠ **首次 precond rc=1 为「假阻断」**：21 臂全部以 `missing_case_script cases/run_cases_r521.py` 被 blocked —— 真因是**证据布局缺件**（本轮 `eval/rover/r619/cases/` 未随派生器复制；runner 本体取的正本是 `eval/rover/r610/cases/`）。处置 = 从 r610 逐字节补齐（`d9aecf4d397550b8` / `270128eb85c7afc0`，**逐字节同源**）后**只重跑后处理**（**零重测**，臂读数与二进制 sha 前后不变）；原 blocked 读数保留为 `precond-r619.layout-gap.json`。
- ⇒ 依协议：**rc≠0 ⇒ 本轮一切质量/成本读数标「参考（未可验收）」**，禁作验收依据。

### 3.7 成本与形态（细表见 `kpi-table-r619.json`）

| 臂 | 调用 | 新算 prompt | completion | 命中率 v_all | 命中率 v_incr | 步数中位 / plan 中位 | rc 分布 |
|---|---|---|---|---|---|---|---|
| T | 18 | 14,877 | 70,366 | 0.8838–0.9709 | 0.8121–0.9097（8/9 上报） | 6 / 12 | {5:6, 0:3} |
| C | 19 | 13,981 | 65,970 | 0.8947–0.9709 | 0.8305–0.9339（7/9 上报） | 7 / 10 | {5:6, 4:1, 0:2} |

命中率口径 = **中继 dump 时间轴 v_all/v_incr**；未上报条数**单列**（T 1 / C 2），**不按 0 计入**。

## 4. 失败定因（逐条可机检，不作超出证据的归因）

| 编号 | 现象 | 定因 / 状态 |
|---|---|---|
| U1 | **回退分支零行使**（0/9） | 9/9 T 跑次均映射出**非空**执行面 ⇒ 回退前提（映射面为空）本轮**从未成立**⇒ 机制**未测到**（`NOT_EXERCISED`）。**不作有效/无效结论**；下轮须造出「空执行面」窗（或按预注册的冗余布置使目标语义可命中） |
| U2 | rc=5 ×6（T）/ ×6（C）（`expect_stdout_exhausted` ×5、`run_rc_exhausted` ×1） | 与 R618 同族；**未定因**（候选序 vs plan 序差异未证）⇒ 本轮不作归因、不修 |
| U3 | 能力面 w212 T 0/3 | 单窗读数；同臂跨窗摆动（3/3 → 0/3 → 3/3）**远大于**臂间效应 ⇒ 欠功率，禁单窗结论 |

## 5. 收口五件

1. **轮工件**：本文件 + `dag-r619.md` + `prereg-r619.json` + `verdict-r619.json` + `kpi-table-r619.json` + `gate-margin-r619.json` + `bins-r619.json` + `precond-r619.json`（含 `layout-gap` 原样保留件）。
2. **证据文档**：本节 + §3 各读数（判据器/影子自检 → `judge_r619.py` / `selftest_judge_r619.py`）。
3. **registry 行**：`r619.exec-face-fallback`（L3，`closeout_r619.py` 幂等写入，写前断言「序列化器逐字节复现原文件」）。
4. **kpi 行**：`eval/capability/kpi.jsonl` 追加一行，带 **`baselines` 11 条 id**（RF0004 §4.1 引用义务）。
5. **提交**：逐文件名 `git add`（从 `git status --porcelain` 逐字取）+ 提交后回读 HEAD 关键行。

## 6. 诚实边界

- **第三刀的核心机制（回退）本轮未测到**（U1）⇒ 本轮**不可**宣称回退有效、也不可宣称无效；可宣称范围仅 = J0 ∧ J1a ∧ J1b ∧ J1c ∧ **J1d** ∧ J2b。
- **能力面负向/欠功率**：T 池化 0.6667 vs C 0.5556 vs 真值 1.0；逐窗极差 1.333 ⇒ 单窗集不作能力结论（R587 教训）。
- **铁律 11 rc=1** ⇒ 质量/成本读数一律**参考（未可验收）**；不得进验收结论。
- 被测件按设计变更（产品源码改动 ⇒ 重发布 AOT）⇒ 与 R585–R618 冻结件轮**禁相减**，只**并列**。
- 首试 fail-closed 与 precond 首跑假阻断**均如实入档**（前者零测量；后者原读数保留、修复只重跑后处理）。
- M3 出口闸（调用数去重 ≤ 旧臂 50%）只作读数：R1 链每任务 1–3 次调用，「旧臂」= 跨轮自由文本动作环，**形态不同源**。

## 7. 下轮候选（第四刀）

- **C1（必做）**：造出「映射面为空 ∧ plan 非空」的可命中窗 —— 否则回退机制永远 `NOT_EXERCISED`（本轮的实质缺口）。手段限**夹具/题面侧冗余布置**（禁改判据阈值、禁新增夹具若协议禁）。
- **C2**：U2 定因（rc=5 六例的早退点是否与执行面顺序有关）——须先证「候选序 vs plan 序」可区分。
- **C3**：J3 v2 的 `b1_unit_new_prompt` 与 `a2_per_window_calls` 列——是否降级为报告列（**须用户裁定**）。
- **C4**：成本面「少发请求」方向（按类分解先量天花板，再谈实现）。
