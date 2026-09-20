# R605 轮志 · 同件扩窗轮（第十一窗集 w193..w195）

- 被测件 `pub_r600` sha256 `8c3ade04d542c091…`（与 R600/R602/R603 **同一枚**；本侧独立复核 `sha256sum $HOME/.agentframework/artifacts/pub_r600/agenthost` 前 12 位一致）· 冻结题集 `taskset-r605.json` sha256 `e0c667c2a313c04b` 与 r603 件 `cmp` **零差异** ⇒ **唯一自由度 = 窗集**。
- 臂：`T` 产品默认档 ×3/窗 · `C` 轴关对照档 ×3/窗 · `C1` codex 外部真值 ×1/窗（21 跑次）；单变量 = `AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER`（T 缺省 on / C 显式 0）。
- 预注册 `prereg-r605.json`（written_before_run=true）· DAG `dag-r605.md` · 起手闸 A1/A2 PASS（`ceiling=2775 / prev_swing=285 / margin=65(cap_binding) / REQ=2715`；起手前按 pid 收口会话端 LSP 子进程，实测 `MemAvailable` +177MB）· 判别力成对控制**未行使**（内存高于阈值带 ⇒ 两闸同 PASS，如实登记）· leak-selfcheck rc=0。

## 1. 主判据 v3（同窗 codex 配对，set11）

| 窗 | 真值中位(cases) | 产品中位(cases) | 有效窗 | D(产品−真值) |
|---|---|---|---|---|
| w193 | 58 | 58 | ✔ | 0 |
| w194 | 58 | 56 | ✔ | -2 |
| w195 | 58 | 58 | ✔ | 0 |

- **D_list=[0, -2, 0] / D_median=0 / valid=3 / 阈值(D_median≥−2 ∧ 各窗>−15) ⇒ 判据 v3 = PASS**
- 真值自败窗（剔除配对，**禁筛窗**）：无
- 本窗集**三窗真值全 58/58**（首例）：全部窗进配对 ⇒ 主判据**第一次具备完整分辨率**（承 W_floor 条款）。
- LD 诊断列（**不作判据**）：`v3_ex_LD` D_list=[0, -4, 0] / median=0（冻结名单 ['wythoff#43-public', 'wythoff#57-hidden']；非平凡=True）
- **W_floor 零回归（候选④ 负控）**：回放 11 轮 ⇒ 标签翻号 3（全为 `不达→NO_RESOLUTION`：r591(valid=1), r597(valid=1), r599(valid=0)）；`NO_RESOLUTION→PASS` **0**、`PASS→任何` **0** ⇒ **纯标签语义收口、非阈值改动**；主 rc 不由该标签决定（机制面结论见 `mechanism_rc`）。

## 2. 机制/成本/能力（J1–J5 取自 `verdict-r605.json`）

| 判据 | 结果 | 读数 |
|---|---|---|
| J1 机制（随附打点） | True | T 跑次含随附 8/9 · C 0/9 |
| J2 修复收敛（主） | False | T 1/9 Wilson [0.0199, 0.435] vs C 1/9 Wilson [0.0199, 0.435] |
| J3 成本 **v2（本轮主判据）** | False | a1 池化 Σcalls 21 vs 19=False · a2 逐窗 {'w193': False, 'w194': True, 'w195': True} · b1 单位新算 665.8095 vs 287.8947=False |
| J3 v1（照原样并列，不翻案） | False | T_max_calls 4 vs C_max_calls 3 |
| J3 v2′（b1 降级为报告列；须用户裁定） | False | a1∧a2（b1 不进判据） |
| J4 能力（次级/欠功率） | False | 整题全对 T 4 vs C 4 vs C1 3 |
| J5 跨窗集同向性（并列） | False | set10(r603) 0.3334 / set11(r605) 0.0（率，禁相减） |
| W_floor 有效窗下限 | True | valid=3 ⇒ label `PASS` |

### 2.1 逐窗整题全对（v3 配对）

| 窗 | T | C | C1(cases/58) | D(T−C) | D(T−C1) |
|---|---|---|---|---|---|
| w193 | 2/3 | 2/3 | 58/1 | 0.0 | -0.3333 |
| w194 | 0/3 | 0/3 | 58/1 | 0.0 | -1.0 |
| w195 | 2/3 | 2/3 | 58/1 | 0.0 | -0.3333 |

### 2.2 成本三列（信息项；铁律 11 未过 ⇒ 标「参考·未可验收」）

| 臂 | 调用 | 新算 prompt | completion | 命中率 v_all 中位 | 命中率 v_incr 中位 |
|---|---|---|---|---|---|
| T | 21 | 13982 | 43809 | 0.9202 | 0.8613 |
| C | 19 | 5470 | 44278 | 0.9654 | 0.9486 |
| C1 | 15 | 12104 | 8802 | — | — |

- codex 真值三列：调用 15 / 新算 12104 / completion 8802（命中率 [0.8872, 0.9162, 0.9062]）

## 3. 只读并轮（rc=0）

- **L2 前缀连续性**：pass=True（`prefix_chars` 唯一 [15291] ∧ `prefix_sha256` 唯一 1 ∧ `task_sha256` 唯一 1）
- **L3 判定卫生**：pass=True（18/18 跑次由外部用例套件判、自证面 0）
- **Q1 假信心率**：0.0556（1/18）：rc==0 ∧ 外部未满分 **1 例**（w194/agentDT-r3 57/58）；反向 rc≠0 ∧ 外部满分 **7 例**（**自判过度保守**方向）
- **负控有牙**：注入前缀漂移 ⇒ L2 翻红（`rc=0, negctl_teeth=True, l2_violated=True`）
- **V_int 第六窗集**（`vint-r605.json`；同件同口径，未改一字）：跑次 21/21 (err=0) · oracle 一致 True · 控制 OK/POS/NEG 落点唯一（新粒度 has_teeth=True，旧粒度 =False）· 守恒 True；agent 桶 `{"B_coldset": 48, "A_landing_loose": 27, "D_delivery_or_shape": 9, "A_selection_order": 3}` / codex 桶 `{}`；`v_int_hist` agent `{"0": 14, "3": 1, "29": 1, "32": 1, "118": 1}` / codex `{"0": 3}`；层 agent `{"(c) 本轴外": 12, "(b) 冷集构造层": 4, "(a) 落点/选择谓词层": 2}`
- **V_int 器具 rc=2（两项 False，均已定因、不翻案）**：① `零回归=False` = **已知 scope 伪影**（单窗集重算 vs r592 登记值比较域不同；同器具对历史全集复算 match=True ⇒ 器具完好）② `只读=False` = **本侧流程违反**（器具以 `src/` 树 sha 前后比对作只读判据，而本侧在器具运行期间并发跑了 `dotnet test` ⇒ 构建写 `src/*/obj|bin`；快照树 `-newermt 04:26` 文件数 = 0 ⇒ 被测面未被改）。R606 以「无并发构建」重跑取纯净读数；本轮 V_int 读数按「参考（器具 rc=2）」登记，**不入主线结论**（V_int 为诊断项，预注册禁止阈值化）。

## 4. 铁律 11 可验收前置

- `exec_precondition.py --round r605` ⇒ **rc=1**（blocked 10 条，全部落 `wythoff` 族）⇒ 全部成本/质量读数标「**参考（未可验收）**」，禁作验收依据。
- `EXECUTABLE_AND_CORRECT=False` · `SELF_REPORT_AGREES=True` · 未声明臂 21 条（NONREQUIRED 单列 `0`）

## 5. 诚实边界

- J4 为 n=9/档 的欠功率读数 ⇒ 只作并列，不作能力结论
- 被测件按设计变更（产品源码改动 ⇒ 重发布 AOT）⇒ 与 R585–R599 冻结件轮**禁相减**
- 成本三列取中继 dump 时间轴；铁律 11 前置器 rc 见 precond-r605.json（rc≠0 ⇒ 标参考·未可验收）
- J2 的「收敛」按终态机械判（探针 failed==0 ∧ rc==0）；中间步骤失败不算收敛
- J3 v2 的 b1 项对机制**结构性不利**（随附产物必然抬高修复轮单次新算 prompt）⇒ 是否降级须用户裁定（候选③/R606）；本轮照原样计入 v2 判据并并列报 v2'
- 有效窗 ∈{0,1} ⇒ NO_RESOLUTION（禁记 PASS/不达）；真值自败窗剔除配对但单列我方读数
- LD 两例只作诊断列，不作收益/缺陷证据（主判据不剔除以保跨轮可比）
- 判别力成对控制本轮**未行使**（内存高于条款带 ⇒ 两闸同 PASS，实测 ceiling 2775MB vs REQ 2715MB）⇒ 记「未测」，不得读成条款已收紧生效。
- 本轮**零产品源码改动 / 零新增夹具语义 / 零新增开关**；J3 v2 是**形态收口**（收紧）而非放宽。

## 6. 复现命令

- 真机臂轮：`bash eval/rover/r605/run_r605.sh`
- 判决：`python3 eval/rover/r605/judge_r605.py --D $HOME/.agentframework/harness/runs/r605 --pd eval/rover/r605`
- 只读并轮：`python3 eval/rover/r605/checks_r605.py --D $HOME/.agentframework/harness/runs/r605 --pd eval/rover/r605`（负控 `--negctl`）
- 铁律 11：`python3 eval/rover/r507pre/exec_precondition.py --round r605`
