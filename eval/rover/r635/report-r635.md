# R635 · 主线对照轮（新窗集 w231..w233）· 轮报告

- **轮次**: R635 · 2026-09-22 · 前置锚 = R634b（`a436b69a`）
- **性质**: 主线对照轮（**无单变量轴** ⇒ 测量轮，预注册自陈 ⇒ 禁计为单变量轮、禁跨轮相减）
- **零产品源码改动**（`git diff --stat src/` 空）· **零新增夹具** · **零新增开关** · 零远端新增形态 · 跳步「构建/AOT」（无新二进制可构建）
- **被测件**: `/home/agentuser/.agentframework/artifacts/pub_r630/agenthost` sha256 `cefd045e8d1d…ba19`（19,870,960 B）∧ `bin_sha_stable=true`（起臂前后同 sha）
- **外部真值件**: codex `61b0194f3bb6…cf70`（8,790 B）
- **题集**: 逐字节冻结件（文件 sha `e0c667c2a313c04b…` / payload sha `e7ddce02f75d2e3e…`），与 R610–R634 同值；aux 同批携带（`run_cases_r521.py` sha16 `d9aecf4d397550b8`）
- **窗集**: **w231 / w232 / w233**（与历史 w184..w230 不相交；窗集只增不复用）
- **臂**: 每窗 = 产品默认档 ×3（P，剂量键全 unset）+ codex 外部真值 ×1（C1）⇒ 12 跑次
- **held-constant 前缀锚**: `a9792fdbe5b2…`（legacy 档；M1 面 9/9 逐跑次命中，缺项 0）

## 1. 起手闸与前置

| 面 | 读数 |
|---|---|
| 起手前采样 | ceiling(min of 3) = 2841MB · spread = 1MB |
| 条款 | `MARGIN := clamp(prev_swing, 60, CEIL−GATE−floor)`；prev_swing = **75MB**（源 = R634 在飞窗 run-samples n=54 min 2772 / max 2847）⇒ MARGIN=75 / REQ=2725（cap=131，cap_binding=false） |
| A1 / A2 | PASS（2843MB / 2823MB ≥ 2725MB） |
| leak-selfcheck | rc=0 |
| 前提闸 | PASS（前缀锚 `a9792fdbe5b2…` + 计划面 `plan_steps_total=14`） |
| 先写后跑闸 | prereg ok：arms=[C1,P] · windows=[w231,w232,w233] · scope_require=12 · policy=`truth_arm_window_unavailable` |

## 2. 判据读数（预注册 v6-scope-and，照原样判）

- **M1 锚面前提 PASS**：`applicable_face` 9/9 跑次有提示面且 == 锚；`missing_runs=[]`（无超时跑次）⇒ 无缺席、无漂移。
- **Q1（主判据）PASS**：逐窗配对差 **D = [0, 0, 2]**（中位 **0**）；阈值 = 中位 ≥ −2 ∧ 逐窗 ≥ −15 ⇒ 中位与逐窗双过。**有效窗 3**（`W_floor` PASS）。
  - 逐窗：w231 P 中位 58 / C1 58；w232 P 58 / C1 58；w233 P 58 / C1 56。
  - 真值自败例单列：`truth_self_failed_cases` = w231 codex 0 / w232 codex 0 / **w233 codex 2**（`wythoff#55-hidden`、`wythoff#57-hidden`）⇒ 按本轮 `unreliable_policy` B1（窗有效 = 真值跑通 ∧ 非自败例 ≥1）**不构成窗失效**；该真值臂同时被 `policy_demoted`（`unreliable_excluded`）从验收面移出并单列 `unreliable_windows=[w233/codex]`。
- **Q2（次级）PASS（非回归）**：整题全对 P **8/9 = 0.8889** vs C1 **2/3 = 0.6667**（`P_rate ≥ C1_rate`）。
- **判据器影子自检 6 态 rc=0**（`selftest-r635.json`）：`EQUAL` / `WORSE_BY_3` / `MISSING_TRUTH`⇒NO_RESOLUTION / **`TRUTH_SELF_FAIL_NOW_VALID`**（B2 ①：自败但跑通 ⇒ 有效窗 3）/ **`TRUTH_VOID`**（B2 ②：真值挂死 ⇒ 有效窗 2 ∧ w232 剔除，证明修正**不放宽**另一侧）/ `ANCHOR` 两侧样例 —— `all_ok=true`。

## 3. 铁律 11 可执行前置器（`exec_precondition.py --round r635`）

**rc = 1**（`ACCEPTABLE_SCOPED=False`）· `SCOPE_SOURCE=eval/rover/r635/prereg-r635.json` ∧ `PREREG=True`（承 R634 E2 的修正形态：验收面显式声明，**未**事后 `--scope` 补声明）· `POLICY_ACTIVE=True`（A2/A3 时序检查全 true）· `SELF_REPORT_AGREES=True`。

- 验收面（require，12 项）= 3 窗 × {agentP-r1, agentP-r2, agentP-r3, codex}
- **blocked_scoped（1 项）**: `w232/agentP-r2/g1` rc=1 · **43/58** · failed = `wythoff#43-public, #44-public, #45..#57-hidden`（**15 例 = 整族**）
- 全局 blocked（2 项）：上一项 + `w233/codex/g1` 56/58（真值臂，**非验收面**，已 `policy_demoted`；差额单列 `NONREQUIRED`）
- ⇒ **质量/成本读数一律标「参考（未可验收）」**，禁作验收依据。

## 4. 成本三列（口径 = 中继 dump 时间轴；跨轮禁相减）

| 臂 | n | 调用 | 新算 prompt | completion | v_all 中位 | v_incr 中位 | 每跑次调用 | 每跑次新算 | 每跑次 completion |
|---|---|---|---|---|---|---|---|---|---|
| P（产品默认档） | 9 | 18 | 16,639 | 44,653 | 0.9039 | 0.8407 | **2.00** | **1,849** | **4,961** |
| C1（codex 真值） | 3 | 36 | 22,806 | 14,944 | 0.9201 | 0.9306 | **12.00** | **7,602** | **4,981** |

- **口径诚实（本轮新登记）**：P 与 C1 的**跑次数不等（9 vs 3）**⇒ 三列**总和**是异分母口径（历史沿用），**并排时必须同时给每跑次归一列**。归一后读数：调用 **−83.3%** · 新算 prompt **−75.7%** · completion **−0.4%（实质持平）** ⇒ **不应读作「completion +199%」**（那是分母产物）。
- `bad_dumps = 0`；VOID 跑次 0 条。
- 步数面：P 逐跑次 `steps_executed/plan_steps_total` = 7/7 · 16/16 · 7/10 · 7/7 · 7/10 · 7/10 · 7/14 · 16/18 · 7/7；rc/stage = `8 self_test_unmet` ×3 / `5 expect_stdout_exhausted` ×6 / `5 run_rc_exhausted` ×1（C1 面 `n/a`：外部 CLI 无该转录字段）。
- **摆动 ≥ 效应**：C1 自身跨轮成本摆幅（R634 25 调用 → R635 36 调用，**+44%**）大于任何臂间差 ⇒ 成本面**不作结论**，只作并列读数。

## 5. 逐例归因（blocked 臂 `w232/agentP-r2`）

- **性质 = 能力面**，非器具面：① 同一枚二进制其它 8 个 P 跑次全 58/58；② 同窗真值 `w232/codex` **58/58 全对** ⇒ 夹具可判、真值可达（R512「两侧同败 ⇒ 疑夹具」判据**不成立**）；③ 失败集合集中于**单一族**（wythoff 15 例）。
- **分数结构**：一模块/一族的缺陷带走整族（15/58）⇒ 用例级分数对单族缺陷极敏感；中位口径（58）**看不见**该跑次 ⇒ **中位判据必须与 `executable_and_correct`（逐臂-题）成对读**，这正是铁律 11 挡住「中位 PASS = 达标」假绿的位置。
- **族分列（P，9 跑次）**：wythoff 族 **8/9 跑次全过**、1 跑次 43/58；其余族（life / nim / sub）**9/9 全过**。
- **与历史对齐**：wythoff 族 = R621/R622 登记的**承重缺口**（R622 定因：冷点谓词/胜负态判定层 90.6%）；本轮**未做**机制归因（本轮为测量轮，无产品改动）⇒ 只登记「复现一次」，不沿用旧结论定因。

## 6. 自捕与诚实边界

- **自捕 1 条（登记行形态，同轮修，判据零放宽）**：registry 新行首跑被形式门禁判红 **13/14** —— `VerificationFormTests.Registry_Exists_And_HasNoViolations` 报两条：① `R2c`：`covers` 里一条**叙述性条目含半角斜杠**（「总和 / 每跑次归一」）⇒ 被当作路径解析 ⇒ 判「路径不存在」；② `R2e`：`pin_status=live` 的行**不得带 `artifact_sha12`**（R634 同处置 = `null`），我按「pin 即钉 evidence 字节」的直觉填了值 ⇒ 判违规。修法 = 叙述条目去斜杠 + `artifact_sha12=null`（**阈值/判据一字未动**，只改登记行形态；改前用「序列化器逐字节复现原文件」断言保形）⇒ 重跑形式门禁 **14/14（Failed 0 / Passed 14）**。教训入册：**`covers[]` 是纯路径清单**，叙述性说明不得混入（含 `/` 即被当路径）；**「live 行」的 pin 语义 = 不钉字节**，字节钉只属冻结件行。
- 跳步「构建/AOT」：无新二进制可构建（零 `src/` 改动）。
- 跳步「roundcheck audit」（声明式）：R635 是**逐窗归档轮** ⇒ 提交面 113 文件 > `R6_commit_hygiene` 的裸计数阈值 40；而 `tools/roundcheck/baseline.json` 里同形态条目（R614/R618）`expires_round=R625` **已期满**，按「过期回红 ∧ 抑制只许减」**不新增抑制**（不为凑绿加基线）。⇒ 收口判据由 `status_gen.py --check` **PASS** + 形式门禁 **14/14** 承担，与 R633/R634 同处置；audit 另作**只读**复核（结果不入本轮提交面）。
- 诚实边界：
  1. **铁律 11 rc=1** ⇒ 全部质量/成本读数**未过可验收前置**，标「参考（未可验收）」；
  2. **无单变量轴** ⇒ 只作「同件同题集、新窗集」并列面，**禁跨轮相减**；R634 D 中位 −3（不达）与本轮 D 中位 0（达）**只并列**；
  3. n=9（P）/3（C1）**欠功率**，单窗不作结论；摆动 ≥ 效应（成本面）⇒ 不作结论；
  4. 主判据 Q1 PASS **不得**读作能力达标 —— 同批 1/9 跑次整族失败（wythoff 15 例）且被铁律 11 拦下；
  5. 真值非硬上限：w233 真值自败 2 例已单列，`unreliable_windows` 只影响对照列标注、**不**影响本侧臂判读（策略只对本轮声明之后产生的窗生效，**拒绝追溯**）；
  6. 三档终局目标读数（32 ms / 快 50× / −95% / −85~91%）本轮**不动不宣称**。

## 7. 下轮候选（R636）

① **wythoff 族单变量修法轮**（承重缺口；先预注册 + 引 `baselines`；须先读 R622 已定因的判定层，**禁**沿用旧结论直接改法）；② **验收面成员与真值自败的交互**（本轮 `policy_demoted` 只移真值臂，`w232/agentP-r2` 仍 blocking ⇒ 是否给「本侧单跑次整族失败」设独立分类，须新预注册）；③ 「中位 PASS ∧ 逐臂失败」并读的判据形态入册（防中位口径掩盖族级失败）；④ 文献候选（对抗/自合成用例面）**须放行**方可实施。
