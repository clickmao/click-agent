# R563 — 判据 v2 首次作预注册判据的真机对照轮 + 起手闸振幅余量条款行使

- 日期: 2026-09-18 (cron tick 22:53–23:2x)
- 承上: R562 候选 ③④ **并轮**（③ 起手闸擦边 PASS 的振幅余量条款落地；④ 判据 v2 首次作为预注册判据参与新判决）
- 用户令 (2026-09-18): 「开工, 不许新增夹具和额外开发了」 ⇒ 本轮**零产品源码改动 / 零新增夹具 / 零新增开关**，全部复用既有件；动到代码的两处（起手闸条款、判决驱动）都声明「改的是哪一格读数」。

## 0. 纪律前置

- 轮号: `max(现有)+1`，起跑前核 `.git/ROUND_CLAIM`（无）、活动执行体（无 `run_r*` / `dotnet` / `codex`）、锁与 mtime（无新写者）。
- 预注册**先写后跑**：`eval/rover/r563/prereg-r563.json`，runner 第 0 步机检（`round` / `written_before_run` / 臂集 / `require` 计数 12 / `criterion_version` 以 `v2` 开头）。
- 同输入硬门: 冻结题面 prompt sha256 `516f3208…3aca3`（与 R559/R560 逐字节同件）；臂身份: 同一枚二进制 sha `320d0eb1…ee48`（R556 交付件，runner 机检）。
- 推送暂停令在效: 只本地 commit。

## 1. 起手闸振幅余量条款（候选③）

### 1.1 条款
```
MARGIN = max(60MB, 上一轮**同一宿主运行中**实测振幅)
REQ    = GATE_MB(2650) + MARGIN
起臂条件 = 起手读数 >= REQ ∧ 起手前样本极差 <= 50MB ∧ 连续 2 次 PASS ∧ blockers 空
运行中   = postcheck: min(mem) >= 2650, 否则该窗标 window_drift（读数不作验收依据）
行使方式 = 既有闸 eval/rover/r483/preflight_gate.py 的 --gate-mb $REQ（翻既有开关, 零新逻辑进闸）
```

### 1.2 v1 常量 → 首跑被拒（读数原样留档）
| 项 | 读数 |
|---|---|
| v1 常量 | 200MB（= R562 观测振幅 197MB 取整，**跨区制**） |
| 首跑时间 | 23:01 |
| 起手前 3 样本 | 2610 / 2609 / 2603 MB（极差 7MB） |
| REQ | 2850 MB |
| 结果 | `rc=2`，**未起臂、零臂运行** |
| 留档 | `eval/rover/r563/gate-margin-r563-v1-blocked.json` + `/tmp/r563/logs/pre-samples-v1.jsonl` + `/tmp/r563/logs/run-v1-blocked.txt` |

**定因（两条，均为器具/环境面，不归因被测）**：
1. v1 常量取自**另一区制**的振幅 ⇒ 在本宿主**结构性不可达**（清残留后顶棚最高 2813 < 2850）。与 R561 v1 判据不可达**同族**：把另一个区制的数字当成本区制的门槛。
2. 本侧 `.py` 写入经 gateway 唤起**共享语言服务器**（`pyright-langserver`，RSS **191MB**，ppid = gateway，起于 22:59:06）⇒ 顶棚 2855 → 2670；**该进程不在既有闸的 blocker 模式内**（沉默占用，闸看到的是「内存无故少 190MB」）。

**处置**：按「闸红先查残留」先核实归属（`/proc/<pid>`），再**按 pid** 清本侧残留（禁 `pkill -f`），复测顶棚 2808 ⇒ 条款 v2 放行。

### 1.3 v2 行使读数（本轮）
| 项 | 读数 |
|---|---|
| 起手前 3 样本 | 2808 / 2811 / 2808（极差 3MB） |
| MARGIN / REQ | 60（首轮取下限）/ 2710 MB |
| 闸 A1 / A2 | PASS `mem=2793` / PASS `mem=2798`（连续 2 次，REQ=2710） |
| leak-selfcheck（闸 B） | `rc=0` |
| 运行中 41 样本 | `in_min=2734 / in_max=2798 / swing=64MB / window_drift=false` ⇒ **下一轮 MARGIN=64**（数据先行） |
| 成对控制 | `--selftest` **6/6**：2 正控（下限档 / 自适应档）+ 4 负控（擦边 2652 / 抖动 150 / 低顶棚 / **v1 常量不可达参数化复现**） |

**自捕#1（条款空心化）**：条款首版把 `MARGIN` 夹到下限 25MB 并「顶棚不允许时取可用最大值」⇒ 顶棚 2700 也被放行（即 25MB 擦边被当窗口）= **空心条款**。负控 `NC_low_ceiling` 当场判 `expected 2 / got 0` ⇒ 改 **fail-closed**（余量不缩水，顶棚给不出满额余量即 `rc=2`）。

## 2. 判据 v2 首次作为预注册判据（候选④）

- 口径文本**只在** `docs/external-reference-harness.md` §12（R562 入册），`prereg-r563.json` 只**引用**，不重定义（防同一判据两份实现）。
- 判决器 `eval/rover/r563/adjudicate_r563.py`：动态载入 R561 装置，运行时仅在内存里扩展 `REPORTS['R563']`（供 VOID 臂窗归属），调用其 `judge/decide/selftest` ⇒ **零逻辑复制**；输出记录 `device_file_sha_before/after`（相同 ⇒ 保形，器具文件零改动）。

### 2.1 读数（6 新窗 w113..w118 × 2 臂）
| 臂 | 逐窗 cases/58 | 中位 | 配对中位 Δ | 单窗最小 Δ | 结论 |
|---|---|---|---|---|---|
| C1（codex 外部真值） | 58/58/58/58/58/58 | 58.0 | — | — | 真值 6/6 窗全可靠（range 0） |
| R563B0（产品默认档） | 50/58/43/58/58/55 | 56.5 | **−1.5** | **−15（w115）** | 命中 `PAIR_FLOOR ≤ −3` ⇒ 点名 ⇒ **过门失败** |

判决: `rc=1` / `FAIL(被测或前提)` / `blocked=[quality_paired_shortfall:R563B0]` / `fail_arms=[R563B0]`；`reliable_windows=6`（**无 unreliable 窗** ⇒ v2 的崩窗分支本轮未被行使）、VOID 臂窗 **0**。

### 2.2 tokens（三列分列，禁名义总量）
| 臂 | 调用 | 新算 prompt | completion | 命中率 v_all / v_incr（中继 dump 时间轴） |
|---|---|---|---|---|
| C1 | 34 | 22,418 | 18,653 | 0.9244 / 0.9520 |
| R563B0 | 6 | 906 | 13,379 | 0.9819 / n/a（每窗 1 次调用 ⇒ 无增量口径） |

### 2.3 器具面读数
- 矩阵 `matrix_r563.py`：判分一律对**副本**（`/tmp/r563/pc`），6 窗 × 2 臂 = 12 臂窗，`errors=0`，xref（矩阵 vs 落盘 `report.json`）**12/12 agree**。
- 判据器影子自检 **6/6** 无牙即 rc=2（本件）—— 实测 6/6 全绿 ⇒ 器具可用。
- 铁律 11 前置器 `--round r563` **rc=1**（blocked 3 臂窗：`w113/R563B0 50/58`、`w115/R563B0 43/58`、`w118/R563B0 55/58`；真值侧 0 blocked）⇒ **全部降幅/质量读数标「参考（未可验收）」**。

### 2.4 自捕#3（前置器的布局依赖）
`exec_precondition.py --round r563` 首跑 `rc=3 DISCOVER_FAIL`（缺 `eval/rover/r563/taskset-r563.json`），补齐后又在每个臂窗报 `missing_case_script cases/run_cases_r521.py`（缺轮目录自带的 `cases/`）。补齐**冻结件逐字节拷贝**（`taskset` sha 与 r560 件相同；`cases/run_cases_r521.py` = a67215a7…、`cases-r521.json` = 270128eb…，与器具 pin 的 sha 一致）后前置器可跑 ⇒ 12 臂窗进入验收面。

## 3. 归属与共享树（三态分列）

| 项 | 归属 | 证据 |
|---|---|---|
| R563 全部读数与器具 | `self`（本侧实施 + 本侧自跑） | 本轮 tick 的 `/tmp/r563/*` + `eval/rover/r563/*` |
| `eval/capability/kpi.jsonl` R562 行 ts 重写 + `eval/rover/r562/verdict-r562.json` 字段变更（22:55:44） | `foreign`（**同一作业的前一轮 tick**，本侧未做该改写） | mtime 22:55:44 vs 本侧时间线（本侧首个写动作 22:58+）；无活动进程，按 mtime 窗与执行体清单归属 |
| `docs/external-reference-harness.md` / `iteration-master-plan.md` 的 R562 内容 | `pre_existing`（已提交，HEAD 410fbf7） | `git log` |

## 4. 诚实边界

1. 铁律 11 `rc=1` ⇒ 本轮**任何降幅/质量读数不得作验收依据**（含「本侧 vs 真值」的 −1.5 中位）。
2. 分歧主源是**单窗 w115（−15）**；n=6 窗，且与 w104..w112 旧窗**并列不相减**（新窗非同一窗集延续）。
3. v2 的 `unreliable` 分支与 VOID 分支**本轮均未被行使**（真值 6/6 全可靠、零 VOID 臂窗）⇒ 这两条分支只有 R561 影子自检（S3/S4/S6）作证，尚无真机实例。
4. 条款余量受宿主顶棚限制（2808 − 2710 = 98MB）；语言服务器「沉默占用」**仅登记未修**（修它属新增开发，用户令禁止）。
5. 单轮读数不得当承诺（跨窗摆动常大于效应）；本轮只作 v2 口径下的**一次**真机读数。

## 5. 复现命令

```bash
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
cd /home/agentuser/AgentFramework
python3 eval/rover/r563/gate_margin_r563.py --selftest
D=/tmp/r563 PORT=49443 WIN0=113 NWIN=6 bash eval/rover/r563/run_r563.sh
python3 eval/rover/r563/matrix_r563.py --out eval/rover/r563/percase-matrix-r563.json --work /tmp/r563/pc
python3 eval/rover/r563/adjudicate_r563.py --matrix eval/rover/r563/percase-matrix-r563.json --out eval/rover/r563/verdict-r563.json
python3 eval/rover/r507pre/exec_precondition.py --round r563 --out eval/rover/r507pre/precondition-r563.json
```

## 6. 下轮候选（R564）

① wythoff 族修复（须动契约/产品分支 ⇒ **待放行**）② 交付闸/停止条件（rc=8/rc=5 仍交付 ⇒ 新增产品分支 ⇒ **待放行**）③ 条款按本轮实测 `swing=64` 派生行使（`--prev-swing-mb 64` ⇒ `REQ=2714`）④ **w115 单窗 −15 的族级只读定因**（复用 `eval/rover/r562/wythoff_cause_r562.py`，零产品改动）。
