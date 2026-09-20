# R596 DAG（起手先行；每节点含完成判据）

**意图**: 主线质量自检 = 同环境·同输入·同模型下，与外部真值 codex 对照，对本项目做质量自检（`iteration-master-plan.md` §0-0 铁律 10）；
本轮 = 判据 v3 **第四窗集**行使 + R596 候选 ②③④⑤ 并轮；候选①（产品侧修复）待放行。

| 节点 | 内容 | 依赖 | 完成判据（可机检） |
|---|---|---|---|
| N0 | 侦察: §7 最新块 / 上轮预注册 / 驱动器 / 环境（配额 key、内存、磁盘、残留进程） | — | 六项读数落盘；无残留重负载进程 |
| N1 | **先写后跑**: `prereg-r596.json` + 本 DAG + 派生件（`derive_r596.py` 22 项断言全过 + `bash -n`/`py_compile` rc=0） | N0 | 预注册机检通过（runner 第 0 步断言）；派生件语法门 rc=0 |
| N2 | 起手闸条款（候选⑤）: `MARGIN := clamp(133, 60, CEIL−2650−60)`；3 样本 CEIL=min ∧ 极差 ≤50MB；连续 2 次 PASS；判别力成对控制 | N1 | `gate-margin-r596.json` + A1/A2 PASS + 成对控制 rc |
| N3 | **真机臂轮**（主线）: 3 窗 `w172..w174` × 每窗 (codex 真值 ×1 + 产品默认档 ×3) = 12 跑次/58 例；同件（bin `4b70fd7cdb39`）同题集 | N2 | `windows.jsonl` 12 跑次 × `cases.txt` 58 例齐全；`bin-sha-check.json` stable=true |
| N4 | 判据面: v3 第四窗集（`pool_taskface_r596.py`）+ 用例级参照（`kpi_r596.py`）+ 成本三列 + 步数列 | N3 | `taskface-pool-r596.json` C0 pass ∧ C7 有牙 |
| N5 | 候选② 逐例归因（只读, 零子进程）: A/A2/B/C/D 桶 + POS/NEG/非平凡控制 | N3（数据面）/ N4 | `percase-attrib-r596.json` 控制三件齐备 |
| N6 | 候选③ 行为面契约普查（只读, 有界子进程）: 6 轮窗集 × 每跑次 4 族入口实跑 | N3 | `behav-census-r596.json` POS 翻面 ∧ NEG 不翻 ∧ 无孤儿 |
| N7 | 候选④ `V_int` 第三窗集分布（r593 同件定因器 `--rounds r596`）+ 零回归逐位复现 | N3 | `landing-predicate-r596.json` 零回归 true 或 rc=2 单列 |
| N8 | 铁律 11 前置器 `--round r596`（可验收前置；rc≠0 ⇒ 成本读数标「参考（未可验收）」） | N3 | `precond-r596.json` rc ∈ {0,1,2,3} 落盘且与逐例读数自洽 |
| N9 | 收口: 形式门禁 14/14 + 轮志 + 台账 `kpi.jsonl` + §7 块/快照 + improvements + 本地 commit（推送暂停令在效，禁 push） | N4–N8 | 形式门禁 Failed 0 / Passed ≥14；`git log -1` 含本轮；**无 push** |

**可并行面**: N5/N6/N7 只读且互不写同仓文件 ⇒ 可并行；但 N3 在飞时**禁任何重算**（污染内存读数）⇒ N5–N7 一律排在 N3 之后串行起（本 tick 单进程执行）。

**收尾重启判据（按 DAG 判「该重启哪条边」）**:
- `bin-sha-check.json` stable=false ⇒ 臂身份不成立 ⇒ **N3 整条边重跑**（换窗集命名空间，旧读数单列不翻案）。
- 器具缺陷（判分器/池化器 Traceback 或 C0 不 pass）⇒ **只重启 N4 后处理边**（从在盘快照重算），**不重测**（承 R595 处置）。
- 起手闸 fail-closed（顶棚装不下 `2650+MARGIN`）⇒ **只重启 N2**（清本会话工具子进程后重采样），N1 不重做。
- 铁律 11 rc≠0 ⇒ **不重启任何边**；按纪律把成本读数降级标注（可验收前置未过）。
