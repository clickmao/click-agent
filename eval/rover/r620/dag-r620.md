# R620 DAG（RF0004.2 · M3 **第四刀 = 回退分支真机行使**）

协议：`docs/plans/RF0005-completion-protocol.md` §2 固定环 0–9
单变量：`AGENTFRAMEWORK_R1_ACTION_EXEC`（T=1 / C=unset，产品缺省 off）
held-constant 上下文：`AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy`（**两臂同值**，非被测变量）
窗集：**w214..w216**（与历史 w184..w213 不相交）｜ 臂：T×9 / C×9 / C1(codex 真值)×3 = 21 跑次
被测件：**与 R619 同件**（`artifacts/pub_r619/agenthost` 逐字节，sha256 `a184d7317b6e3c5e…`）⇒ 零产品源码改动

## 意图 → 子任务

R619 第三刀把「映射面为空 ∧ plan 非空」改成回退读 `plan`，但其触发前提（候选键未到达）在 9 个治疗跑次里
**从未成立**（J1e = NOT_EXERCISED）⇒ 修复代码**从未被真机行使**。本轮的意图 = 把前提造出来并判「回退是否真生效」。

## 节点 / 依赖 / 可并行面 / 重启判据

| 节点 | 动作 | 依赖 | 可并行 | 出口证据 |
|---|---|---|---|---|
| N0 | 起手闸 `roundcheck preflight --round R620` + 清 VBCSCompiler/pyright | — | 与 N1/N2 并行 | `rc=0`（FAIL 0 / WARN 0）· 落盘 MemAvailable 前后 |
| N1 | 主线提醒 1 行（读 §7 + RF0004 + r619 verdict） | — | 与 N0/N2 并行 | 报告首行 |
| N2 | 选靶逐例归因（r619 U1 台账回放） | — | 与 N0/N1 并行 | 缺口表（回退 0/9 行使） |
| N3 | 文献小步（arXiv ≤3 query / 全文 ≤2 / 间隔 ≥4s） | 起手闸后 | **与 N5 并行**（只读网络，不写仓、不抢内存） | 台账追加行（8 列） |
| N4 | 预注册 `prereg-r620.json`（**先写后跑闸**，臂前落盘） | N2 | — | 文件 mtime < 首臂时刻 ∧ runner 机检过 |
| N5 | 产品侧改动 = **零**（复用 R619 既有轴/回退代码；本轮只造触发前提） | N4 | 与 N3 并行 | `git diff --stat src/` 为空 |
| N6 | 派生件生成 `derive_r620.py`（run/judge/selftest 逐条声明替换 + `--check`） | N4 | — | 补丁逐条命中数 == 1；题集逐字节同源 sha12 相同 |
| N7 | **前提闸**（起臂前 1 跑次）：legacy 档 ⇒ 候选键未到达 ∧ `exec_source=plan_fallback` ∧ 前缀 == legacy 锚 | N6 | — | `premise-r620.json` rc=0（不过 ⇒ 零臂起跑 rc=5） |
| N8 | 真机跑 21 跑次（T/C × w214..w216 ×3 + C1 ×3） | N7 | — | `logs/runs.jsonl` / `snapshots/` / `bin-sha-check.json` |
| N9 | 判决 `judge_r620.py` + 影子自检 + 铁律 11 前置器 `exec_precondition --round r620` | N8 | — | `verdict-r620.json` + `precond-r620.json` |
| N10 | 收口五件 + `status_gen.py --check` + 形式门禁 + 逐名列名 commit | N9 | — | `PASS (违规 0 / 基准漂移 0 / 缺源 0)` ∧ 14/14 |

## 收尾重启判据（按 DAG 判「该重启哪条边」，不重跑全轮）

| 症状 | 定因面 | 重启边 |
|---|---|---|
| 前提闸 rc=5 | 触发面（held-constant 未生效 / 候选键仍到达） | 只改 N5/N6 的触发面设计（**禁改判据**），不重跑臂 |
| 预注册机检不过 | 器具面 | 只改 N4（禁改阈值/判据） |
| 判据器读空 / 键缺失 | **器具面（首选假设）** | 只重启 N9 后处理（**禁重测**） |
| 铁律 11 `rc=3`（输入缺失） | 器具面 | 补 `cases/` 逐字节件后只重跑后处理 |
| J6 等价面不成立 | 回退面 | 撤回未提交 `src/`（本轮本就零改动）⇒ 单列并列为下轮第一优先 |
| `bin_sha_stable=false` | 臂身份面 | 只重启 N8（N4/N6 不动） |

## 并行纪律

- 只有 **N3（文献，只读网络）** 与 N5（零改动核对）可并行；N3 不写仓、不起子 agent、不抢内存。
- 同仓写者：起手前核 `pgrep` = 空 ∧ 无 `.git/ROUND_CLAIM` ⇒ 本侧独占。
- N8 期间**禁** `dotnet build` / `dotnet test`（构建会把起手闸余量抬到千 MB 级，并违「批测/单测/build 三者互斥」）；
  本轮零产品改动 ⇒ **不做 AOT 重发布**（被测件与 R619 同件，`bins-r620.json` 钉 sha）。
