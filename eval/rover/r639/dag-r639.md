# R639 · DAG（起手先行；节点 / 依赖边 / 可并行面 / 收尾重启判据）

意图：**主线对照轮**（新窗集 w237..w239：codex 外部真值 ×1/窗 + 产品默认档 ×3/窗）＋ **判据面新增并读**
（`F_lift_min` 最低族栏，承 R637 候选②）＋ 文献小步；零产品源码改动。

| 节点 | 内容 | 依赖 | 出口证据 |
|---|---|---|---|
| N0 | 起手闸：env/keys ⇒ 清 pyright/bhs 残留 ⇒ `roundcheck preflight --round R639` | — | `preflight_r639.sh` 读数（首跑 rc=1 = 内存闸 2691<2900 ⇒ **清残留后** MemAvailable 2833MB ⇒ 复测 PASS） |
| N1 | 主线提醒（读 master plan §7 + improvements + plans） | — | 报告结论行（1 行） |
| N2 | 文献小步（arXiv ≤3 query / 全文 ≤2 / 间隔 ≥4s） | — | 台账 `docs/research/lit-review-ledger.md` 追加段 |
| N3 | 器具派生（driver/judge/prereg/DAG）＋ 影子自检 | — | `derive_r639.py` / `derive_judge_r639.py` / `gen_prereg_r639.py` 输出 + `selftest-r639.json`（`all_ok=True`） |
| N4 | 真机臂：12 跑次（3 窗 × (1 codex + 3 产品)）＋ 逐窗判据 | N0,N3 | `$HOME/.agentframework/harness/runs/r639/**` + `evidence/windows/w23{7,8,9}/report.json` |
| N5 | 判决：`judge_r639.py`（Q1 + B + **F** + 成本 + 铁律 11 前置器） | N4 | `verdict-r639.json` / `kpi-table-r639.json` |
| N6 | 收口：证据文档 + registry 行 + kpi 行 + `status_gen --check` + 形式门禁 + 本地 commit | N5 | `docs/evidence/RF0001/R639-*.md`、`status_gen --check` PASS、门禁 14/14 |

**可并行面**：`N1 ∥ N2 ∥ N3`（三者互不写同一文件；N2 只 append 台账）；`N0 → N4` 为硬序（内存闸必须先过）。
**同仓在飞写者**：起手闸 P5 `no_sibling_load` = 无在飞执行体 ∧ `pgrep` 无 dotnet/codex 重进程 ⇒ 允许 N4 真机写入。
**收尾重启判据**：① 若 N4 中某臂 VOID（`cli_rc=124`/同质超时）⇒ 只重启该跑次（不重跑全轮）；
② 若 N5 判据层红（器具缺陷 rc=2）⇒ 只重启 N5（零重测，读冻结落盘）；
③ 若 N0 内存闸在运行器自身复检时被拒（擦边 PASS）⇒ **不起臂**，本轮转「判据面只读轮」并如实登记顺延原因（禁调闸值）。
