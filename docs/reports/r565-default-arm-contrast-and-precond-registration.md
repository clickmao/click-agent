# R565 · 产品真默认档 × 外部真值对照（含铁律11 前置器输入登记修复）

> 轮次: **R565** (2026-09-19, 60m 常驻能力自检作业; 主线对照轮)。零产品源码改动 / 零新增夹具 / 零新增开关 / 零远端除链内调用。
> 预注册: `eval/rover/r565/prereg-r565.json`（先写后跑: 起跑前 `[先写后跑闸] arms=['C1','R565B0'] require=12`）。
> 冻结件: 题集与判分器为 R560 逐字节复用（`taskset` sha256 `e0c667c2a313c04b…`, 副本登记见 `eval/rover/r565/frozen-reuse-registration.json`）。

## 1. 本轮单变量与臂集

| 臂 | 语义 | 差异 |
|---|---|---|
| `C1` | 外部真值（codex-cli, 同真实模型, 同题面同夹具） | — |
| `R565B0` | **产品真默认档** | `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` **未设**（与 R563 的剂量档 `=0` 构成单变量） |

窗口 = 6 个新窗 `w119..w124`（与 R563 的 `w113..w118` 不重叠）。

## 2. KPI 读数（同题集 sha, 可跨轮并列）

| 轮 | 臂 | 逐窗 cases | 中位 | 极差 | 调用 | 新算 prompt | completion | 命中率 v_all(中位) | rc/窗 |
|---|---|---|---|---|---|---|---|---|---|
| R565 | C1(真值) | 58,58,58,43,58,58 | 58.0 | 15 | 67 | 36,797 | 30,872 | 0.9329 | — |
| R565 | R565B0 | 53,50,43,52,56,52 | 52.0 | 13 | 13 | 3,732 | 31,071 | 0.9637 | 5,5,8,5,5,5 |
| R563 | C1(真值) | 58×6 | 58.0 | 0 | 34 | 22,418 | 18,653 | 0.9247 | — |
| R563 | R563B0 | 50,58,43,58,58,55 | 56.5 | 15 | 6 | 906 | 13,379 | 0.9819 | 1×6 |

- 判决（R561 装置, 判据 v2）: `rc=1 FAIL(被测/前提)`, `blocked=[quality_paired_shortfall:R565B0]`, `delta_median=-6`, `delta_min=-15`, `reliable_windows=5`（`w122` 真值窗判 `unreliable`, MARGIN=3）, 判据器自检 `6/6`。
- 终止形态: `R565B0` 每窗仅 **2–3 次调用**即终止, 5 窗 `rc=5 expect_stdout_exhausted` / 1 窗 `rc=8 self_test_unmet`, `exec_repairs=1`（默认修复上限 1 用尽）。
- 失分集中: **wythoff 单模块**（B0 6/6 窗均含 wythoff 失败例; C1 唯一失分窗 `w122` 亦为 wythoff 族）。

## 3. 铁律 11 前置器: 输入登记修复（本轮承重件）

- **缺陷（静默失效）**: 前置器按 `<round>` 目录约定发现 `taskset-<r>.json` + 任务字段 `cases` 相对路径。R563 轮只把冻结件**指过去**（`TS=$REPO/eval/rover/r560/taskset-r560.json`, 复用不复制）⇒ `--round r563` 报 `[致命] DISCOVER_FAIL … rc=3`，而 rc=3 与 rc=1/0 在轮末日志里同为一行 ⇒ **该轮的对照读数实为未可验收**。
- **修复（零器具改动）**: 落一份**逐字节冻结复用登记**（`eval/rover/r565/frozen-reuse-registration.json`）：`taskset` 副本 sha 与原件相等 + `cases/` 4 文件逐字节相等（`all_byte_identical=true`）。冻结原件未被修改。
- **修后读数**: `python3 eval/rover/r507pre/exec_precondition.py --round r565` ⇒ 6 窗 × 2 臂全跑通、`VERDICT_BLOCKED ⇒ rc=1`、`ACCEPTABLE_SCOPED=False`、`SELF_REPORT_AGREES=True`、`blocked` 逐条点名 12 臂窗中的 7 项。

## 4. 候选④: 判定输入指纹 + 口径恒等式器具（新上线）

`eval/rover/r565/fingerprint_r565.py`（只读落盘件, 零远端）:

| 判据 | 读数 |
|---|---|
| 夹具判别力（4 夹具, 含 `hit_gt_prompt` / `total_lt_parts` / `miss_negative`） | `has_teeth=true` 4/4 |
| C4-1 身份（同窗同调用 id 唯一/单调） | 13/13 调用 `identity=true`, `na_unreported=0` |
| C4-2 确定性 | `call1` prompt sha8 6/6 窗相同（`b9068f56`）; 任务 sha / 前缀 sha 各 1 类 |
| C4-3 非平凡 | `call1` vs `call2` prompt sha 6/6 窗**互异**（确定性 ≠ 恒定输出） |
| rc | **0** |

## 5. 起手闸判别力成对控制（首跑自捕）

- 首跑（`attempt1-hollow-control/`，**零臂运行**）: 条款写成「两闸必须异判」⇒ 内存态 2811/2813 MB 在条款阈 `REQ=2714` 之上时两闸皆 PASS 是**正确行为** ⇒ 断言前提不成立 = 假红，起手即拦（未起任何臂）。
- 修法（判据不改松，改**前提构造**）: 用占用把内存态**压进判别带** `[2650, REQ)` 再反判 —— 基本阈 PASS ∧ 条款 `GATE_BLOCKED` ⇒ 真判别行使；带内不可达 ⇒ `rc=3` 如实登记「真判别未行使」，**不当 FAIL**（承 R562「诱饵控制前提静默落空」同族教训）。
- 运行中采样 postcheck: `rc=0`, `2729–2797 MB`, `swing_mb=68`。

## 6. 诚实边界

1. `verdict rc=1` ∧ 铁律 11 前置器 `rc=1` ⇒ 本轮**调用/token 降幅一律标「参考（未可验收）」**，不作验收依据。
2. `matrix_r565.py` 本轮以 `--work /tmp/r565` 调用 ⇒ 该脚本 `shutil.rmtree` 掉**整轮运行工作目录**（`logs/`、adapter 逐调用件、`windows.jsonl`）。KPI 表与指纹在 rmtree **之前**已落 PDIR ⇒ 已报读数不受影响，但原始逐调用件不可复得。**器具使用缺陷（本侧）**，登记候选 = `--work` 指向轮根须 fail-closed 拒绝。
3. `R565B0` 的终止形态是**预算/修复耗尽**（`rc=5`），非能力读数：每窗 2–3 次调用即停 ⇒ 本读数**不能**区分「预算不足」与「能力不足」。
4. `w122` 真值窗判 `unreliable`（真值自身崩窗），已按判据 v2 单列。

## 7. 下轮候选（逐项: 做/未做 + 原因）

| # | 候选 | 状态 | 原因 |
|---|---|---|---|
| 1 | `matrix --work` 守卫（拒绝指向轮根/live 运行根） | 未做 | 本轮预算；缺陷已登记并留档 |
| 2 | 预算轴单变量臂（显式抬修复/步数上限, 同题同窗） | 未做 | 需新臂 ⇒ 独立轮预注册 |
| 3 | exp1 backlog 项剩余候选 | 未做 | 属器具/登记类, 与用户 2026-09-17 方向逆转冲突（登记不推进） |
