# R614 轮志 · R610 顺延边（N8→N9）重启：M3 第一刀真机读数

- 日期：2026-09-21（cron `b15eb2f40a69` 60min tick）｜ 类型：**重启边轮**（零产品源码改动；单变量 = 已提交的 `AGENTFRAMEWORK_R1_ACTION_CANDIDATES`）
- 权威预注册：`eval/rover/r610/prereg-r610.json`（臂前 10:05 落盘）；本轮**引用件** `eval/rover/r614/prereg-r614.json`（阈值/臂表/窗集/证伪条目**一字未改**）
- DAG：`eval/rover/r614/dag-r614.md`
- 被测件：`$HOME/.agentframework/artifacts/pub_r610/agenthost`，sha256 `6a31fc47a694d567…`，`bin_sha_stable=true`（运行前后一致）
- 题集：`eval/rover/r610/taskset-r610.json`（**逐字节冻结**，sha16 `e0c667c2a313c04b`，与 R585–R608 同件）
- 窗集：**第十三窗集 w199..w201**（与历史窗集不相交）｜ 臂：T（产品默认档）×3 / C（轴显式 0）×3 / C1（codex 外部真值，同环境同输入同模型 deepseek-flash）×1 ⇒ 21 跑次 + 3 真值跑次

## 0. 结论（一行）

**机制面未达标（`mechanism_rc=1`）：动作候选声明到岸率 0/9（两臂皆 0）⇒ M3 第一刀在真机未被行使；故 T−C 的成本/能力差一律不可归因（摆动）。** 任务面（主判 v3）**PASS**：T−真值同窗率差 `[0, 0]`、中位 0、有效窗 2（w201 真值自败 ⇒ `unreliable` 剔除配对）。铁律 11 前置器 **rc=1（未可验收）** ⇒ 成本降幅一律标「参考（未可验收）」。

## 1. 固定环执行与跳步

| 环 | 动作 | 状态 |
|---|---|---|
| 0 | 起手闸 `roundcheck preflight --round R614` + 清 VBCSCompiler/MSBuild/pyright | rc=0（FAIL 0 / WARN 0）；清场后 `MemAvailable` 2567→2967 MB |
| 1 | 主线提醒 | 见 KPI 报告（一行） |
| 2 | 选靶逐例归因 | 本轮为**重启边**（非新靶）⇒ 归因取自 R610 已登记缺口（执行面消费点 0） |
| 3 | 文献小步 | 见 `docs/research/lit-review-ledger.md` §12（arXiv 面 429/超时不可用 ⇒ 第二来源官方工程文档 2 件，采信 0 / 观察 2） |
| 4 | 预注册 | r614 引用件（先写后跑闸：`prereg ok: arms=['C','C1','T'] require=7 criterion=v3`） |
| 5 | 产品侧最小改动 | **跳步**：本轮零产品改动（`src/`、`tools/` 与 R610 提交零 diff；单变量为 R610 已提交件） |
| 6 | 构建/AOT | `eval/rover/r614/aot_r614.sh` ⇒ `PUBLISH_RC=0 IL_WARNINGS=0 ERRORS=0`；ELF 字节数 + 装载冒烟（仓库外 cwd、`env -i`、非空回复） |
| 7 | 真机跑 | `bash eval/rover/r610/run_r610.sh` ⇒ 21 跑次，逐窗 690/300/99 s |
| 8 | 判决 | `judge_r610.py` ⇒ `verdict-r610.json`（v1，sha12 `cbc98163980d`）＋ **v2 后处理重算** `verdict-r610-v2.json`（sha12 `66fa17ad3d42`，仅 J2b 真空绿修法） |
| 9 | 收口 | 本文件 + `eval/capability/kpi.jsonl`(R614) + registry 行 + 主线「最近一轮」+ `status_gen.py --check` + 形式门禁 + 提交（禁 push） |

## 2. 真机读数（21 跑次；逐窗 = 真值 ×1 + T ×3 + C ×3）

**质量（整题全对 = 58 例全过）**

| 臂 | 逐窗 | 池化全对率 | 用例通过中位 | 备注 |
|---|---|---|---|---|
| T（轴默认 on） | 3/3 · 2/3 · 2/3 | **0.778** (7/9) | 58 | |
| C（轴显式 0） | 1/3 · 1/3 · 1/3 | 0.333 (3/9) | 51 | |
| C1（codex 真值） | 1/1 · 1/1 · 0/1 | 0.667 (2/3) | 58 | w201 用例 47/58 ⇒ 真值自败 ⇒ `unreliable` |

**配对（任务面 v3，主判）**：同窗率差 T−C1 = `w199 0.000 · w200 −0.333 · w201 +0.667` ⇒ 有 1 窗真值自败 ⇒ 剔除后 **D_list `[0, 0]`、中位 0、有效窗 2 ⇒ PASS**（floor −15 / median_floor −2 均未触）。

**成本三列（中继 dump 时间轴聚合，非 transcript 自报；铁律 11 rc=1 ⇒ 参考·未可验收）**

| 臂 | 调用（逐跑次/池化） | 新算 prompt（池化/单位调用） | completion（池化） | 命中率 v_all（中位） | v_incr（中位） |
|---|---|---|---|---|---|
| T | `2×7,1,2` / **17** | 16,785 / **987.4** | 40,777 | 0.900 | 0.834 |
| C | `2,1,2,2,2,2,1,3,2` / **17** | 12,342 / 726.0 | 38,891 | 0.915 | 0.855 |
| C1 | `5,80,7` / 92 | 44,185 / 480.3 | 28,932 | 0.916 | 0.945 |

**步数/轮数**：T 步数 7×7/14/15（`plan_steps_total` 7–15）；C 同量级。**机制面计数**：`action_candidates_declared = 0` 于 **T 9/9 ∧ C 9/9 ∧ C1 3/3**（18 跑次 transcript 无该字段 ⇒ 声明数 0）。

**判决（v2，后处理重算，未重测）**：`rc=0`（器具可用）／`mechanism_rc=1`（J1 未达标）／`label=机制未达标`；J2 修复收敛 FAIL（T 2 vs C 2，需 ≥+1）；J3 成本 v2 FAIL（a1 池化调用 17 vs 17 持平 ∧ a2 逐窗 ∧ b1 单位新算 prompt 987 vs 726 **更差**）；J4 次级 PASS（T 7/9 ≥ C 3/9+1，欠功率 n=9 ⇒ 只作并列）；J5 跨窗集同向 PASS（并列项）。

## 3. 归因：声明率 0/9 = **模型未声明**，不是接线缺口（关键判定）

| 假设 | 机检 | 判定 |
|---|---|---|
| 契约块**未**进实发前缀（接线缺口） | `AGENTFRAMEWORK_DUMP_REQUEST` 取**实发请求体**：system 消息 **15,675 字符**（= `StructuredPrompt.PrefixChars`），含 `<prefix version=…>`、`<self_check>`、**`<action_candidates>`** 块；`prefix_sha256 = a9792fdb…`（= `PrefixSha256Pinned`）、18/18 跑次 `prefix_pinned=true` | **证伪**（块在实发前缀内，两臂逐位同） |
| 远端声明了但抽取器读空（判据器读法错） | `grep -l action_candidates w*/agent*/g1/reply.txt` ⇒ **0 命中**（21 条回复全文）；transcript 亦无该字段 | **证伪**（抽取器无输入可读；J1=0 为真实读数） |
| ⇒ 真因 | 远端模型对该**可选**字段**零遵守**（9/9 未声明） | **机制未被行使**（驱动/合规缺口），非接线缺口 |

**由此的成本面（J3）不得读作「无收益」**：轴未产生任何执行面输入 ⇒ T/C 两臂在行为上**按构造近同**（调用 17 vs 17），其差只能记「摆动」。按 `kpi-eval-harness-context` 同族纪律：**mechanism-not-engaged ⇒ Δ 数字作废，不得据此下「无效」结论**。

## 4. 自捕器具缺陷（2 件；均有两侧样例/负控，未放宽任何判据）

1. **J2b 裁选守恒判据「真空绿」**（最贵）：`judge_r610.py` 实现只判 `conservation_violations == 0`，而其 `need` 串已写明「T 档有声明跑次 > 0 ∧ …」⇒ 声明数 0 时守恒式**真空成立** ⇒ v1 报 `J2b pass=True`（把「没测到」读成「测过通过」）。
   - 修法：门加 `j2b_declared_runs > 0`（阈值未改）+ 新增 `reason=NO_DECLARATION_VACUOUS`；**后处理重算**得 v2（`J2b pass=False`），首跑 v1 读数**原样保留**（`verdict-r610-v1.json` / `kpi-table-r610-v1.json`），v1 driver sha12 `cbc98163980d` 与 v2 `66fa17ad3d42` 双列。
   - 负控有牙：`eval/rover/r614/j2b_teeth_r614.py` —— ①门表达式**源派生**（不手抄）+ 防漂移；②两侧样例（真空 ⇒ 不可判 / 有声明且守恒 ⇒ 通过）；③不守恒 ⇒ 判红。正控（v2 判据器）**rc=0**；**前态负控**（`pretest/.../judge_r610.py`，sha256 `cbc98163980d…` **= v1 首跑所用件逐位同源**）**rc=2 GATE_MISSING** ⇒ 门确实有牙。
   - **件名对照（防混用）**：`verdict-r610.json` = 运行器在臂后（修复前判据器）落盘的**首跑 v1**；`verdict-r610-v1.json` = 其副本；`kpi-table-r610.json` = 后处理重算后的表（与 v1 表读数同，见 `kpi-table-r610-v1.json`）；`verdict-r610-v2.json` = **修复后判据器的后处理重算件**（唯一权威 v2）。三个 v1 件**不得**被 v2 覆盖。
2. **读法错（自捕，1 件）**：首查用 adapter 侧 `full-agent-*.json` 判「前缀是否含 `<action_candidates>`」得「不含」——实为**两因叠加**：adapter dump 把 system 截断到 **12,000 字符**（块位于前缀尾部 ≈14.5k+）+ STJ 序列化把 `<` 转义为 `\u003C`。改用**产品自落盘**的 `AGENTFRAMEWORK_DUMP_REQUEST` 原文才定案。⇒ 纪律：判「字段/块是否在实发请求里」**只认实发件原文**，且须先确认落盘件**未截断**。

## 5. 铁律 11（可执行且正确）前置器

`python3 eval/rover/r507pre/exec_precondition.py --round r610` ⇒ **rc=1**（`precond-r610.json`）：
- `EXECUTABLE_AND_CORRECT=False`、`ACCEPTABLE_SCOPED=False`、`SELF_REPORT_AGREES=True`、`POLICY_ACTIVE=False reason=no_policy_key`；
- 不合格臂窗 9 项（本侧 T/C）：`w199 C-r1 rc=124 超时 0/6`、`w199 C-r3 51/58`、`w200 C-r2 52/58`、`w200 C-r3 47/58`、`w200 T-r2 44/58`、`w201 C-r2 47/58`、`w201 C-r3 43/58`、`w201 T-r1 51/58`；
- **外部真值臂自身亦不合格**：`codex 47/58` ×3 窗（失败**全在 wythoff 族**：family 通过 life 42/42 · sub 42/42 · nim 45/45 · **wythoff 34/45**）⇒ **真值非硬上限**，w201 剔除配对并单列我方读数。
- ⇒ 本轮**任何** token/调用降幅**不得作验收依据**（用户令 2026-09-17 + RF0005 §1）。

## 6. 诚实边界

1. `mechanism_rc=1` ⇒ 成本与能力两面的 T−C 差**不可归因**（轴未行使）；J3「b1 单位新算 prompt 更差」**不得**读作产品变差（同因）。
2. J4 为 n=9/档 **欠功率**读数 ⇒ 只作并列，不作能力结论（R587 教训：跨窗摆动 ≥ 臂效应）。
3. 真值臂 47/58（3 窗同值）⇒ 该题集对**真值也非上限**；wythoff 族为双侧共同缺口（R586/R602 同族，非本轮新增）。
4. 被测件按设计变更（R610 前缀加厚 15291→15675 字符）⇒ 与 R585–R606 冻结件轮**禁相减**，只并列。
5. J2/J3 为**继承面**（修复收敛 / 成本形态）⇒ 不进 `mechanism_rc`（该面定义已收窄为 J1∧J2b）。
6. M3 出口闸（调用数 ≤ 旧臂 50%）**本轮不判**：执行面消费点仍为 0（`git grep ActionCandidatesAccepted` 于执行器面为空）⇒ 按构造无可分离量。
7. `grep` 面判据本轮**两次**受「落盘件截断/转义」干扰（§4.2）——凡「文本是否出现」类判据，本轮起一律先验落盘完整性与编码形态。

## 7. 下轮候选（并轮，供 R615 起臂）

| # | 候选 | 动作 | KPI 格 | 前置 / 判据 |
|---|---|---|---|---|
| ① | **声明面驱动**（最高优先） | 契约面把候选字段从「可选」改为**任务需要多步工具动作时必填**（或在 `self_check` 清单加一条）；单变量轴不变 | 调用数 / 轮数 | 判据 = 声明到岸率 > 0（≥1 跑次）；**先证前缀加厚不破 97% 命中下限**（`PrefixMinCharsForCache97` 档位） |
| ② | **执行面接线**（M3 第二刀） | 让 `accepted` 被执行器消费（当前消费点 0） | 调用数 ≤ 旧臂 50%（M3 出口闸） | 接线证据 = 事件数 ≥1；负控 = 轴关时旧路径计数 > 0 |
| ③ | 捕获面加固 | adapter dump 12,000 字符截断显式化（落 `truncated:true` + 原长） | 器具（非产品） | 判据 = 截断标记出现率 = 100%（超限时） |
| ④ | 超时窗 | `w199 C-r1 rc=124`（600s 上限，0/6 例）⇒ 记录是否复现；**不调阈值** | 质量 | 复现 ⇒ 标 `unreliable` 单列（与 R586 C7 同族） |
| ⑤ | wythoff 族双侧缺口 | 真值 34/45 与本侧同族 ⇒ **先判夹具/题面**再谈能力（R512 教训） | 质量 | 判据 = 两侧同败集合逐字比对 |

**收口状态**：`eval/capability/status_gen.py --check` ⇒ PASS（违规 0 / 基准漂移 0 / 缺源 0）；形式门禁 `VerificationForm|SkillGeneralization|DevPlanDocRef` ⇒ 见 kpi.jsonl(R614)。
