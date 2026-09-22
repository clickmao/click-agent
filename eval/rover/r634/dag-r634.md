# R634 · DAG（意图 → 子任务：节点 / 依赖边 / 可并行面 / 收尾重启判据）

意图：**主线自检**（宪法级）＝ 用真实开发任务（随机程序/数学题冻结题集）在「同环境·同输入·同模型」下
与外部真值 codex 对照，对本项目做质量自检。本轮行使 RF0005 §2 固定环 + R633 登记的候选①（**预注册判据修正**
= 主判据 rc=3 的直接解除条件）、候选③（超时跑次成因只读分诊）与文献小步；候选②（`wythoff` 冷点集修法）
需放行 ⇒ 本轮只读、零产品码改动。

## 节点与依赖边

| 节点 | 动作 | 依赖 | 写面 | 出口判据 |
|---|---|---|---|---|
| N0 | 起手闸 `roundcheck preflight --round R634 --min-avail-mb 2710`（R633 实测 swing 38 → clamp floor 60） | — | 只读 | rc=0（P1–P8 全 PASS） |
| N1 | 主线提醒（读 §7 + RF0004 + 上轮 verdict + 最新 v0.22 计划） | N0 | 只读 | 1 行结论（并入报告首行） |
| N2 | 选靶：R633 候选台账 → 本轮并轮清单（候选①②③④⑤逐条截记） | N1 | 只读 | 候选全列，无静默丢项 |
| N3 | 预注册 `prereg-r634.json`（**先写后跑**；窗有效性修正声明在本节点落盘） | N2 | `eval/rover/r634/` | 起臂前机检闸（arms/windows/无轴声明/**修正版 unreliable_policy**/falsification≥2）过 |
| N3b | 判据器影子自检 `judge_r634.py --selftest`（**六态**） | N3 | `selftest-r634.json` | rc=0；且 `TRUTH_SELF_FAIL_NOW_VALID.valid==3`（修正有牙）∧ `TRUTH_VOID.valid==2`（未放宽） |
| N4 | 真机臂轮（新窗 `w228..w230` × codex×1 + 产品×3） | N3b | `$HOME/.agentframework/harness/runs/r634` + `eval/rover/r634/{snapshots,evidence}` | `runs.jsonl` 12 行；每窗 `judge --win` 落盘；`bin-sha-check` 稳定 |
| N5 | 判决 + 铁律 11 前置器 | N4 | `eval/rover/r634/` | `verdict-r634.json` rc 分层 + `precond-r634.json` rc |
| N6 | 只读诊断：R633 VOID 跑次（`cli_rc=124`）本轮复现率与形态归类 | N4（只读） | `eval/rover/r634/evidence/` | 逐跑次表；**禁**先归因被测 |
| N7 | 文献小步（arXiv ≤3 query / 全文 ≤2 篇 / 间隔 ≥4s） | N0（可并行） | `docs/research/lit-review-ledger.md`（追加） | 台账 +1 段；出口不可达则记顺延 |
| N8 | 收口五件（轮工件/证据文档/registry/kpi 行带 `baselines`/逐名列名提交） | N5,N6,N7 | 全仓 | `status_gen --check` PASS ∧ 形式门禁 14/14 |

## 可并行面

- **可并行（只读）**：N6（读冻结快照，不写产品面、不重算飞窗）；N7 的网络/磁盘面与 N4 的 CPU 面互不争用，
  但按 R633 先例**排在 N4 之后**执行，避免抢核影响真机窗口纯净性（承「测量窗口内不做吃 CPU 的活」）。
- **禁并行**：N4 在飞期间禁 build / 单测 / publish（会把起手闸余量抬到千 MB 级并污染内存读数）；
  也禁在本轮写 `src/`（兄弟写者与在飞窗不可区分）。
- **禁开子 agent 抢仓**：文献小步不开子 agent（用户令）。

## 收尾重启判据（不重跑全轮）

- N5 rc=3（有效窗 <2）⇒ **只重开 N4**（补窗，禁调阈值）——若修正已生效而仍 <2，按 F3 **照原样判 rc=3**。
- N5 rc=2（器具缺陷）⇒ 只重开 N5 对应判据器段 + 重审 N4 冻结面（**不重测**）。
- 前提闸（起臂前 fail-closed）未过 ⇒ 只重开 N4 起臂段。
- N8 形式门禁红 ⇒ 只重开 N8 对应件（不改 N4 读数）。
- 缺派生件（如 `precond-r634.json`）⇒ 只重跑**后处理**，不重测（承 RF0005 §10）。
