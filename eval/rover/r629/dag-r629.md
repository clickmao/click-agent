# R629 DAG（起手先行；每节点含完成判据）

**意图**: 主线 = 用真实开发任务与外部真值（codex-cli，同环境·同输入·同模型）对照，对本项目做质量自检
（`iteration-master-plan.md` §0-0 铁律 10）。
本轮 = **器件/判据面修法轮 + `wythoff` 族逐例归因（只读定因）**：R628 遗留候选 ①②④⑤ 并轮。
R628 候选 ③（面 4 达标路径处置裁定）**待用户放行** ⇒ 本轮零 `src/` 改动、零新臂、零远端 LLM。

## 节点

| 节点 | 内容 | 依赖 | 完成判据（可机检） |
|---|---|---|---|
| N0 | 侦察: §7 最新块 / RF0005 协议 / R628 verdict+precond / 当前件 sha / 内存 / 磁盘 / 在飞写者 | — | `roundcheck preflight --round R629` rc=0（P1–P8 PASS） |
| N1 | **先写后跑**: 本 DAG + `prereg-r629.json` | N0 | `py_compile` rc=0 ∧ `prereg.written_before_run == true` ∧ 时间戳早于所有判据落盘 |
| N2 | **候选② `wythoff` 族逐例归因**（只读，零产品/零夹具改动）: 独立 oracle 复现冻结期望 → 独立重放 R628 九跑次产物 → 逐例四分 → **最小修复实验 + null 重写负控**（行号级机制钉死） | N1 | `attribution-r629.json`: `oracle_vs_fixture` 15/15 ∧ `replay_vs_harness` 12/12 臂窗失败集逐字相同 ∧ `minrepair.fixed==目标2例 ∧ regressed==0` ∧ `nullrewrite.fails==baseline.fails` |
| N3 | **候选① 器具面修法**（零产品改动）: 判决面 == 预注册主判据面 —— 主判据键**落盘**进 verdict 顶层 + `verdict_source` 字段机检 + 铁律 11 指针**随 `--out` 同源派生** | N1 | `judge_r629.py` 对正控（现盘 R628 数据）与负控（注入 `C7` 键副本）**成对**判定：正控 ⇒ 器具缺陷 rc=2（源数据缺主判据键）；负控 ⇒ `verdict_source=="C7"` ∧ rc 由主判据出 |
| N4 | **候选④ 负控指标形态转正**: 禁用 `agreement(臂, 产品)`，改**臂间差异量**（`symdiff_hits` / 命中数差），引 `baselines#rerank-oracle-form` | N1 | `negform-r629.json`: POS 差异 **0** ∧ N1/N2/N3 差异 **>0 且单调**（59<68<75<88）∧ 旧形态无牙读数**并列保留**（N2 agreement 0.8333 ≫ 0.25，不翻案） |
| N5 | **候选⑤ 归并/截断次序轴关闭**（已证伪，禁再开同类候选）+ R628 判决叙述错误登记 | N2 | 关闭条目落盘 + 该轴在 §7 后续候选列表中**不再出现** |
| N6 | 文献小步（出口前置探针 + ≤3 式 + 台账 `io.open(...,'a')` 追加） | N1 | 台账行数 ++ ∧ `tail`/`wc -l` 复核 |
| N7 | 收口: 形式门禁 + `status_gen.py --check` PASS + registry 行 + kpi 行（带 `baselines`）+ §7 块 + 本地 commit（推送暂停令在效） | N2–N6 | 形式门禁 Failed 0；`status_gen --check` PASS；`git log -1` 含本轮；**无 push**；`git add` 逐名列名 |

**可并行面**: N6（curl 只读）与 N2–N4（纯本地、不写 `src/`）并行；本轮**无真机臂、无构建** ⇒ 不撞共享编译节点。

**收尾重启判据（按 DAG 判「该重启哪条边」）**:
- N2 `oracle_vs_fixture != 15/15` ⇒ **夹具缺陷分支成立** ⇒ N2 结论作废（只重跑 N2，不重跑 N3–N6）。
- N2 `minrepair.regressed > 0` ⇒ 归因不成立（改的不是该行）⇒ 只重启 N2 的机制段。
- N3 负控仍判「主判据键缺失」⇒ 机检器无牙 ⇒ **只重启 N3**（修机检器），不降标准。
- N7 形式门禁红且红项仅声明类字段（`instrument_sha12`/`version`）⇒ 声明滞后 ⇒ **只重启 N7 的重钉段**。
