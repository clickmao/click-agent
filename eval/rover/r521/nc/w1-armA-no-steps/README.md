# R521 作废窗 w1 (负控归档, 非验收窗) · 证据留痕

**这是 R521 的第一窗** (`run-0917-153525`, 2026-09-17 15:35), **因器具缺陷作废**, 不属验收面; 证据整体保留于此, 未做任何删改。

## 1 为什么作废
臂 A 由 `proj_run_side.py --side agent` 拉起时**未传 `--max-steps`** (默认 0) ⇒ 工具面关闭 ⇒ CLI 退回纯对话: 上游调用 1 次、墙钟 5.38 s、代码只出现在回复文本里, 工作区 `$D/A-r1/g1/work/` **零字节**。同一窗口的臂 C (codex-cli) 与臂 O (编排器 5×8) 照常产出。

## 2 w1 仍有效的读数 (仅作机制/方向参考, 不作验收依据)
| 臂 | 用例 | 上游调用 | total tok | 备注 |
|---|---|---|---|---|
| A-r1 | **0/58** | 1 | 7,674 prompt + 1,288 completion | **工具面关闭负控**: 零产物 ⇒ 0/58 |
| C-r1 | **58/58** | 7 | — (见 report.json) | codex 外部真值 |
| O-r1 | 9/58 | — | — | 同器具同题面, w2 同臂为 31/58 ⇒ **摆动 22 用例** |

## 3 该窗暴露的器具第二缺陷 (假绿)
`freeze_r521.py` 对**空产物树静默跳过** (`os.walk` 零迭代 ⇒ 目标目录不落盘), 而 `exec_precondition.py` 只遍历**已存在**的快照目录 ⇒ 零产物臂既不判分也不阻断 ⇒ 该窗前置器一度报 **rc=0 (假绿)**。
**修复**: `emit()` 先 `makedirs(dst)` ⇒ 空臂也落盘 (`snapshot_empty: true`); **负控面板** `eval/rover/r521nc/` (空 `agentA` 树 + 自报 `all_pass=true`) ⇒ **rc=1** · `BLOCKED w1/agentA/g1 0/58` · `SELF_REPORT_AGREES=False`。

## 4 归档件
`artifacts.json` · `report.json` · `grade-{A,C,O}-g1.json` · `precond-r521nc.txt` (留痕见 `../../evidence/precond-r521nc.txt`)。
