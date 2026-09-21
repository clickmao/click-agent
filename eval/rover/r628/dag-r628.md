# R628 DAG（起手先行；每节点含完成判据）

**意图**: 主线 = 用真实开发任务与外部真值（codex-cli，同环境·同输入·同模型）对照，对本项目做质量自检（`iteration-master-plan.md` §0-0 铁律 10）。
本轮 = **判据 v3 第五窗集行使（真机臂轮 w220..w222）+ 当前件（pub_r619，sha12 `a184d7317b6e`）** + 只读并轮（R627 候选 ②/⑤/⑥ 的零产品改动面）。
R627 候选 ①（面 4 达标路径处置裁定）**待用户放行** ⇒ 本轮零 `src/` 改动。

| 节点 | 内容 | 依赖 | 完成判据（可机检） |
|---|---|---|---|
| N0 | 侦察: §7 最新块 / RF0005 协议 / 上轮预注册 / 当前件 sha / 端口 / 内存 / 磁盘 / 在飞写者 | — | 六项读数落盘；`pgrep` 无重负载在飞执行体；端口 49681 空闲 |
| N1 | **先写后跑**: `prereg-r628.json` + 本 DAG + 派生件（`run_r628.sh`/`kpi_r628.py`/`pool_taskface_r628.py`） | N0 | `bash -n` rc=0 ∧ `py_compile` rc=0 ∧ runner 第 0 步预注册机检通过 |
| N2 | 起手闸条款: `MARGIN := clamp(224, 60, CEIL−2650−60)`（224 = r621 同态在飞窗实测振幅）；3 样本 CEIL=min ∧ 极差 ≤50MB；连续 2 次 PASS；判别力成对控制 | N1 | `gate-margin-r628.json` + A1/A2 PASS + 成对控制 rc 落盘 |
| N3 | **真机臂轮（主线）**: 3 窗 `w220..w222` × 每窗 (codex 真值 ×1 + 产品默认档 ×3) = 12 跑次 / 58 例；同件（bin sha12 `a184d7317b6e`）同题集（sha `e0c667c2a313c04b`） | N2 | `windows.jsonl` 12 跑次 × `cases.txt` 58 例齐全；`bin-sha-check.json` stable=true |
| N4 | 判据面: 判据 v3 第五窗集（`pool_taskface_r628.py`，逻辑源 = r589 import）+ 用例级参照（`kpi_r628.py`）+ 成本三列（调用/新算 prompt/completion）+ 命中率双口径 + 步数列 | N3 | `taskface-pool-r628.json` C0 pass ∧ C7 有牙 ∧ `evidence/windows/*/report.json` 落盘 |
| N5 | 铁律 11 前置器 `--round r628`（可验收前置；project 布局独立物化 + 逐用例实跑） | N3 | `precond-r628.json` rc ∈ {0,1,2,3} 落盘，与逐例读数自洽 |
| N6 | 文献小步（arXiv 出口前置探针 + ≤3 式 + 台账追加）—— 与 N3 **可并行**（只读、零仓写、零重算） | N1 | 台账 `docs/research/lit-review-ledger.md` 追加 + `tail`/`wc -l` 复核 |
| N7 | 收口: 形式门禁 14/14 + `status_gen.py --check` PASS + kpi 行 + registry 行 + §7 块 + 本地 commit（推送暂停令在效） | N4–N6 | 形式门禁 Failed 0 / Passed ≥14；`status_gen --check` PASS；`git log -1` 含本轮；**无 push** |

**可并行面**: N6 与 N3 并行（文献面 = curl 只读，不写同仓、不做重算 ⇒ 不污染内存读数）；其余节点串行（N3 在飞时禁任何重算/构建）。

**收尾重启判据（按 DAG 判「该重启哪条边」）**:
- `bin-sha-check.json` stable=false ⇒ 臂身份不成立 ⇒ **N3 整条边重跑**（换窗集命名空间，旧读数单列不翻案）。
- 器具缺陷（判分器/池化器 Traceback 或 C0 不 pass）⇒ **只重启 N4**（从在盘快照重算），**不重测**。
- 起手闸 fail-closed（顶棚装不下 `2650+MARGIN`）⇒ **只重启 N2**（清本会话工具子进程后重采样），N1 不重做。
- 铁律 11 rc≠0 ⇒ **不重启任何边**；按纪律把质量/成本读数降级标注「参考（未可验收）」。
