# R620 轮志（RF0004.2 · M3 **第四刀 = 回退分支真机行使**）

- 日期：2026-09-21 20:05–20:23（cron 60min tick）
- 协议：`docs/plans/RF0005-completion-protocol.md` §2 固定环 0–9
- 判决件：`eval/rover/r620/verdict-r620.json`（rc=2 / mechanism_rc=0）｜ 前置器：`~/.agentframework/harness/runs/r620/precond-r620.json`（rc=1）
- 预注册：`eval/rover/r620/prereg-r620.json`（先写后跑闸）｜ DAG：`eval/rover/r620/dag-r620.md`｜ 臂身份：`bins-r620.json`

## 1. 意图与单变量

R619 第三刀建立了「采纳集映射出的执行面为空 ∧ plan 非空 ⇒ **回退读 plan**」的判定与接线，但其触发前提
（候选键未到达 ⇒ 采纳面为空）在 R619 的 9 个治疗跑次里**从未成立**（`J1e = NOT_EXERCISED`）⇒ 该修复**未被真机行使**。
本轮把前提**造出来**并判「回退是否真生效」。

| 项 | 值 |
|---|---|
| 单变量 | `AGENTFRAMEWORK_R1_ACTION_EXEC`（T=1 / C=unset） |
| held-constant（**两臂同值**，机检断言） | `AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy`（legacy 尾块自带「可选 + 不声明 ⇒ 本地只按 plan 执行」豁免句 ⇒ 模型不给候选字段） |
| 窗集 | w214..w216（与历史 w184..w213 不相交） |
| 臂 | T×9 / C×9 / C1(codex 真值)×3 = 21 跑次 |
| 被测件 | **与 R619 逐字节同件**（`~/.agentframework/artifacts/pub_r619/agenthost`）⇒ **零产品源码改动** |

## 2. 起手环（0–9 依序，无跳步）

| 环 | 读据 |
|---|---|
| 起手闸 | 首试 `ceiling=2687 − 2650 = 37MB < 60MB` ⇒ **fail-closed 拒绝开窗**（零臂起跑、无测量读数，不入对账）；清场后 `ceiling=2903` 重跑首跑。条款：`prev_swing=125 margin=119 REQ=2769 cap=119 cap_binding=true spread=2MB`；A1/A2 PASS（2840/2844 MB） |
| 判别力成对控制 | rc=0（0 真判别行使 / 3 未行使已如实登记） |
| leak-selfcheck | rc=0 |
| **前提闸（本轮新增，起臂前 1 跑次）** | **PASS**：`exec_source=plan_fallback` ∧ `exec_fallback=candidates_absent` ∧ `prefix_sha256 == legacy_anchor a9792fdb…` ⇒ 触发面成立，才允许起臂 |
| 预注册 | `prereg-r620.json` mtime < 首臂时刻；runner 机检（臂键集/窗口/事件/阈值引 baselines）通过 |

## 3. 读数

**核心结论：回退分支首次真机行使 9/9。**

| 判据 | 读数 | 结论 |
|---|---|---|
| J0 臂轴生效 | T `exec_source=plan_fallback` 9/9 ∧ C 五字段全缺席 9/9 ∧ 两臂 `prefix_sha256` 同源 ∧ 前缀 == legacy 锚（held-constant 真生效） | **PASS** |
| **J1 回退行使（主判据）** | 面覆盖 9/9 ∧ **回退跑次 9**（R619 = 0）∧ 回退跑次 `executed>0` 9/9 ∧ `candidates ∧ executed==0` = 0 ∧ 三态 **EXERCISED_OK**（原因码 `candidates_absent`） | **PASS** |
| J2b 逐条裁定守恒 | legacy 档声明面结构性为空 ⇒ N/A（j2b_applicable=false，不可读作通过） | N/A |
| J3 成本（v2 三条款） | Σcalls **14 vs 16** ∧ 逐窗 ok（4/5、6/6、4/5）∧ 单位新算 **667 vs 834** | **PASS** |
| J4 能力（次级） | 整题全对 T **7/9** vs C 6/9 vs 真值 2/3（欠功率，逐窗 3/2/2 vs 3/1/2） | 并列 |
| **J6 零回归等价面** | 逐窗 rc 多重集与用例数 **T ≠ C**（w214 `[0,0,5] vs [0,5,5]`；w215 用例 `[48,58,58] vs [50,56,58]`；w216 `[0,0,5] vs [0,5,8]`） | **不成立（未判明）** |
| W 分辨率地板 | 有效窗 **2**（真值自败窗 w216：`56/58` 剔除配对、我方读数单列 58） | PASS |
| 铁律 11 前置器 | `exec_precondition.py --round r620` **rc=1**（未可验收） | 读数标 **参考（未可验收）** |

| 臂 | 调用(9 跑次) | 新算 prompt | completion | 命中率 v_all（逐跑次中位，区间） | 用例通过(中位) | 整题全对(逐窗) |
|---|---|---|---|---|---|---|
| T（轴开） | 14 | 9,340 | 34,651 | 0.9176（0.8921–0.9787） | 58 | 7/9（3/3·2/3·2/3） |
| C（轴关） | 16 | 13,349 | 40,112 | 0.9085（0.8703–0.9787） | 58 | 6/9（3/3·1/3·2/3） |
| C1（codex 真值） | — | — | — | — | 58 | 2/3（1/1·1/1·0/1） |

### 与前轮并排（**禁相减**：提示档不同 ⇒ 形态不同源，只能并列）

| 项 | R619（默认档，w211..w213） | R620（legacy 档，w214..w216） |
|---|---|---|
| 整题全对 T / C / 真值 | 6/9 · 5/9 · 3/3 | 7/9 · 6/9 · 2/3 |
| 调用 Σ（T vs C） | 18 vs 19 | 14 vs 16 |
| 新算 prompt Σ | 14,877 vs 13,981 | 9,340 vs 13,349 |
| 单位新算/调用 | 826 vs 736 | 667 vs 834 |
| **回退行使** | **0/9（NOT_EXERCISED）** | **9/9（EXERCISED_OK）** |
| J3 成本 v2 | FAIL（`a2 w212` / `b1`） | PASS（三条款） |
| rc / mechanism_rc | 0 / 0 | 2 / 0 |

## 4. 判决与两条「不成立」的如实登记

- `verdict.rc = 2`、`mechanism_rc = 0`、`label = 器具缺陷（rc=2，禁作被测结论）`。
  rc=2 的驱动条款是判据器实现 `rc = 2 if defects else 0`（`judge_r620.py:607`），而 `defects` 的唯一成员 = J6 等价面不成立。
  **判据器与阈值一律未事后改动**（预注册判据照原样判 FAIL）；把「机制面次级 FAIL」编码进器具缺陷层这件事本身
  记为**器具面缺陷**、作下轮候选（须在预注册里改，不回溯改本轮）。
- **J6 在摆动下无分辨率**：同臂逐跑次用例数摆动 48..58（≈10 例），而 J6 要求逐窗 rc 多重集与用例数逐位相等 ⇒
  「回退面 ≠ 轴关面」与「同臂噪声」在此判据下**不可区分** ⇒ 记「未判明」，按纪律 **加 reps / 扩窗**（禁下调阈值）。
- **claims_violated**（1 条）：「前缀零改动」宣称作废 —— 本轮 held-constant 主动换成 legacy 档，跨轮 pin（R617 `25c97bef…`）
  不再成立；同轮两臂可比性不受影响（`C_prefix_shared=true`）。

## 5. 诚实边界

- **不可宣称**：回退零回归（J6 未判明）· 回退带来收益（rc=2 ⇒ 禁作被测结论）· 能力提升（J4 n=9/档 欠功率）。
- 质量/成本读数一律 **参考（未可验收）**（铁律 11 rc=1）。
- 被测件与 R619 同件 ⇒ 与 R585–R619 各轮**禁相减**，只并列；窗集与历史不相交。
- M3 出口闸（调用数 ≤ 旧臂 50%）本轮只作读数：「旧臂」为跨轮自由文本动作环，形态不同源，禁跨形态相减。

## 6. 收口五件

| # | 件 | 路径 |
|---|---|---|
| 1 | 轮工件 | `eval/rover/r620/`（prereg / dag / run / judge / selftest / premise / bins / 21 跑次快照 / evidence） |
| 2 | 证据文档 | 本文件 + `evidence-run-r620.txt` |
| 3 | registry 行 | `docs/verification-registry.json` → `r620.exec-fallback-exercised`（L4） |
| 4 | kpi 行 | `eval/capability/kpi.jsonl`（带 `baselines` 11 条 id） |
| 5 | 逐名列名提交 | 见 commit（`git status --porcelain` 逐字取），提交后回读 HEAD 关键行 |

收口闸：`python3 eval/capability/status_gen.py --check`（违规 0 / 基准漂移 0 / 缺源 0）· 形式门禁 14 测试。

## 7. 下轮候选

- **C1（必做，器具面）**：J6 判据分级 —— 把「机制面次级 FAIL」从 `instrument_defects` 移出（否则每轮 J6 不成立即 rc=2 整轮禁判）；
  须在**预注册**里写明，禁回溯改本轮判据。
- **C2（必做，机制面）**：J6 的分辨率 —— 加 reps（≥6/窗）或扩窗，使「回退 vs 轴关」差异可与摆动分离；摆动 ≥ 效应则判「非承重变量」定案关闭。
- **C3**：R619 遗留 U2（`rc=5` 早退点是否与执行面顺序有关）。
- **C4**：J3 v2 的 `b1_unit_new_prompt` / `a2_per_window_calls` 是否降级为报告列（**须用户裁定**，R619 C3 未决）。
- **C5**：文献候选 PAPER-2601.06007（缓存策略：动态工具结果入前缀 ⇒ 命中率受损）⇒ 压成单变量候选（改哪一格：命中率/新算 prompt）。
