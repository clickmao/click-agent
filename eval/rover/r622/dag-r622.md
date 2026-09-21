# R622 DAG（起手先出图；节点 / 依赖边 / 并行面 / 收尾重启判据）

意图：对 R621 冻结产物做**只读**定因 —— 「wythoff 族承重缺口」的失败落在哪一层（逐例）∧ 哪一机制（行为式谓词）。
零产品源码改动 / 零新臂 / 零远端 / 零新增夹具语义。

| 节点 | 内容 | 依赖 | 产出（可机检） |
|---|---|---|---|
| N1 | 起手闸：`roundcheck preflight --round R622 --min-avail-mb 119 --min-disk-gb 1 --need-key AGENTFRAMEWORK_KEYS_DEEPSEEK`（先清 VBCSCompiler/MSBuild/pyright） | — | preflight rc=0 |
| N2 | 主线提醒（读 §7 状态 + improvements + 最新 plan） | N1 | 报告结论行 |
| N3 | 选靶：承 R621 轮志候选 **C1**（wythoff 族决策语义逐例归因） | N2 | prereg 的 hypothesis_source |
| N4 | 独立 oracle + **正控**（复现冻结期望字节） | N3 | J0（15/15） |
| N5 | 逐例四分复算（39 跑次 × 15 例） | N4 | `out/percase-r622.json` |
| N6 | 机制归因（行为式谓词，问产物自身接口） | N5 | `out/mech-r622.json` |
| N9 | **预注册落盘（必须在 N5/N6 正式跑次之前）** | N3 | `prereg-r622.json`（含 v1 J1 判据） |
| N7 | 只读副读数：夹具普查 / 成本分解 / 崩溃取证 | N5 | `out/fixture-census|cost-decomp|crash-stderr-r622.json` |
| N8 | 文献小步（arXiv ≤3 式 + 摘要取件；只作机制假设） | N2 | `docs/research/lit-review-ledger.md` §19 |
| N10 | 收口：`closeout_r622.py`（J0–J5 机械比对）+ `status_gen --check` + `roundcheck audit --round R622` | N6, N7, N9 | `verdict-r622.json`、status_gen PASS |
| N11 | 本地 commit（**禁 push**：推送暂停令在效） | N10 | HEAD 回读 |

**并行面**：N7 与 N8 只读、且不写同仓同件 ⇒ 可与 N5/N6 并行；N5/N6 串行（同写 `out/`）。
**禁并行**：任何写同仓的节点（N10/N11）在飞时不得另起写者。
**收尾重启判据**：① N4 红 ⇒ 只重启 N4（修 oracle），不重跑全轮；② N5/N6 与 N9 判据不符 ⇒ 只重跑不符的那条边并**保留原样失败读数**（禁翻案）；③ N10 报 rc=2（器具层）⇒ 修器具后**换命名空间**重跑复算，首跑读数不覆盖。
