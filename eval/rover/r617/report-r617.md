# R617 报告 · 提示尾块单变量第二档：`豁免句 → 必声明句`（J1 声明面抬升的可归因化）

轮次：R617 ｜ 协议：`docs/plans/RF0005-completion-protocol.md` §2 固定环 0–9 ｜ 窗集：**w205..w207**（与历史窗集 w184..w204 不相交）
被测件：`$HOME/.agentframework/artifacts/pub_r617/agenthost`（sha256 `cd7c8dca2ae252c1a1b220a73152ff8eb041f82e271e963488105fc9ab994b44`，19,817,472 B；`bin_sha_stable=true`）
判据器：`eval/rover/r617/judge_r617.py` ｜ 预注册：`eval/rover/r617/prereg-r617.json`（先写后跑）｜ DAG：`eval/rover/r617/dag-r617.md`
臂：T×9 / C×9 / C1(codex 真值)×3 = 21 跑次 ｜ 题集 sha16 `e0c667c2a313c04b`（与 R600–R615 逐字节同）

## 0. 一句话

**机制面 PASS**：唯一单变量（尾块豁免句 → 必声明句）把「有声明跑次」从 R615 的 **2/9** 抬到 **9/9**（C 档同窗仍 2/9）；**能力面只作并列**（整题全对 T 6/9 vs C 3/9 vs 真值 3/3，但 J5 跨窗集方向翻号 ⇒ 欠功率）；**成本面 completion +39%**（66,509 vs 47,716）⇒ 铁律 11 未可验收，降幅一律标「参考」。

## 1. 起手闸与前置（先证器具可用，再读被测）

| 条目 | 读数 |
|---|---|
| `roundcheck preflight --round R617` | rc=0（P1 key / P2 weights / P3 mem 2,859MB / P4 disk 5GB / P6 轮号未占 / P7 R617 空闲 / P8 PUSH_PAUSED=yes；**P5 WARN = 本臂自身在飞 agenthost**，非对侧写者） |
| 起手闸 A1/A2 | PASS（`ceiling=2795 / prev_swing=70 / margin=70 / REQ=2720`；A1 mem 2,905MB、A2 2,908MB） |
| 判别力成对控制 | rc=0（0 真判别行使 / 3 未行使已如实登记） |
| leak-selfcheck | rc=0 |
| 同输入硬门 | 两侧夹具逐字节同（题集 sha16 `e0c667c2a313c04b`） |
| 臂身份 | 全臂同一二进制（pinned sha 上式）+ 运行期 `bin_sha_stable=true` |

## 2. 本轮做了什么（产品侧最小改动 + 器具）

| # | 改动 | 位置 | 性质 |
|---|---|---|---|
| 1 | 尾块措辞：删去「plan 已表达的写文件/执行步骤**不要**在本字段里重复声明」⇒ 改为「**执行面只读本字段**（必声明）」 | `tools/r1gen/r1prompt.py`（`ACTION_CANDIDATES`） | **被测单变量** |
| 2 | 对照臂载体：R615 现盘尾块**逐字节**副本（由 `git show HEAD:` 派生，禁手抄）+ 轴取值 `AGENTFRAMEWORK_R1_ACTION_PROMPT ∈ {unset, r615}`（legacy 档仍在册，本轮不作臂） | 同上 + `tools/r1gen/gen_csharp.py` → `src/agent/contract/StructuredPrompt.cs` | 对照臂 / 器具 |
| 3 | 键**到达面**遥测（`action_candidates_present`）**两臂同开**（非被测变量；R615 口径的到达面解耦在本轮沿用） | `src/agent/r1/*`（R615 已接线，本轮不改） | 器具 |

**只加厚不变量**（`eval/rover/r617/prefix-r617.json`）：chars **15794 → 15796**（+2）；T pin sha `25c97bef…`（新块）· C pin sha `8b8be6b8…`（= R615 现盘块，亦即 R615 冻结 pin）· legacy 锚 `a9792fdb…`（chars 15675）。
**轴关等价**：C 档前缀 = R615 现盘块**逐字节**（sha 与 R615 `F_env.prefix.sha256` 同值）⇒ 「轴关 = 旧行为逐位等价」由 J0 逐跑次机检。

## 3. 真机读数（w205..w207）

### 3.1 J0 臂轴生效（fail-closed 器具闸）

| 臂 | 跑次 | prefix_sha256 集合 | 缺席 |
|---|---|---|---|
| T | 9 | `25c97bef…`（9/9） | 0 |
| C | 9 | `8b8be6b8…`（8/9） | **1**（`w207/agentC-r3` = rc=124 超时，无 transcript） |
| C1 | 3 | 无本仓前缀遥测（codex 臂，不入本判据） | 3 |

J0 = **PASS**（`A_T_pinned ∧ B_C_pinned ∧ C_disjoint ∧ D_telemetry_coverage`；缺席跑次**单列** `instrument_gap`，不判红、也不吞掉）。

### 3.2 J1 机制面（主判据，预注册阈值）

| 指标 | T（新块） | C（R615 块） | R615 基线（同判据） |
|---|---|---|---|
| 到达跑次（present=1） | **9/9** | 7/9 | T 8/9 / C 0/9 |
| **有声明跑次（declared>0）** | **9/9** | **2/9** | T **2/9** |
| 到达但空数组 | **0** | **5** | T 6/8 |

判据（预注册）：`T 有声明 ≥ C 有声明 + 2 ∧ T ≥ 2` ⇒ **PASS**。归因成立：R615 的「到达但空数组 6/8」病灶就是那句**豁免句**（改后空到达降为 0）。

### 3.3 J2b 逐条裁定守恒（机械）

T 9/9 跑次 `accepted + rejected == declared`（例：w205-r1 declared 10 = accepted 9 + rejected 1），守恒违例 **0** ⇒ **PASS**。

### 3.4 J4/J2 能力面（并列，不作结论）

| 臂 | 整题全对 | 用例级 | 逐窗全对 | Wilson95 |
|---|---|---|---|---|
| T | 6/9 = 0.667 | 498/522 = 95.4%（[48,58,52,58,58,58,50,58,58]） | 1/3 · 3/3 · 2/3 | [0.354, 0.879] |
| C | 3/9 = 0.333 | 491/522 = 94.1%（[58,47,44,47,56,58,56,58,**0**]） | 1/3 · 1/3 · 1/3 | [0.118, 0.647] |
| C1 真值 | **3/3 = 1.0** | 174/174 | 1/1 · 1/1 · 1/1 | — |

- C 的 `0/58` 即 `w207/agentC-r3` **rc=124 超时**（turn 1 被杀，无产物无遥测）⇒ **剔除后 C = 3/8 = 0.375**，两列并列。
- J4 预注册判据「T ≥ C+1 ∧ 无窗下降」= PASS，但 **J5 跨窗集方向翻号**（R615 池化 T−C = **−0.1111** vs 本轮 **+0.3334**）⇒ 窗集依赖、欠功率，**能力面只作并列**。
- 任务面 v3：`C1_task_face_v3` PASS（D_list [−6,0,0]，中位 0，floor −15/−2 未触）；`W_floor` 有效窗 3 ⇒ 判据行使。

### 3.5 J3 成本（三列分列；铁律 11 未过 ⇒ 参考）

| 臂 | 调用 Σ | 新算 prompt Σ | 单位调用新算 | completion Σ | 命中率 v_all 中位 | v_incr 中位 | bad_dumps |
|---|---|---|---|---|---|---|---|
| T | 16 | 15,430 | **964** | **66,509** | 0.9034 | 0.8394 | 0 |
| C | 17 | 15,845 | 932 | 47,716 | 0.9007 | 0.8367 | 0 |

J3 形态 v2（a1∧a2∧b1）= **FAIL**：`b1 单位调用新算 prompt` T 964 > C 932（+3.4%）；
**completion +39.3%**（声明句 = 更长输出，是本次机制的直接代价，如实入档）。
判据口径 = 中继 dump 时间轴 `v_all / v_incr`；`bad_dumps=0`。

### 3.6 铁律 11 可验收前置（`exec_precondition.py --round r617`）= **rc=1（未可验收）**

21 臂全部**独立物化 + `python3 -I -B` 实跑隐藏用例 + 逐条机械判对**；`SELF_REPORT_AGREES=True`（判据器自报与独立实跑一致）∧ `EXECUTABLE_AND_CORRECT=False`。
- **blocked 9 臂**（同一臂-题不许有错）：`w205/C-r2 47/58`、`w205/C-r3 44/58`、`w205/T-r1 48/58`、`w205/T-r3 52/58`、`w206/C-r1 47/58`、`w206/C-r2 56/58`、`w207/C-r1 56/58`、**`w207/C-r3 rc=124 0/6`（超时，与遥测缺席同源）**、`w207/T-r1 50/58`。
- **codex 真值臂 3/3 窗全对**（58/58）⇒ 未通过面**非本侧独有**；主失败族 = `wythoff#43..#57`（承 R615）。
- 结论：**成本/降幅一律「参考（未可验收）」**（`precond-r617.json` / `logs/precond.txt`）。

## 4. 文献小步（第 2 步；检索 ≤3 次 / 全文 ≤2 篇）

| 检索式 | 出处（含版本） | 采信/结论 |
|---|---|---|
| `"abstention" tool routing on-device` | arXiv **2609.18672v1**（2026-09-16 · comment: 12 pages, 4 figures, 13 tables） | **采信 C7**：`Abstention, not selection, is where a neural component is required.` ∧ `constraining a decoder to a tool grammar repairs malformed output without improving the choice` ⇒ ① 本仓弃权面**实测更正**：`RecognitionVerdict.cs:9-21` + `RecognitionOutlet.cs:3-19`（只读渲染器，缺省 on）消费点 `IndustrialAgentV2.cs:1880-1899` ⇒ 弃权面**已接主链但非独立决策**；② 该文预测「形态类约束抬形态、不抬选择质量」与本轮 J1↑/J4 欠功率**方向一致**（外部旁证，不作收益证据） |
| `"prompt prefix cache" reuse` | arXiv **2609.19969v1**（2026-09-17） | **不采纳（本轮）**：KV 驻留/低位缓存由上游决定，本仓无可动旋钮 ⇒ **不假装有牙** |
| （首条检索式命中 1,087 条 ⇒ 短语未被 API 收紧，已如实标注；近月预印本 cited_by_count 恒 0、S2 无 key 时 429 ⇒ **引用数不可用**） | — | 台账 `docs/research/lit-review-ledger.md`（追加 2 行，`+2 −0`） |

**反空转计数**：本轮 采信 1 / 不采纳 1 / 证伪 0 / 顺延 0；连续 0 采信轮数 = **0**（R615 第 1 轮已清零）。

## 5. 自捕器具/流程缺陷（均修，**读数未重测**，首跑件原样保留）

| # | 缺陷 | 形态 | 修法 | 取证 |
|---|---|---|---|---|
| **I1** | 判决器 v1 **崩整轮汇总** | `judge_r617.py` J0 对 `sorted({None, str})` ⇒ `TypeError`，KPI 汇总 rc=1、无判决件（14:14 日志 Traceback 在案） | 缺测哨兵 `∅` + 覆盖度列（`D_telemetry_coverage`）+ `instrument_gap` 单列；pin 判定只取有遥测者 | `eval/rover/r617/nc_j0_r617.py` 正/负控 4 例 **rc=0**（PC 真 ∧ NC1 单次缺席仍真且 gap=1 ∧ NC2 轴未分离假 ∧ NC3 全臂缺席假） |
| **I2** | 铁律 11 首跑 **BLOCKED=材料缺口** | `eval/rover/r617/cases/` 缺 `run_cases_r521.py` ⇒ 21 臂全 `missing_case_script`（判 BLOCKED 而非 FAIL，fail-closed 正确） | 从 `eval/rover/r615/cases/` **逐字节**补齐（sha `d9aecf4d397550b8…` / `270128eb85c7afc0…`，与 r610 同值）⇒ 重跑后处理（**不重测**） | 重跑 rc 见 `precond-r617.json`；两次运行同路径 ⇒ 覆盖已披露（I3） |
| **I3** | 首跑读数被同名覆盖（流程） | 两次 `--out precond-r617.json` 同路径 ⇒ 首跑 BLOCKED 明细仅存于会话记录与本节叙述 | 下轮起派生物名带 `-v1<原因>` 后缀（承 R587 纪律） | 本节即披露面 |

## 5b. 门禁读数（本轮收口）

- **build 读数**: `dotnet test` 构建 **0 error**（仅 NU1510 警告：System.Text.Json 显式引用）。
- **形式门禁 14/14**（`VerificationForm|SkillGeneralization|DevPlanDocRef` 过滤集）· 承重面定向 **36/36**（`R524PrefixStability|ActionCandidates|Recognition`）· `Supplement` **10/10**。
- `status_gen.py --check` **PASS**（违规 0 / 基准漂移 0 / 缺源 0）· `decl_sweep --check` **0 漂移** · `gen_csharp.py --check` **R1GEN_DRIFT_FILES=0**。
- `roundcheck audit --round R617`：R1–R5/R7/R10–R12 PASS；**R6 FAIL（169 文件 > 40）= 归档轮代理判据**（与本轮 21 臂逐窗快照归档同源，与 R614 的 162 文件同形态）⇒ 按治理四件套登记为 R617 作用域例外（见 `tools/roundcheck/baseline.json`）；**R8** 首跑缺读数面 ⇒ 本段补档（真实缺档，非豁免）。R9 WARN = 提交后暂存面为空，expected。

## 6. 诚实边界

1. 机制面只证「措辞决定**声明面**」；**不证能力/成本收益**（J5 方向翻号 ⇒ 能力面并列）。
2. 成本与降幅一律 **参考（未可验收）**（铁律 11 未 rc=0）。
3. `w207/agentC-r3` rc=124 超时 = 已知现象（R615 候选 ④）本轮**复现 1 例**；剔除后读数已并列给出。
4. 三档终局目标读数（32 ms / 快 50× / −95% / −85~91%）本轮**不动不宣称**（铁律 14）。
5. `M3 出口闸`（调用数按 request_id 去重 ≤ 旧臂 50%）**本轮不判**：`accepted` 目前只有声明没有执行接线（第二刀）。
6. 本轮为**被测件变更轮**（`src/` + `tools/` 有改动、AOT 重发布）⇒ 与 R585–R616 冻结件轮 **禁相减、只并列**。

## 6b. 候选台账（R616 下发候选 → 本轮处置；禁挑选式汇报）

| 候选（R616 下发） | 状态 | 读数 / 原因 |
|---|---|---|
| ① **豁免句单变量**（最高优先） | **本轮完成** | 有声明跑次 **2/9 → 9/9**（C 同窗 2/9）；「到达但空数组」**6/8 → 0**；J1 判据 PASS |
| ② **M3 第二刀 = 执行面接线** | **未做（前置未闭合）** | `accepted` 消费者数仍 0；未放行的产品分支改动不许动，且前置（声明到岸 9/9）本轮才刚闭合 ⇒ 转 R618 首位 |
| ③ **wythoff 族双侧共同缺口** | **未做（非同源，须先判夹具）** | R615 的判据是「真值也失分」；本轮**真值臂 3/3 窗 58/58 全对** ⇒ 前提变了，先判题面/夹具（R512 教训）再谈能力，转 R618 |
| ④ **`rc=124` 超时是否复现** | **本轮已复现 1 例并单列** | `w207/agentC-r3` rc=124（turn 1 被杀 ⇒ 无产物无遥测 ⇒ 质量分母须单列）；阈值未调 |
| ⑤ **铁律 11 可验收面**（多臂全绿/显式降级） | **本轮部分推进** | 器具面：判据器**缺席单列**（`instrument_gap`，缺席不判红也不吞掉）+ 铁律 11 首跑 BLOCKED 类缺陷修复；判据面（可验收阈值）未改、仍 rc=1 |
| ⑥ **completion +39.3% 的代价**（本轮新增候选） | **转 R618** | 声明句直接代价；候选 = 声明面格式压缩或复用 plan 的 id/字段 |

## 7. 产物清单

`eval/rover/r617/{dag-r617.md,prefix-r617.json,prefix_r617.py,prereg-r617.json,run_r617.sh,judge_r617.py,nc_j0_r617.py,aot_r617.sh,taskset-r617.json,bins-r617.json,gate-margin-r617.json,cases/,snapshots/,evidence/,report-r617.md}`
＋ 判决件 `verdict-r617.json` · KPI 表 `kpi-table-r617.json` · 台账 `eval/capability/kpi.jsonl`（R617 行，带 `baselines`）· registry 行 `r617.prompt-tail-block-mandatory-declaration` · 文献 `docs/research/lit-review-ledger.md`。
