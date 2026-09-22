# R638 / EXP1-Q43 — DAG 先行 (用户令 2026-09-19)

**意图**: 推进计划面「最前未完成项」= backlog L3 `exp1 本地索引/代码引用图`(进行中, 零产品代码)，
本轮 = 该计划项 `AN.11` 下轮候选的**并轮**推进，全部读数须真机背书；**零产品源码改动**。

## 节点

| # | 节点 | 依赖 | 并行面 | 判据 |
|---|---|---|---|---|
| N0 | 起手闸 `roundcheck preflight --round R638` | — | 否 | rc=0 (已 PASS: 8/8 项, MemAvailable=2806MB) |
| N1 | 预注册 `prereg_q43.json` (先声明后测量) | N0 | 否 | M1–M6 落盘 ∧ `written_before_any_measurement=true` |
| N2 | **候选#6(主) 两器入器具面** `verify_replay_archive_q42` / `nc_prestate_q42` (31→33) | N1 | 否(写面) | 新两行 `cmd` rc==expect ∧ `nc_cmd` 非零 (有牙) ∧ 其余 31 行零回归 |
| N3 | 候选#1 序列化形态统一：活通路/一次性件**分类普查** | N1 | 只读 | 活通路件数 == 0 ⇒ 零功能增益 ⇒ 收窄关闭 |
| N4 | 候选#5 尾 LF 写入器缺口：R481 起新增产物件**增量普查** | N1 | 只读 | 新增缺尾 LF == 0 ⇒ 缺口闭合；>0 ⇒ 点名并结转 |
| N5 | 文献小步 (arXiv ≤3 query / 台账追加) | N1 | 只读 | 8 列台账行追加 ∧ `tail`+`wc -l` 复核 |
| N6 | 形式门禁 + `decl_sweep --check` + registry 重钉 | N2,N3,N4 | 否 | `dotnet test` filter Failed=0 ∧ `--check` rc=0 |
| N7 | `status_gen --check` + 本地 commit + 逐文件 stat 回读 | N6 | 否 | CHECK PASS (违规0/漂移0/缺源0) ∧ 回读=本轮清单 |

## 依赖边与并行约束

- 串行主链: N0 → N1 → N2 → N6 → N7。
- N3/N4/N5 与 N2 无依赖边，但**同仓写者只有本侧**且「禁额外开发」⇒ **不开子 agent**，串行执行(只读)。
- N2 写 `instruments.json`(面) ⇒ **面在飞时禁编辑该面会调用的器具**(R-Q38 崩溃面教训)：面跑与器具编辑严格串行。

## 收尾重启判据 (按 DAG 判该重启哪条边，不重跑全轮)

| 红项 | 重启边 |
|---|---|
| 新两行 `cmd`/`nc` 不达预期 | N2 (器具侧) —— 只重跑 scoped 面, 不动 N3/N4 |
| 其余 31 行出现新红 | N2 的**基线对比**边 (先查是否本侧写入所致, 非重跑全轮) |
| 形式门禁红 | N2 的 registry 重钉边 (`decl_sweep --apply` + 重跑 filter) |
| `status_gen --check` 非 PASS | N7 的派生文件重生成边 |
