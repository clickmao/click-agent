# R602 证据面 · 同件扩窗轮（第九窗集 w187..w189）

- 级别：**L3 真机运行**（真二进制 + 真外部真值 codex + 机械判分；**未可验收**：铁律 11 rc=1）
- 被测件：`$HOME/.agentframework/artifacts/pub_r600/agenthost` sha12 `8c3ade04d542`（与 R600 同件）
- 冻结题集：`eval/rover/r602/taskset-r602.json` sha256 `e0c667c2a313c04b2d87ac06fcba9f50166a4a0be5d5162cabdbf520d9d3927a`（与 r600 逐字节同：`cmp` 零差异）
- 复现命令：`bash eval/rover/r602/run_r602.sh`（含起手闸 A1/A2 + 判别力成对控制 + leak-selfcheck + 铁律 11 前置器）
- 判决：`python3 eval/rover/r602/judge_r602.py --D $HOME/.agentframework/harness/runs/r602 --pd eval/rover/r602`
- 只读并轮：`python3 eval/rover/r602/checks_r602.py --D <run根>`（L2/L3/Q1；负控 `--negctl` 有牙）· `python3 eval/rover/r602/l1_axis_probe_r602.py`（L1 可构造性）· `python3 eval/rover/r593/landing_predicate_r593.py --rounds r600,r602`（V_int）
- 轮志：`eval/rover/r602/report-r602.md` · KPI 行：`eval/capability/kpi.jsonl`（round=R602）
