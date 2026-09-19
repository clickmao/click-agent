# R585（主线对照轮 · 器具环境恢复后首次可起臂）

**轮类型**: 主线对照轮（外部真值 codex 同窗对照）｜**产品源码改动**: 零｜**新增夹具语义**: 零｜**新增开关**: 零
**臂**: `C1`（外部真值 codex-cli，同模型 deepseek-flash） ×  `R585D`（产品**默认档**：三枚剂量键显式 unset）
**窗**: `w154 / w155 / w156`（3 窗，每窗 = 真值 ×1 + 产品 ×3 reps）
**冻结题集**: `eval/rover/r585/taskset-r585.json`（与 R559–R583 同件 sha `e0c667c2…`，逐字节复制）
**二进制**: `~/.agentframework/artifacts/pub_r585/agenthost`（NativeAOT，sha `4b70fd7c…`；运行前后 sha 一致断言 `bin_sha_stable=true`）

## 1 结论（预注册判据，照原样判）

| 判据 | 结果 | 读数 |
|---|---|---|
| C0 真值可靠性 | **含 1 不可配对窗** | `w154` 真值自身 56/58（`wythoff#55-hidden`, `wythoff#57-hidden`）⇒ 标 unreliable、不进配对；`w155/w156` 真值 58/58 |
| C1 质量配对（主判据） | **FAIL** | 配对差（产品 − 真值，逐窗）= `[-8, -3]`，中位 **−5.5**（预注册中位下限 `−2`，未过）；逐窗下限 `−15` 全过；有效窗 2（≥2 成立） |
| C2 成本三列 | 信息项 | 见下表（**因铁律 11 rc=1 ⇒ 降幅一律标「参考（未可验收）」**） |
| 铁律 11 可验收前置 | **rc=1（未可验收）** | `executable_and_correct=false`；`self_report_agrees=true`、`self_report_mismatch=[]`（独立物化实跑与在跑自报**逐条一致**） |
| 总判决 | **rc=1 FAIL(质量配对未过)** | `verdict.blocked=[C1_quality_paired:R585D]` |

## 2 读数（真机，落盘件 `kpi-summary-r585.json` / `kpi-table-r585.json`）

| 臂 | 回复质量（逐窗中位） | 中位 | 极差（跨窗） | 调用 | 新算 prompt | completion | 命中率 v_all / v_incr | 步数 | rc |
|---|---|---|---|---|---|---|---|---|---|
| C1 真值（codex） | w154 56 / w155 58 / w156 58 | 58 | 2 | 74 | 28,392 | 23,907 | 0.97 / 0.97 | n/a | null |
| R585D 产品默认档 | w154 58 / w155 50 / w156 55 | 55 | 8 | 20 | 5,601 | 48,941 | 0.97 / 0.96 | 未测 | [0,0,5,8,5,5,5,5,5] |

**产品逐跑次**（同窗同二进制，真实摆动）: w154 `58/58/58`；w155 `53/50/47`；w156 `58/48/55`

## 3 逐例归因（失败族，`per-case-failures-r585.json`）

- **失败 100% 集中在 `wythoff` 单族**（w154 真值 2 例；w155 产品 5/8/11 例；w156 产品 0/10/3 例）⇒ 与「一个模块缺陷带走整族」结构一致，分数对单模块极敏感。
- 失败形态分列：`stdout_mismatch`（真错输出）为主；`TimeoutExpired` 8 例仅在 w155-r2（固定 60s 截止）；`rc=1` 2 例（w155-r1）。
- **TimeoutExpired 两条独立路径互证**：在跑自报 8 例超时 ∧ 铁律 11 前置器独立物化重跑该跑次亦 `rc=124`（50/56，另 2 例因其自身超时未测）⇒ **不是采集侧假红**，是该产物在这些用例上真的不收敛/极慢（诚实边界：前置器 56 分母 < 58）。
- 真值自身在 w154 挂 2 例（`wythoff#55/57-hidden`）⇒ 依预注册该窗不作配对，**该 2 例单列**，不记作我方缺陷。

## 4 本轮自捕的器具缺陷（2 件，均未放宽任何判据）

1. **闸输出读契约**（起臂前自捕，fail-closed 生效）: 交付的 `run_r585.sh` 首版以 `json.load(stdin)` 读闸输出，而闸 stdout = pretty JSON **＋ 尾行 `out <path>`** ⇒ 解析异常被吞成空串 ⇒ 起手闸 A1 读成「未过」并 `exit 2`（**未起臂，零污染**）。修法 = 读 `--out` 落盘件（与 R571 同形）。**该失败跑次留痕** `logs/run.txt` 22:23 段，未翻案。
2. **KPI 判据器残留臂名**（后处理面）: 派生脚本遗留 `out["arms"]["R585M1"]` 引用（本轮无剂量轴）⇒ 汇总 `KeyError`、`rc=1`。修法 = 删残留两行；**只重跑后处理**（不重测），重跑后汇总与原始读数一致（`readings.jsonl` 未变）。原始 traceback 留档 `logs/run.txt` 22:42 段。

## 5 起手闸与判别力（共享机口径）

- 条款: 阈值 + 观测振幅余量（R571 实测 `swing_mb=105`）+ 连续 2 次 ⇒ `REQ=2713`（`ceiling=2773`，`cap=63`，余量按上界夹取）。
- 真机: A1 PASS（2768MB）/ A2 PASS（2761MB）；**判别力成对控制 rc=0**（压制到带内 ⇒ 基础门槛 PASS ∧ 条款 GATE_BLOCKED ⇒ 闸确行使）；泄漏自检 rc=0。
- 起臂前清场: 本会话工具子进程（2 个 LSP，RSS 317MB）按 pid 清除 ⇒ `MemAvailable` 1906→2890MB（同 R571 记录形态）。

## 6 诚实边界

- **降幅不可作验收依据**: 铁律 11 rc=1 ⇒ 调用 −73% / 新算 prompt −80% 只作**参考**；completion **+105%**（产品收尾叙述显著更长）单列，不得用调用下降掩盖。
- 质量列: 主判据 FAIL（中位 −5.5 < −2）⇒ **产品默认档本轮质量未达判据**；跨窗摆动 8 例 > 部分臂间差 ⇒ 单窗读数不作能力结论。
- w154 因真值自身失败不可配对 ⇒ 有效窗仅 2（预注册下限恰为 2，未加窗）。
- `steps_executed/plan_steps_total`（轮数列）本轮**未测**（adapter 未取该字段）⇒ 表内写「未测」。
- 真值臂 rc 字段为 null（外部 CLI 不产本仓 rc 语义）。

## 7 落盘件

- 预注册（先写后跑闸）: `eval/rover/r585/prereg-r585.json`（12 条 `evidence_scope.require`，`arms={C1,R585D}`，`criterion_version=v2`）
- DAG: `eval/rover/r585/dag-r585.md`｜驱动器: `eval/rover/r585/run_r585.sh`｜判据器: `eval/rover/r585/kpi_r585.py`
- 读数: `kpi-summary-r585.json`、`kpi-table-r585.json`、`per-case-failures-r585.json`、`bins-r585.json`、`bin-sha-check.json`
- 铁律 11: `~/.agentframework/harness/runs/r585/precond-r585.json`（`precond.rc=1`）
- 快照: `eval/rover/r585/snapshots/w15{4,5,6}/<arm>/g1/`
- 台账: `eval/capability/kpi.jsonl`（R585 行，键集与同族既有行逐字相同）
- 运行根（稳定路径，**不再只存 /tmp**）: `~/.agentframework/harness/runs/r585/`
