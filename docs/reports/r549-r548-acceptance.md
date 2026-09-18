# R549 — R548 关账轮：**仓外证据入仓 + 铁律 11 机检 + wythoff 定因**（产品源码零改动）

**日期**: 2026-09-18 · **前置器**: `python3 eval/rover/r507pre/exec_precondition.py --round r549` ⇒ **rc=1**（`declared_absent=0` / `blocked=4` / `SELF_REPORT_AGREES=True` / `EXECUTABLE_AND_CORRECT=False` / `ACCEPTABLE_SCOPED=False`）· **器具**: `eval/rover/r549/`（`ingest_r548.py` / `make_evidence.py` / `replay_cases.py` / `prereg-r549.json` / `snapshots/` / `evidence/` / `readings-r549.json`）

## 1 因果链

R548 的读数（新契约 58/47/58 · 2 调用/窗）只存在于**仓外**运行树 `/tmp/r548_{c2,d}`，仓内既无快照也无 usage 落盘 ⇒ 前置器无从发现 ⇒ 按铁律 11 该轮一切降幅只能标「参考（未可验收）」。本轮把该运行树**按字节入仓**（72 文件 + 逐文件 sha256），使前置器能独立物化 + 58 用例实跑 ⇒ 首次拿到 R548 声称的机检裁决，并定位「降幅不可验收」的**唯一阻塞族**。

## 2 器具缺陷修复（前提：旧执行路径会泄漏僵死子进程）

- 现场：08:29/08:33 两个 pid（203815 / 205078）各烧 ~77% CPU 逾 2h，`/proc/<pid>/cwd` = `/tmp/precond-w1-agentE1c-g1-*` ⇒ 前置器**早前一轮**的泄漏残留（父已亡、被 init 收养）。
- 根因：`run_case_script`/`run_file` 用 `subprocess.run(timeout=…)`，超时只杀**直接**子进程；用例脚本自起的循环子进程留在原地。
- 修复（`eval/rover/r507pre/exec_precondition.py`）：执行体一律 `start_new_session=True` 独立进程组；超时与**正常收尾**都 `killpg` 整组；新增 `group_gone` 断言（`killpg(pgid,0)` 轮询 ≤3 s）；新增 `--leak-selfcheck`。
- 自检（`--leak-selfcheck` ⇒ 落 `eval/rover/r549/leak-selfcheck.json`）：A 正常退出但留下循环子 ⇒ 组收口后 `/proc` 扫 cwd 零残留；B 用例脚本自身超时 ⇒ `rc=124` 且零残留；C **假阴控制**（人工在同一目录塞活循环子）⇒ 扫描器必响。
- 开发中两次**探针自身**的假信号（记入 `leak-evidence.txt`）：① 用 `subprocess.PIPE` + `communicate()` 时孙进程持管道 ⇒ 直接子进程已退出却被判「超时」（改用临时文件承接 stdout/stderr）；② `os.getpgid(p.pid)` 在直接子进程已退出时抛 `ProcessLookupError` ⇒ 退回 `p.kill()` 空操作，孤儿照留（改为直接 `killpg(p.pid)`——组长身份由 `start_new_session` 保证）。
- **保形**：`run_file` 超时 `rc=124` / 异常 `rc=125` 的旧编码与 `MIN_ENV+HOME`、`cwd=dirname(path)` 语义均保持；对照 `git diff` 逐行确认唯一功能差异 = 进程组收口。
- 独立保形回归（新执行路径重放 r547/w2 三臂，`eval/rover/r549/replay-r547-form.json`）：`agentA1on-g1` 58/58、`agentD1a-g1` 56/58、`agentE0a-g1` 50/58，**逐臂 `cases_pass` 与历史落盘读数 `same=True`**，失败用例名单亦逐条相同（`wythoff` 10 例）⇒ 收口修复**未改变判分语义**，且重放 5.3 s 无挂死（修复前该类臂会留孤儿）。

## 3 入仓与同输入硬条件（①）

| 项 | 值 |
|---|---|
| 快照 | `eval/rover/r549/snapshots/w{1,2,3}/agent{R548b-g1,R548base-g1}/g1`（72 文件，含 `__pycache__` 保真） |
| 题面 | `taskset-r549.json` 的 `prompt` sha256 `516f3208963c6e66…` **== R548 运行树 `task-g1-prompt.txt`**（逐字节） |
| 用例 | `cases/cases-r521.json` sha256 与 r531/r547 副本**逐字节同**（同题面/同用例，跨轮可比） |
| 逐调用 usage | `readings-r549.json`（源：`/tmp/r548_*/adapter/side-agent-*.json`，逐文件 sha256 入 `source-manifest.json`） |

**排除项**：`snapshot-manifest.json` 逐文件 sha256 覆盖入仓时的全部 72 文件，其中 `games/__pycache__/*.pyc` 受 `.gitignore` 管辖 **不入提交**（仓内不可复现缓存字节，只影响导入缓存，不影响判分语义）；题面/用例/源码 6×3 臂文件全部入库。

## 4 机检读数（铁律 11，判分器独立于自报）

| 窗 | 臂 | 用例 | rc | 判定 | 失败用例 |
|---|---|---|---|---|---|
| w1 | agentR548b-g1 | **58/58** | 0 | correct | — |
| w1 | agentR548base-g1 | 46/58 | 1 | ✗ | wythoff ×12 |
| w2 | agentR548b-g1 | 47/58 | 1 | ✗ | wythoff ×11 |
| w2 | agentR548base-g1 | 47/58 | 1 | ✗ | wythoff ×11 |
| w3 | agentR548b-g1 | **58/58** | 0 | correct | — |
| w3 | agentR548base-g1 | 52/58 | 1 | ✗ | wythoff ×6 |

- `SELF_REPORT_AGREES=True`（本轮派生的自报行与机检逐条一致）；**失败 100% 落 `wythoff` 家族**（与 R547/R548 的观察一致，本轮首次由仓内机检复现）。
- **声明面笔误的 fail-closed 行为**（run#1）：`require` 初版写成臂标签 `w1/R548b-g1`，前置器按快照目录名匹配 ⇒ 6 条 `DECLARED_ARM_ABSENT`、rc=1；改声明为目录名后重跑（run#2）`declared_absent=0`。两次运行的**评分字段逐字节相同**（`cases_n/cases_pass/rc/correct/failed_cases/claimed_all_pass`），差异仅在 `scope` 域（`undeclared`→`require`）⇒ 声明修正，非评分修正（run#1 存 `/tmp/precond-r549-run1.json`，`prereg-r549.json.declaration_fix_log` 留痕）。

## 5 同尺 KPI（同一题面/夹具/58 用例，三窗并列）

| 侧 | 调用 (w1/w2/w3, Σ) | prompt tokens (Σ) | completion (Σ) | 用例 (Σ) | 全绿窗 |
|---|---|---|---|---|---|
| R1 新契约 (R548b) | 2/2/2 = **6** | **50,331** | 11,889 | 58/47/58 = **163/174** | 2/3 |
| R1 旧契约 (R548base) | 2/2/3 = 7 | 57,878 | 14,090 | 46/47/52 = 145/174 | 0/3 |
| codex 外部真值 | 9/14/85 = 108 | 2,030,796 | 38,362 | 56/58/58 = **172/174** | 2/3 |

- **判据①（成本）成立**：prompt tokens **−97.5%** vs codex（50,331 / 2,030,796），调用 **−94.4%**。
- **判据②（质量不降）不成立**：163/174 vs 172/174，差 **9 例全在 `wythoff`**。
- ⇒ 主线判据整体**未达成**；`rc=1` ⇒ 本轮全部降幅一律标**参考（未可验收）**。

## 6 定因（非同源独立 oracle）

`eval/rover/r531/oracle_wythoff_r531.py`（手写「必败点 DP + 合法着法暴力枚举」，本轮加 `--round/--arms/--cases` 参数化，**保形**：默认路径下重放 r531/w3 ⇒ 与冻结读数 `15/15×3 + codex 13/15` 逐值一致，且 `fixture_agrees_with_oracle=True`）：

| 臂 | w1 | w2 | w3 | 缺陷分类（三窗合计） |
|---|---|---|---|---|
| R548b-g1 | 15/15 | **4/15** | 15/15 | `non_winning_move` 11 |
| R548base-g1 | 3/15 | **4/15** | 9/15 | `non_winning_move` 16 · `illegal_move` 9 · `wrong_lose` 2 |

- **夹具无缺陷**：15 条冻结用例的 `expected_stdout` 与 oracle 15/15 一致 ⇒ 失败是**产物能力缺陷**。
- 机制（从在盘产物读出）：臂自建「必败点表」后用**未自验的落点**输出着法 ⇒ 落点常不在必败点集合上（例：`(21,25)` 期望 `WIN 15 15`，w2 臂出 `WIN 17 17`）；base 臂另有**非法着法**（`WIN -15 -15`，负数）与**误判必败**（`LOSE`，把能赢局面判负）两类。
- 管道侧含义：这批错例**含题面公开用例**（#43/#44），而现有 public probe 已能命中（该窗 `rc=8` 成对报 / 自测未达成）⇒ 缺口不在「发现」，而在「**自测未过仍交付**」+ 缺「落点自验」。

## 7 口径复核（R548 候选②）：命中率行**不可复现**

从入库的中继逐调用 usage 重算（`readings-r549.json`）：

| 口径 | R548b w1/w2/w3 | R548base w1/w2/w3 |
|---|---|---|
| `v_all` = 1 − Σmiss/Σprompt | 48.1 / 96.1 / 96.1 % | 96.2 / 95.8 / 95.5 % |
| `v_incr` = 1 − miss(增量调用)/prompt(增量调用) | 93.0 / 94.4 / 94.3 % | 94.9 / 94.1 / 94.5 % |
| 1 − miss_last/前缀字符(15,119) | 96.0 / 96.8 / 96.8 % | 97.2 / 96.7 / 97.5 % |
| **R548 报告值** | **95.6 / 96.5 / 96.4 %** | **97.8 / 95.6 / 96.5 %** |

- 穷举上述自明口径**无一**能复现报告值；最接近的单点拟合是「1 − **末次调用** miss / ~13.6k token 前缀」（`601/13,659=4.40%`→95.60% · `478/13,657`→96.50% · `489/13,583`→96.40%，三窗同分母），**但该口径未在报告里写明**，且与首调用读数直接冲突（R548b w1 首调用 `miss 8,105 / prompt 8,233` 为**冷启动**，任何含首调用的口径 ≤48.1%）。基线行（97.8/95.6/96.5，末次 miss 430/494/512）在任何候选口径下都不可复现，且与 R548b 行两值重叠错位 ⇒ 疑跨窗/跨轮转录。
- 裁决：该行**不得作验收依据**；重钉口径 = per-call 中继 usage 双口径并列（`v_all` 含冷启动 / `v_incr` 仅增量），脚本化入 R550 候选。
- **外侧同病**：同一行的 codex 列（87.8/87.4/94.8%）亦不可复现——仓内 `posthoc-codex-g1/summary.json` 的 `cached/prompt` = **92.1 / 91.4 / 98.0 %**（miss 7,348 / 11,576 / 36,448），两者恒差 ~4 pp 且**调用数**也不同（该行 9/5/71 vs 在盘 9/14/85、prompt Σ 1,802,336 vs 2,030,796）⇒ 「R548 的两套 codex 读数并非同一物证」；对外侧真值同样只有「取中继 usage 重算」一条可复现路径。

## 8 诚实边界（没测到什么）

1. **本轮零远端调用** ⇒ 无新增能力证据；所有 R1/codex 读数来自 R547/R548 运行树（本轮只做入仓 + 机检 + 定因）。
2. 快照逐文件 sha256 入仓，但**运行环境未同时冻结**（二进制 sha / env 仅从 transcript 读回，未与仓内 pin 对账）。
3. w2 两臂**同败**（4/15 vs 4/15）⇒ 单窗内不能判「新契约质量更优」；质量结论只有三窗并列方向（163 vs 145）。
4. codex 侧 token 取自其 `summary.json` 自报（该树 adapter dump **无 usage 字段**）⇒ 非同口径，仅作量级对照；codex 调用数 85 与 R547 记录一致。
5. **未测**：修复后能否 58/58（修复本轮未实施）；泄漏自检未纳入 run 脚本起手闸；δ=1 质量损伤成对检验仍未做；旧路径列 n≥5 未补。

## 9 下轮候选（R550）

① **wythoff 落点自验**（唯一能解锁验收的动作：让 58/58 成立 ⇒ 前置器 rc=0 ⇒ 主线降幅首次可验收）—— 复用既有自检开关，把「产出着法前必须验证落点 ∈ 必败点集」接进自检面，先写预注册再跑。② 命中率口径**脚本化重钉**（per-call，双口径并列，接进 `make_evidence.py`）。③ `--leak-selfcheck` 纳入 run 脚本**起手闸**（防空跑/泄漏污染测量窗）。④ codex 侧 token 计量接进 adapter（补外侧同口径）。⑤ 遗留：δ=1 质量损伤成对检验、旧路径列 n≥5、w2 两臂同败的第二窗复核。
