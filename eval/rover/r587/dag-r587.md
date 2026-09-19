# DAG · R587（cron 60min tick, 2026-09-20）

**意图（一句话）**：主线对照轮 —— ① 同件扩窗 `w157..w162`（R586 三窗 + 本轮三窗**并列**，禁相减）以收紧「单跑次摆动」估计；
② 收口 R586 登记的**全部 6 项候选**（`wythoff` 同子规格定因 · `EMPTY_OR_ERROR` 定因 · 有效窗下限口径收口 · 成本按跑次归一入册 · 扩窗 · 审计器作用域分支）。
零产品源码改动 / 零新夹具语义 / 零新开关（被测件与 R585/R586 同 sha）。

## 节点 / 依赖边

| 节点 | 内容 | 依赖 | 写面 | 真机 |
|---|---|---|---|---|
| N0 | DAG + 预注册（`dag-r587.md` / `prereg-r587.json`，含 `audit_scope` 声明） | — | `eval/rover/r587/` | 否 |
| N1 | **①** `wythoff` 同子规格定因（只读：9 份产物 `games/wythoff.py` 逐份 sha + 静态读冷点判据形态 + 归类映射到失败类别） | — | `eval/rover/r587/wythoff-subspec-r587.json` | 否 |
| N2 | **②** `EMPTY_OR_ERROR` 定因（只读：冻结快照副本重放 + 捕获 stderr/rc，判「崩溃·空产物」是否同源） | — | `eval/rover/r587/empty-error-cause-r587.json` | 否（本地重放） |
| N3 | **⑤** 真机臂：3 新窗 `w160..w162`，每窗 = 真值 codex ×1 + 产品默认档 ×3（12 跑次，独立会话） | N0 | `$HOME/.agentframework/harness/runs/r587/**` + `eval/rover/r587/snapshots/**` | **是** |
| N4 | 汇总判决器（C0/C1/C2 + **C5 六窗并列摆动** + **C8 成本按跑次归一** + C6/C7） | N3 | `kpi-table-r587.json` / `verdict-r587.json` | 否（后处理） |
| N5 | 铁律 11 前置器（两侧产出物独立物化实跑） | N4 | `eval/rover/r507pre/precondition-r587.json` | 本地实跑 |
| N6 | **⑥** 审计器作用域分支（零产品源码改动对照轮）：`tools/roundcheck/roundcheck.py` + `--selftest` 负控（声明生效/未声明旧行为不变/声明但碰 `src/**` 必红/读数件缺必红） | — | `tools/roundcheck/roundcheck.py` | 否 |
| N7 | **③④** 判据面收口：有效窗下限显式二选一写进预注册与轮志；成本列按跑次归一口径入册（`kpi.jsonl` 行含 per-run 三列） | N4 | `kpi.jsonl` / `report-r587.md` | 否 |
| N8 | 形式门禁（VerificationForm/SkillGeneralization/DevPlanDocRef）+ 轮志 + 主线块刷新 + 本地 commit | N4,N5,N6,N7 | `docs/reports/**` | 本地构建 |

## 可并行面

- **N1 ∥ N2 ∥ N0**：三者互不依赖、写不同文件、且**都不写产品代码**（只读冻结快照）⇒ 可并行；本轮不分派子 agent（均为单一脚本调用，分发开销大于收益）。
- **N6 与 N3 互斥（硬约束）**：N6 会改仓内工具并跑 dotnet 测试（`tcmalloc`/编译服务会吃内存与 CPU）⇒ **严禁与真机臂并发**（污染内存读数与起手闸）。故 N6 排在 N3 之后。
- **N4/N5/N7 串行**（同一读数面，后处理）。

## 收尾重启判据（不重跑全轮）

- 起手闸（内存裕量 / leak-selfcheck）未过 ⇒ **只重起 N3**（N1/N2 只读产物不动）。
- `bin-sha-check.json` 报 `bin_sha_stable=false` ⇒ 整轮 VOID（臂身份不成立），**重跑 N3**。
- N4 判据器自身缺陷（`bad_dumps` / 缺列 / 键缺失）⇒ **只重跑后处理**（`--D` 重读已落盘 `readings.jsonl`），**不重测**。
- N5 前置器 rc≠0 ⇒ 不改判据、只按判据标「参考（未可验收）」；若 rc=3（输入缺失）⇒ 修前置器输入面后**只重跑 N5**。
- N6 selftest 任一负控未红 ⇒ 判定器无牙 ⇒ **判 N6 未达成**（不改判据凑绿）。

## 判据面（口径来源）

口径文本取自 `docs/external-reference-harness.md` §12 + 本轮 `prereg-r587.json`（**先写后跑闸**，runner 第 0 步机检）。
跨轮一律**并列不相减**；配对差只在同一轮内算。
