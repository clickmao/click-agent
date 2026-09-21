# R617 DAG（起手先出，再执行）

**意图**：把 R615 的「有声明跑次 2/9」缺口归因到**尾块豁免句**这一条措辞自由度上，并用同一被测件族的单变量真机对照给出可证伪读数。

## 节点 / 依赖边 / 可并行面

| 节点 | 动作 | 依赖 | 并行面 | 完成判据 |
|---|---|---|---|---|
| N0 | `roundcheck preflight --round R617` | — | 只读 | rc=0（key/内存/磁盘/轮号/无在飞执行体） |
| N1 | 主线提醒 1 行（读 §7 + RF0004 + 上轮 verdict） | N0 | 只读，可与 N2 并行 | 1 行 |
| N2 | 代码：尾块豁免句 → 必声明句（`tools/r1gen/r1prompt.py`）+ R615 对照载体 + 生成器三档轴（`gen_csharp.py` → `StructuredPrompt.cs`） | N0 | 与 N3 并行（不同文件） | `gen --check` drift 0；单测 3 条新件全绿 |
| N3 | 文献小步（arXiv ≤3 query） | N0 | 与 N2/N6 并行 | 台账 §16 追加（8 列） |
| N4 | 前缀不变量 + 基准重钉（`prefix_r617.py` → `baselines.json` 三条） | N2 | 串行 | `prefix_r617.py` rc=0 ∧ `status_gen --check` PASS |
| N5 | 预注册 + 臂表 + 判据器/驱动器派生（`prereg-r617.json` / `judge_r617.py` / `run_r617.sh`） | N4 | 串行 | 先写后跑闸（驱动器第 0 步机检 prereg） |
| N6 | AOT 发布（`aot_r617.sh`）| N2 | 与 N3 并行 | PUBLISH_RC=0 ∧ IL=0 ∧ 冒烟出回复 |
| N7 | 真机臂（w205..w207：T×3 / C×3 / codex×1 = 21 跑次） | N5,N6 | 串行（单 llama-server/单端口） | 每窗判分落盘 + `bin_sha_stable=true` |
| N8 | 判决（`judge_r617.py`）+ 铁律 11 前置器 + 判据器负控（R615 旧跑次喂 R617 判据器 ⇒ J0 必红） | N7 | 串行 | verdict 落盘 ∧ 负控两侧样例齐 |
| N9 | 收口：报告 / registry 行 / kpi 行（带 baselines）/ §7 块 / 形式门禁 / commit | N8 | 串行 | 形式门禁 14/14 ∧ `status_gen --check` PASS |

## 起手闸（N0 现读数）

`P1 key PASS · P2 weights PASS · P3 MemAvailable 2910MB ≥ 70MB · P4 disk 5GB ≥ 1GB · P5 无在飞执行体 · P6 轮号未占用 · P7 R617 空闲 · P8 PUSH_PAUSED=yes` ⇒ **rc=0**。

## 收尾重启判据（按 DAG 判「该重启哪条边」）

- 起臂前内存闸红 ⇒ 只重启 **N7 前置（清场→重取 ceiling）**，不重跑 N2–N6。
- 臂跑完但判分/汇总缺件 ⇒ 只重启 **N8（后处理）**，不重测 N7（R587 定因：后处理幂等重算）。
- J0 判红（两档 sha 未分离/不符 pin）⇒ 停机修 **N2/N5**（臂无效，读数作废），不得改写判据。
- 真值自败窗剔除后有效窗 < 2 ⇒ rc=3 停链先造窗集（N7 换窗），禁调阈值。

## 唯一变量与臂表

- 唯一变量：`AGENTFRAMEWORK_R1_ACTION_PROMPT`（T = unset 新尾块 / C = `r615` R615 现盘尾块逐位）。
- 臂：T×9 / C×9 / C1(codex 真值)×3；窗集 w205..w207（与历史不相交）；同名同题集（sha `e0c667c2…`）。
- 器具（非被测变量）：到达面遥测 `action_candidates_present` 两臂同开；轴解析为纯函数（单测钉住）。
