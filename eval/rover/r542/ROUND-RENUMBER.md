# 轮号重编说明: 执行标签 `R541` ⇒ 登记轮号 `R542`

- **事实**: 本轮器具与 10 臂在 2026-09-18 05:50–05:57 以 `R541` 为内部标签真跑（目录名、prereg 轮号、session id、日志行、快照 `owner` 标记均为 `R541`）。
- **碰撞检出**: 05:37 的**文档轮** `dba59d7`（`docs/evidence/RF0001/EVIDENCE.md` E11/E13）已占用轮号 `R541`，但其**提交标题不含轮号**（"RF0001: 版本线起点 …"）⇒ 起手 `git log --format='%h %ad %s'` 未能检出，`pgrep` 闸亦无非空（该轮已收口）。
- **处置**: 按 `max+1` 原则，本轮**登记轮号 = R542**；仓内**历史标签一律不改写**（改写日志 = 伪造证据），故：
  - `run-w1/**`、`logs/**`、`evidence/**`、`snapshots/**` 内残留 `R541` / `r541-*` / `.owner-r541` 标记 = **真实运行史**，保留原样；
  - 顶层的**器具件**（`prereg-r542.json` / `taskset-r542.json` / `input-pins-r542.json` / `run_r542.sh` / `analyze_r542.py`）已重编为 `r542`（与 `exec_precondition --round r542` 的自动发现面一致）；
  - 旧 `eval/rover/r507pre/precondition-r541.json`（重编前一次的产物，其内部路径引用已失效）**已删除**，改为 `precondition-r542.json`。
- **机检**: `python3 eval/rover/r507pre/exec_precondition.py --round r542` ⇒ rc=1（阻塞 = 剂量 3 三臂），与重编前同判。
