# R590 DAG（起手先出；执行后按此判「该重启哪条边」）

## 意图
主线**只读定因/入册轮**：在 R585–R588 四窗集（12 窗 × 48 跑次 = 真值 12 + 产品 36）的**在盘件**上，把 R589 块列出的候选 ②③④⑤ **并轮**收口。
候选 ①（本轴缺口定案后的处置裁定：直进产品侧修复 / 换更长题面）**须用户放行** ⇒ 本轮不动。
**零新臂 / 零远端调用 / 零产品源码改动 / 零新增夹具 / 零新增开关。**

## 节点 / 依赖边 / 可并行面

| 节点 | 内容 | 依赖 | 写者面 |
|---|---|---|---|
| N0 | 起手：key 自备、在盘数据完整性（12 窗 × 36 产品跑次）、进程/内存闸、**预注册先写后跑** | — | `eval/rover/r590/prereg-r590.json`、`dag-r590.md` |
| N1 | 候选② 只读普查 `escape_form_census_r590.py`：目标形态（契约块内**过度转义**：双反斜杠 + `n`）在 36 产品跑次的出现率 × 与「整族塌陷」「交付缺席」的相关性 + 成对负控 | N0 | `eval/rover/r590/escape-census-r590.json` |
| N2 | 候选④ 起手闸余量条款重派生（R589 **零臂 ⇒ 无在飞窗振幅**）+ 真机行使（A1/A2 + 判别力成对 + leak-selfcheck） | N0 | `eval/rover/r590/gate-margin-r590.json`、`gate_r590.sh` |
| N3 | 候选⑤ 前置器 project 布局**耗时口径**（只读时间戳复算；给出「只读轮抽样复跑」替代口径 + fail-closed 条件） | N0 | `eval/rover/r590/precond-cost-r590.json` |
| N4 | 候选③ 判据面**入册**：`docs/external-reference-harness.md` §12 增「判据 v3（整题全对率 + 按族分列）」，v2 保留 + 作废登记 + 跨版本禁相减 | N0 | `docs/external-reference-harness.md` |
| N5 | 只读性指纹（runs/snapshots 前后 sha256 一致） | N1,N3 | `eval/rover/r590/readonly-fingerprint-r590.json` |
| N6 | 收口：`verdict-r590.json` + `kpi-table-r590.json` + `report-r590.md` + 台账行（`eval/capability/kpi.jsonl`）+ §7 块 + `docs/improvements.md` | N1,N2,N3,N4,N5 | `eval/capability/kpi.jsonl`、`docs/reports/*`、`docs/improvements.md` |
| N7 | 提交（**本地 only**；推送暂停令在效） | N6 | git index |

## 并行面
- N1/N3/N5 **只读**且不写 `~/.agentframework/harness/runs/**`；N2 行使起手闸（只写 `~/.agentframework/harness/runs/r590/logs/*`，与只读面**无交集**）⇒ 理论可并行。
- **本轮不开子 agent**（无「不写同仓」的节点：N4/N6 写 `docs/`）。
- 本 tick 按**串行**执行以保读数纯净（与 R589 同处置）。

## 收尾重启判据（按 DAG 判，不重跑全轮）
- N1 器具有牙性不足（任一成对控制不翻面）⇒ **只修 N1 并重跑 N1**，首跑读数留档不翻案。
- N1 rc=3（在盘数据残缺）⇒ 只补读缺失跑次，**不重跑任何真机臂**（本轮无真机臂）。
- N2 起手闸 fail-closed（顶棚装不下下限）⇒ 回收本会话工具子进程后**只重跑 N2**。
- N4 文档写入异常 ⇒ 只重跑 N4（幂等）。
- N6/N7 失败 ⇒ 只重跑后处理（幂等），不重测。

## 候选①（待用户裁定）本轮不动项
`(b)` 直进产品侧修复 = 动产品源码，须放行；`(c)` 换更长题面 = 改可比性 ⇒ 新基线，非可自决。
二者在本轮只**登记为待裁定**，不产出交付物。
