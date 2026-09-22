# R633 · DAG（意图 → 子任务：节点 / 依赖边 / 可并行面 / 收尾重启判据）

意图：**主线自检** = 用真实开发任务（随机程序/数学题冻结题集）在「同环境·同输入·同模型」下与外部真值 codex 对照，
本轮行使的是 RF0005 §2 固定环 + R632 登记的候选①（造窗，解除 rc=3 停链）与候选③（文献小步），
候选②（wythoff 冷点集修法）只做只读取证（产品码改动需放行）。

## 节点与依赖边

| 节点 | 动作 | 依赖 | 写面 | 出口判据 |
|---|---|---|---|---|
| N0 | 起手闸 `roundcheck preflight --round R633` | — | 只读 | rc=0（P1–P8 全 PASS） |
| N1 | 主线提醒（读 §7 + improvements + v0.22 计划） | N0 | 只读 | 1 行结论 |
| N2 | 选靶：R632 候选台账 → 本轮并轮清单 | N1 | 只读 | 候选 ①②③ 全列，无静默丢项 |
| N3 | 预注册 `prereg-r633.json`（先写后跑） | N2 | `eval/rover/r633/` | 机检闸（arms/windows/无轴声明/unreliable_policy）过 |
| N4 | 真机臂轮（新窗 w225..w227 × codex×1 + 产品×3） | N3 | `$HOME/.agentframework/harness/runs/r633` + `eval/rover/r633/{snapshots,evidence}` | runs.jsonl 12 行；每窗 judge `--win` 落盘 |
| N5 | 判决 + 铁律 11 前置器 | N4 | `eval/rover/r633/` | `verdict-r633.json` rc 分层 + `precond-r633.json` rc |
| N6 | 只读取证：wythoff 自证边界（公开用例 vs 隐藏用例） | N4（只读 R631/冻结 run 目录） | `eval/rover/r633/evidence/` | 逐跑次 public/hidden 二分表 |
| N7 | 文献小步（arXiv ≤3 query / 全文 ≤2 篇 / 间隔 ≥4s） | N0（可并行） | `docs/research/lit-review-ledger.md`（追加） | 台账 +1 段；出口不可达则记顺延 |
| N8 | 收口五件（轮志/证据文档/registry/kpi 行/逐名列名提交） | N5,N6,N7 | 全仓 | `status_gen --check` PASS ∧ 形式门禁 14/14 |

## 可并行面

- **可并行（只读）**：N6（读冻结快照，不写产品面、不重算飞窗）。
- **禁并行**：N4 在飞期间禁并行 build / 单测 / publish（会把起手闸余量抬到千 MB 级并污染内存读数）；
  也禁在本轮写 `src/`（兄弟写者与在飞窗不可区分）。
- N7（文献）安排在 N4 之后执行，避免抢 CPU/网络影响真机窗口的纯净性（承「测量窗口内不做吃 CPU 的活」）。

## 收尾重启判据（不重跑全轮）

- N5 rc=3（有效窗 <2）⇒ **只重开 N4**（补窗，禁调阈值）。
- N5 rc=2（器具缺陷）⇒ 只重开 N5 的对应判据器段 + 重审 N4 冻结面（不重测）。
- 前提闸（起臂前 fail-closed）未过 ⇒ 只重开 N4 起臂段。
- N8 形式门禁红 ⇒ 只重开 N8 对应件（不改 N4 读数）。
