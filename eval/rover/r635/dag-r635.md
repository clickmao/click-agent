# R635 DAG（意图 → 子任务：节点 / 依赖边 / 可并行面 / 收尾重启判据）

意图：把 R634 的两条承重候选落成**真机证据** —— ①预注册同批携带 `evidence_scope` + `unreliable_policy`
（前置器 `SCOPE_SOURCE!=None ∧ POLICY_ACTIVE=True`）②新窗集 w231..w233 的主线对照（产品默认档 ×3/窗 vs codex 真值 ×1/窗）。

| 节点 | 内容 | 依赖边 | 并行面 |
|---|---|---|---|
| N0 | 起手闸 preflight（mem/disk/key/轮号空闲/无兄弟在飞）+ ROUND_CLAIM | — | 只读 |
| N1 | 主线提醒 1 行（§7 + RF0004 + R634 verdict） | — | 只读 |
| N2 | 器件派生（runner/judge/prereg/题集+cases 逐字节复制；prereg 带两把键） | N0 | 只读（禁写同仓 src/） |
| N3 | 文献小步（arXiv ≤3 query；台账追加） | — | **可与 N4 并行**（网络面，低 CPU） |
| N4 | 真机跑 12 跑次 = 3 窗 ×（P×3 + codex×1） | N2 | 串行（同仓、独占 adapter/端口） |
| N5 | 判决 judge_r635 + 铁律 11 前置器（含 S 面机检） | N4 | 只读 |
| N6 | 收口（registry/kpi/§7/improvements/evidence/status_gen/形式门禁/提交） | N5 | 只读+单次写 |

**可并行面**：仅 N3（网络）与 N4（真机）可叠；N4 期间**禁 any 写 src/ 或 build**（内存闸 + 被测件身份）。
**收尾重启判据**：① N4 若因内存闸 fail-closed ⇒ **只重启 N4 这条边**（不改任何阈值；闸值按 R634 实测 swing 75MB 派生）；
② N2 派生件若 sha 漂移（题集/aux）⇒ 只重启 N2→N4；③ N5 若 `SCOPE_SOURCE=None` ⇒ 判 F5 FAIL、**不重启**（禁事后 `--scope` 翻案），如实入档。
