# R627 · DAG（起手先行）

**意图**：推进 RF0005 §2 固定环（面 4 · 上下文精排 / 召回面），本轮 = **器具面判据形态修法轮**（承 R626 单列的 `P4-pos-prereg-form` 缺陷）+ 文献小步恢复 + 未闭合候选并轮。**零产品源码改动**。

## 节点 / 依赖边 / 并行面

| 节点 | 内容 | 依赖 | 写盘面 | 并行性 |
|---|---|---|---|---|
| N0 | 起手闸 `roundcheck preflight --round R627` | — | 无 | 必需前置 |
| N1 | **候选②**：P4 正控判据形态修法（同形口径 oracle：RRF 融合 ∧ 单路 ∧ 配错 三形态） | N0 | `eval/rover/r627/`（本仓独立目录） | 与 N2/N3 无依赖边 |
| N2 | **候选④**：文献小步（出口可用性前置探针 → ≤3 检索式） | N0（出口探针） | `docs/research/lit-review-ledger.md`（**追加**，禁整档回写） | 与 N1 无依赖边（不同写盘面） |
| N3 | **候选⑤** 只读并轮：R619 遗留面状态机检 + wythoff 面读数登记 | N0 | `eval/rover/r627/`（只读结论） | 与 N1/N2 无依赖边 |
| N4 | 收口：registry 行 + kpi 行（带 `baselines`）+ 报告 + `status_gen.py --check` | N1,N2,N3 | `docs/verification-registry.json` / `eval/capability/kpi.jsonl` / `docs/reports/iteration-master-plan.md` §7 | 串行（写同仓） |

## 并行纪律

- 本轮**不开子 agent**：N1/N2/N3 写盘面互斥但均为本侧串行执行，无双写者风险；文献检索按用户令「禁为此开子 agent 抢仓」。
- N1 跑前须显式确认同仓无在飞写者（`pgrep -af` 扫执行体）+ `src/` 工作树脏净基线（P5 零回归判据）。
- 起手前按令清 `VBCSCompiler`/`MSBuild`/`pyright`（内存闸口径）。

## 收尾重启判据（按 DAG 判「该重启哪条边」）

| 情形 | 重启边 |
|---|---|
| N1 正控 < 阈值（同形口径复现失败） | **只重启 N1**（不重跑 N2/N3，不重跑全轮）；新增器具缺陷单列，R626 读数不翻案 |
| N2 出口不可达 | N2 记「顺延」+ 一行原因；**不重启**（顺延计数入台账） |
| N4 机检红（registry/kpi/status_gen） | **只重启 N4**（N1/N2/N3 产物已冻结） |
| `src/` 出现非本轮改动 | 停 N4，先判归属（mtime 时间窗 + `pgrep`），不重跑读数 |
