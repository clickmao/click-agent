# R621 轮志 · RF0004.2 · M3 第五刀 = 等价面分辨率取证 + 判据分级

**轮次**：R621（窗集 w217..w219，与历史 w184..w216 不相交）
**唯一变量**：`AGENTFRAMEWORK_R1_ACTION_EXEC`（T=1 / C=unset），held-constant = `AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy`（两臂同值）
**产品侧改动**：**零**（复用 R619 AOT 件逐字节，sha256 `a184d7317b6e…`，19,838,192 B；bins-r621.json 钉死）
**本轮动的是器具面**：判据 v3→v4（J6 三态 + rc 分级 0/1/2/3）、reps 3→6/窗、影子自检新建
**协议**：`docs/plans/RF0005-completion-protocol.md` §2 固定环 0–9（跳步见 §8）

---

## 1. 起手闸与前提闸（先证「能跑」再谈读数）

| 闸 | 读数 | 判定 |
|---|---|---|
| 起手前采样（3 次） | ceiling(min of 3) = **2836 MB**，spread = 6 MB（≤50MB） | 采信 |
| 余量条款 | prev_swing=119（源 = r620/logs/run-samples.jsonl，n=191，swing=78；口径 = 2769−2650）⇒ MARGIN=119 ⇒ **REQ=2769** | 落盘 `gate-margin-r621.json` |
| A1/A2 起手闸 | mem 2858 / 2859 MB ≥ 2769 ⇒ **PASS**（两次） | 放行 |
| 判别力成对控制 | rc=0（0 真判别行使 / 3 未行使已如实登记） | PASS |
| leak-selfcheck | rc=0 | PASS |
| **前提闸**（起臂前 1 跑次） | `exec_source=plan_fallback` ∧ `exec_fallback=candidates_absent` ∧ `prefix_sha256 == a9792fdbe5b2`（legacy 锚）∧ plan_steps=10 | **rc=0 ⇒ 回退触发面成立** |
| 全臂同一枚二进制 | T/C 同 sha；cfg 三文件 sha 钉死；题集 sha12 = `e0c667c2a313`（与 R620 逐字节同源） | 臂身份由构造保证 |

## 2. 判决（判据 v4；rc 分层 0/1/2/3）

| 判据 | 结论 | 关键读数 |
|---|---|---|
| J0 臂轴生效 | **PASS** | T 档 18/18 `exec_source=plan_fallback`；C 档五字段全缺席（0/18 出现）；两臂前缀同 sha（`a9792fdbe5b2…`）⇒ held-constant 真生效；`cross_round_anchor` FAIL（见 §7 claims） |
| J1 执行面被消费 | **PASS**（J1a/J1c/J1d/J1e 全真） | T：回退行使 **18/18**（`runs_plan_fallback=18` ∧ `runs_fallback_executed_positive=18`）、`candidates∧executed==0` 形态 0、三态 = `EXERCISED_OK` |
| J2 修复收敛 | PASS | T converged 5 vs C（≥C+1） |
| J2b 裁选守恒 | **N/A（不可判）** | `NO_DECLARATION_VACUOUS`：legacy 档候选键结构性不到达 ⇒ T 档 0 个有声明跑次 ⇒ 守恒式真空 ⇒ **禁读作通过**（`mechanism_rc` 已按 N/A 处理） |
| J3 成本（v2 = a1∧a2∧b1） | **FAIL（如实登记，阈值零改动）** | Σcalls **35 vs 34**（fail）· w217 逐窗 **12 vs 11**（fail）· 单位新算 **853.5 vs 851.1**（fail）；controls：POS pass、NEG_equals_base、non_trivial 均 true |
| J4 能力（次级·并列） | PASS（并列口径） | 整题全对 T **12/18 (0.667)** vs C **6/18 (0.333)**；逐窗 6/3/3 vs 3/2/1；真值 C1 **3/3 (1.000)** |
| J5 跨窗集同向 | PASS | 池化 (T−C) 本轮 +0.3334 与 R617 表 +0.3334 **同号**；`sign_consistent=true` |
| **J6 等价面（本轮主判据）** | **state = NO_RESOLUTION ×3 窗（⇒ 非 PASS、非劣、非零回归）** | 逐窗 Δ中位(C−T) = **−6.0 / −0.5 / −1.5**，而同臂极差（阈值，数据派生）**恒 = 15** ⇒ \|Δ\| < 极差 ⇒ **摆动 ≥ 效应 ⇒ 不可判** |
| **rc 分层** | **rc = 0**（`defects=[]` ∧ `mech_secondary=[]`）· `mechanism_rc = 0` | rc=2 的旧口径（R620）不再吞掉等价面差异；NO_RESOLUTION **不入 rc**，但强制在判决件登记 |

**J6 逐窗原始读数**（`per_window`，可复核）：

| 窗 | rc 多重集 T | rc 多重集 C | 用例 T | 用例 C | 极差 | Δ中位(C−T) | state |
|---|---|---|---|---|---|---|---|
| w217 | 0,5,5,5,5,8 | 0,0,5,5,5,5 | 58×6 | 43,45,46,58,58,58 | 15 | −6.0 | NO_RESOLUTION |
| w218 | 0,0,5,5,8,8 | 0,0,5,5,5,8 | 48,56,56,58,58,58 | 43,55,56,56,58,58 | 15 | −0.5 | NO_RESOLUTION |
| w219 | 0,0,5,5,5,5 | 5,5,5,5,8,8 | 58,58,58,58,58,58 | 43,49,54,58,58,58 | 15 | −1.5 | NO_RESOLUTION |

## 3. 逐臂 KPI（同窗同夹具；39 跑次 = T×18 / C×18 / C1×3）

| 臂 | 回复质量（逐窗 / 中位 / 极差） | 调用 | 新算 prompt | completion | 命中率 v_all / v_incr（中位，口径 = 中继 dump 时间轴） | 跑次 | rc |
|---|---|---|---|---|---|---|---|
| T（exec=1，回退面） | 1.0 / 0.5 / 0.5（6,3,3 全对） | 35 | 29,871 | 89,412 | **0.9103 / 0.8491** | 18 | 1（逐跑次 cases 未全对） |
| C（exec unset = 旧行为） | 0.5 / 0.333 / 0.167（3,2,1） | 34 | 28,939 | 83,233 | **0.9087 / 0.8449** | 18 | 1 |
| C1（codex 外部真值） | 1.0 / 1.0 / 0.0（1,1,1 全对） | — | — | — | — | 3 | 0 |
| 配对差 T−C（逐窗） | +0.5 / +0.167 / +0.333 | +1 | +932 | +6,179 | +0.0016 / +0.0042 | — | — |
| 配对差 T−C1（逐窗） | **0.0 / −0.5 / −0.5** | — | — | — | — | — | — |

未上报 usage：**0**（v_all 无 None）；命中率口径 = 中继 dump 时间轴；两列（v_all 全量 / v_incr 增量）**分列不合并**。

## 4. 承重缺口定位：**wythoff 族**（族分列，禁由单族主导跨窗比较）

| 族 | T（pass/总） | C | C1（真值） |
|---|---|---|---|
| life | 250/252 | 252/252 | 42/42 |
| sub | 252/252 | 252/252 | 42/42 |
| nim | 270/270 | 270/270 | 45/45 |
| **wythoff** | **223/270（82.6%）** | **158/270（58.5%）** | **45/45（100%）** |

⇒ 失败面**几乎全在 wythoff 族**（lexicographic-min winning-move 语义），且**真值 C1 全对** ⇒ **不是夹具缺陷、不是两侧同败**，是产品侧真实能力缺口；T（回退面）在该族上比 C 好 **+65 例次**（65/270 = +24pt）⇒ 执行面回退在该族有**方向一致**的收益，但样本仍不支持「等价」也尚未追平真值。

## 5. 三态等价面的处置（本轮主结论）

- 预注册 falsification ③：J6 = NO_RESOLUTION ⇒ **判据不可判**（禁读作零回归、禁读作通过）；按 RF0005 §3 R5 记「该等价面在 n=6/窗 下为非承重变量」⇒ **定案关闭该轴，不再为同一缺口加轮**（reps 3→6 的补救已用尽，摆动仍 15）。
- 这不是「回退无副作用」，也不是「回退有害」：**未判明**。替代读数（并列，不作等价结论）：J4 整题全对 T 12 vs C 6、配对逐窗同向为正、wythoff 族 +24pt。
- **rc 分层的价值**：同一批数据在 R620 口径下会被编码成 `rc=2`（器具缺陷 ⇒ 整轮禁作被测结论）；v4 后 rc=0 + `mechanism_rc=0` + J6 state 显式登记 ⇒ 「不可判」不再伪装成「器具坏」或「通过」。

## 6. 自捕器具缺陷（两条，均如实入档、均不改判据）

1. **label 口径矛盾（起臂后修，非回溯）**：`label` 旧式直接读 `j2b_pass`，而 legacy 档 J2b **结构性 N/A**（`declared_runs=0`）⇒ label 与 `mechanism_rc` 谓词不一致（一个读 N/A、一个读失败）。
   - 修前 label 原文 = `机制未达标`（归档件：`verdict-r621-preLabelFix.json`）
   - 修后 = `机制达标（J0∧J1a∧J1b∧J1c∧J1d∧J1e ∧ J2b=N/A）· J6=NO_RESOLUTION`
   - **逐字段 diff 取证**：两版 verdict 相交键中仅 3 个变化（`verdict.label`、`checks_posthoc`、`instrument_source.driver_sha12`）+ 1 个新增键（`verdict.label_defect_fixed`）⇒ **阈值/rc/判据字段零变动**；R620 判据**不回溯**。
2. **运行期外因污染内存采样**：`logs/run-samples.jsonl` 在 elapsed≈190 s 处含一枚 237 MB 编辑器语言服务器（pyright/node，用户侧工具）⇒ 该窗 mem 被压到 2630 MB；已按 pid 清场（未触在飞件）。本轮判决不读该字段；下轮起手闸 swing 由该文件重派生 ⇒ 方向**保守**（margin 只会更严，不产假绿）。

## 7. 诚实边界

- **铁律 11 前置器 rc=1**（`executable_and_correct=false` / `acceptable_scoped=false`；含 `UNDECLARED_SCOPE` 57 项与 18 项 blocked）⇒ **本轮全部质量/成本读数一律标「参考（未可验收）」**，不得作降幅或能力达标依据。真值 C1 3/3 全对 ⇒ 未可验收由**我方臂**未达「产出物可执行且正确」导致。
- **claims_violated**：`跨轮前缀锚不成立（T 前缀 ≠ R617 pin）` ⇒ 撤回「前缀零改动」宣称（本轮 held-constant 换 legacy 档）；同轮两臂可比性不受影响（C_prefix_shared=True）。
- **J4 欠功率**：n=6/窗（合计 18/档）⇒ 只作并列；跨轮**禁相减**（rc 编码层两轮不同）。
- **LD 诊断列**（`wythoff#43-public` / `#57-hidden`）只作诊断，不进 rc、不剔除（保跨轮可比）。
- **被测件与 R619/R620 逐字节同件** ⇒ 与 R620 禁相减、只并列。
- 有效窗 = 3（真值自败窗 0）⇒ W_floor PASS。
- **实测性能项**（耗时）受同机并发影响 ⇒ 只作信息项。

## 8. 协议符合性（跳步登记）

- 跳步 **无**（固定环 0–9 全跑）。
- 次序偏差 2 条，如实登记：① 文献小步在**起臂后**执行（只读网络、不写任何在飞件；不影响预注册内容）；② `dag-r621.md` 落盘晚于起臂（其依赖边由已执行顺序反推，未改任何已跑读数）。
- 器具面改动 `python3 eval/capability/decl_sweep.py --apply` 与 registry 重钉见 §9 收口。

## 9. 收口五件

| # | 件 | 状态 |
|---|---|---|
| 1 | 轮工件（`derive/judge/selftest/closeout/run/premise/bins/gate-margin/kpi-table/verdict/dag/cases/snapshots`） | 齐（本目录） |
| 2 | 证据文档 | 本文件 + `evidence-run-r621.txt` |
| 3 | registry 行 | `r621.equivalence-resolution-and-rc-tiering`（L4，含 negative_control/covers/evidence_cmd） |
| 4 | kpi 行带 `baselines` | `eval/capability/kpi.jsonl`（11 个 baselines id） |
| 5 | 逐名列名提交 | 见 git（禁 `git add -A`） |

## 10. 下轮候选（杠杆已从「等价面」换到「能力面承重族」）

| 候选 | 动作 | KPI 影响 | 前置 | 判据 |
|---|---|---|---|---|
| C1 | **wythoff 族决策语义**：定位失败子型（lexicographic-min 选点 vs WIN/LOSE 判定），按失败例逐例归因（独立 oracle 复算） | 质量（族分列通过率 ↑） | 冻结产物已在本轮 `snapshots/`；零产品改动即可做归因 | 失败例四分归因完成 ∧ 目标子型占比 ≥50% |
| C2 | 成本面 J3 三条款同向差（+1 调用 / +932 新算 / +2.3 单位）⇒ 分档定位「哪一档多花」 | 成本（单位新算 ≤ C） | 中继 dump 已有 per-call 行 | 逐档分解后定位到 ≥50% 差额来源 |
| C3 | 等价面判据**不再加轮**（已定案关闭）；若将来重启需换杠杆（改判据为逐例级而非逐跑次级） | — | 重开条件：换判据粒度 ∧ 摆动 < 效应 | 预注册声明新粒度 |
| C4 | 文献小步：wythoff 类「博弈解生成的搜索-验证分离」机制（下轮检索面） | 质量 | arXiv 预算 3 query | 采信需本仓代码证据对照 |

## 红线

零产品源码改动；推送暂停令在效（本轮只本地提交）；不新增夹具、不做额外开发；读数落 `eval/capability/kpi.jsonl`；未伪造读数（rc=0 但 `precond rc=1`、J3 FAIL、J6 不可判三者均如实写出）。
