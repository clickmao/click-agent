# R619 DAG（RF0004.2 · M3 **第三刀 = 空候选回退**）

协议：`docs/plans/RF0005-completion-protocol.md` §2 固定环 0–9 ｜ 单变量：`AGENTFRAMEWORK_R1_ACTION_EXEC`（含本轮新增的回退语义）
窗集：**w211..w213**（与历史 w184..w210 不相交）｜ 臂：T×9 / C×9 / C1(codex 真值)×3 = 21 跑次

## 节点 / 依赖 / 可并行面 / 重启判据

| 节点 | 动作 | 依赖 | 可并行 | 出口证据 |
|---|---|---|---|---|
| N0 | 起手闸 `roundcheck preflight --round R619` + 清 VBCSCompiler/pyright | — | 与 N1/N2 并行 | `rc=0`（FAIL 0 / WARN 0）· 落盘 MemAvailable 前后 |
| N1 | 主线提醒 1 行（读 §7 + RF0004 + r618 verdict） | — | 与 N0/N2 并行 | 报告首行 |
| N2 | 选靶逐例归因（r618 D1/D2/D3 台账回放） | — | 与 N0/N1 并行 | 缺口表（族/形态/计数） |
| N3 | 文献小步（arXiv ≤3 query / 全文 ≤2 / 间隔 ≥4s） | 起手闸后 | **与 N5/N6 并行**（只读网络，不写仓、不抢内存） | 台账追加行（8 列） |
| N4 | 预注册 `prereg-r619.json`（**先写后跑闸**，臂前落盘） | N2/N3 | — | 文件 mtime < 首臂时刻 ∧ runner 机检过 |
| N5 | 产品侧最小改动 = 空执行面回退（`src/agent/r1/R1Pipeline.cs` + `R1Transcript.cs` 第五字段 + 单测） | N4 | 与 N3 并行（N3 不碰源树） | diff 只落 2 源文件 + 1 测试文件 |
| N6 | 构建：定向测试 + AOT publish `artifacts/pub_r619/agenthost` | N5 | 与 N3 并行 | `PUBLISH_RC=0 / IL_WARNINGS=0` + sha256 |
| N7 | 真机跑 21 跑次（T/C/C1 × w211..w213） | N6 ∧ N4 | — | `logs/runs.jsonl` / `snapshots/` / `bin-sha-check.json` |
| N8 | 判决 `judge_r619.py` + 铁律 11 前置器 `exec_precondition --round r619` | N7 | — | `verdict-r619.json` + `precond-r619.json` |
| N9 | 收口五件 + `status_gen.py --check` + 形式门禁 + 逐名列名 commit | N8 | — | `PASS (违规 0 / 基准漂移 0 / 缺源 0)` ∧ 14/14 |

## 收尾重启判据（按 DAG 判「该重启哪条边」，不重跑全轮）

| 症状 | 定因面 | 重启边 |
|---|---|---|
| 预注册机检不过 | 器具面 | 只改 N4（禁改阈值/判据） |
| AOT `rc≠0` / IL 告警 > 0 | 构建面 | 只重启 N6 |
| `bin_sha_stable=false` / 两侧夹具 md5 不同 | 臂身份面 | 只重启 N7（N4/N6 不动） |
| 判据器读空 / 键缺失 | **器具面（首选假设）** | 只重启 N8 后处理（**禁重测**） |
| 铁律 11 `rc=3`（输入缺失） | 器具面 | 补 `cases/` 逐字节件后只重跑后处理 |
| 守恒违例 > 0 | 映射器/回退面 | 撤回未提交 `src/` ⇒ 净产品改动 0，只留轮工件 |

## 并行纪律

- 只有 **N3（文献，只读网络）** 可与 N5/N6 并行；N3 不写仓、不起子 agent、不抢内存。
- 同仓写者：起手前已核 `pgrep` = 空 ∧ 无 `.git/ROUND_CLAIM` ⇒ 本侧独占。
- N7 期间**禁** `dotnet build` / `dotnet test`（构建会把起手闸余量抬到千 MB 级，并违「批测/单测/build 三者互斥」）。
