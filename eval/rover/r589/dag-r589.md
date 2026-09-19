# R589 DAG（起手先出；执行后按此判「该重启哪条边」）

## 意图
主线**判据面切换轮**：在 R585–R588 四窗集（12 窗 × 48 跑次）的**在盘机械判分件**上，把质量判据面从
「用例级通过数」切换为「**整题全对率（58/58）+ 按族分列**」，回答 R588 候选①（本轴缺口换判据面后是否仍成立）。
**零新臂 / 零远端调用 / 零产品源码改动 / 零新增夹具 / 零新增开关。**

## 节点 / 依赖边 / 可并行面

| 节点 | 内容 | 依赖 | 写者面 |
|---|---|---|---|
| N0 | 起手：key 自备、数据完整性（48×58）、内存/进程闸、预注册先写后跑闸 | — | 只读 + `eval/rover/r589/prereg-r589.json` |
| N1 | 只读并池器 `pool_taskface_r589.py`（两面重算 + 按族 + 配对 + 摆动/效应 + C6/C7） | N0 | `eval/rover/r589/taskface-pool-r589.json` |
| N2 | 起手闸行使（A1/A2 正控 + 判别力成对 + leak-selfcheck） | N0 | `eval/rover/r589/gate-*.json` |
| N3 | C5 只读性：runs/snapshots 前后 sha256 清单 | N0,N1 | `eval/rover/r589/readonly-fingerprint-r589.json` |
| N4 | 铁律 11 前置器逐轮（r585..r588） | N0 | `eval/rover/r589/precond-*.json` |
| N5 | 候选② `charlevel_bisect_r589.py`（契约块元素级删除二分，只读冻结件） | N0（**可与 N1 并行**：只读、零重算、不碰 runs/） | `eval/rover/r589/charlevel-bisect-r589.json` |
| N6 | 候选③ `codex_cost_cause_r589.py`（adapter 逐调用分类） | N0（只读） | `eval/rover/r589/codex-cost-cause-r589.json` |
| N7 | 候选④⑤（脱钩占比 / per-tag gap 定案）：并入 N1 输出与只读复读 | N0 | `eval/rover/r589/taskface-pool-r589.json` |
| N8 | 收口：`verdict-r589.json` + `kpi-table-r589.json` + `report-r589.md` + 台账行 + §7 块 + 轮志 | N1,N3,N4,N5,N6 | `eval/capability/kpi.jsonl`、`docs/reports/*`、`docs/improvements.md` |
| N9 | 提交（本地 only；推送暂停令在效） | N8 | git index |

## 并行面
- N5/N6 **只读**且不写 `~/.agentframework/harness/runs/**` ⇒ 可与 N1 并行段共存（本 tick 按串行执行以保持读数纯净与可复现）。
- 本轮**无真机臂** ⇒ 无内存/端口争用面；起手闸仍行使（只读轮纪律）。
- 无「不写同仓」的节点 ⇒ **本轮不开子 agent**（同仓有在飞写者面：`docs/reports/*`）。

## 收尾重启判据（按 DAG 判，不重跑全轮）
- N1 rc=3（数据残缺）：只补读缺失跑次，**不重跑任何真机臂**（本轮无真机臂）。
- N1 负控无牙（C7 不变）：**只修器具 + 重跑 N1**，保留首跑读数（不翻案）。
- N5/N6 器具异常：只修该边并重跑该边。
- N8/N9 失败：只重跑后处理（幂等），不重测。
