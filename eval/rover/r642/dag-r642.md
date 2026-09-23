# R642 DAG（起手先出；用户令 2026-09-19）

意图 = **器具面收口**：把 R641 下轮候选 ②③④⑤ 并入同一轮推进，⑥ 文献小步并行；
候选 ①（产品侧 5 处行级修复）**待用户放行** ⇒ 本轮零产品源码改动 / 零真机臂 / 零远端。

## 节点 / 依赖边 / 并行面

| # | 节点 | 依赖 | 并行面 | 收尾判据（可机检） |
|---|---|---|---|---|
| N0 | 起手闸 `roundcheck preflight --round R642` | — | 只读 | rc 记录；P3 内存 FAIL 如实入档（本轮无 build/臂 ⇒ 保护对象未触发） |
| N1 | 主线提醒 1 行（§7 尾块 + improvements + 最新计划） | — | 只读，**可与 N2 并行** | 1 行读出 |
| N2 | DAG + 预注册落盘（`prereg-r642.json`） | — | 只读 | `declared_before_any_reading=true` |
| N3 | ④ `roundcheck R4` 活行/None 分支修复 + 两侧样例 + 历史回放 | N2 | 独占（改器具） | 冻结行错 pin 仍红 ∧ live/None 行不再红 ∧ R637–R641 回放仅 R4@R639 翻绿 |
| N4 | ⑤ `capability_cycle_status` 最新块解析（多源取「轮号最大」） | N2 | **可与 N3 并行**（不同文件） | 真仓 `route.source_round=R641`；4 条负控 + 旧 fixture 全绿零回归 |
| N5 | ②③ 器具模板化（帧感知分类 / 行级+联合最小修复 / 分辨率条款）+ nim/sub 同形态只读实验 + 与 R641 wythoff 读数零回归 | N2 | 独占（子进程面） | `out/attrib-r642.json` 在盘；wythoff 面复算与 R641 **逐值一致** |
| N6 | ⑥ 文献小步（arXiv ≤3 query；出口前置探针） | N2 | 只读，**可并行** | 台账追加 8 列；`tail`+`wc -l` 复核 |
| N7 | 证据文档 + registry 行 + kpi 行（带 `baselines`） | N3,N4,N5,N6 | — | 文件在盘；`status_gen --check` PASS |
| N8 | 形式门禁 14 测试 + `decl_sweep --apply` + 器具重钉 | N7 | 独占（dotnet） | `failed=0 ∧ skipped=0`；`decl_sweep --check` OK |
| N9 | 收口 `roundcheck audit --round R642` + commit（本地） | N7,N8 | — | `FAIL=0`；`git show --stat` + 回读关键行 |

## 边与并行面
- 无依赖边：N1 ∥ N2 ∥ N6；N3 ∥ N4（不同文件，互不写）。
- 串行：N2 → N5 → N7 → N8 → N9（N5 重子进程面 vs N8 的 `dotnet test` 写 `obj|bin` ⇒ 必须串行）。

## 收尾重启判据（按 DAG 判「该重启哪条边」）
- N5 在**器具层**红（锚点缺失/期望表两源不符/负控失败/确定性失败）⇒ 只重启 N5 对应模块（带断点续跑缓存）。
- N5 在**输入层**红（cases sha 不符/缺源）⇒ 重启 N3 前置的冻结面校验，记 fail-closed。
- N8 红且非绿字段仅 `version`/`instrument_sha12` ⇒ 只重启 N7（重审刷新声明），N5 读数保留。
- N4 真仓读数与真仓 `route.first` 语义不符（取到历史块）⇒ 只重启 N4 的解析器，不重跑 N3/N5。
- N6 出口不可达 ⇒ 记「顺延」一行，不入 0 采信计数。
