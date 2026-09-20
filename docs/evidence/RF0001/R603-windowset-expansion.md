# R603 证据面 · 同件扩窗轮（第十窗集 w190..w192）

- 级别：**L3 真机运行**（真二进制 + 真外部真值 codex + 机械判分；**未可验收**：铁律 11 rc=1）
- 被测件：`$HOME/.agentframework/artifacts/pub_r600/agenthost` sha12 `8c3ade04d542`（与 R600/R602 同件）
- 冻结题集：`eval/rover/r603/taskset-r603.json` sha256 `e0c667c2a313c04b2d87ac06fcba9f50166a4a0be5d5162cabdbf520d9d3927a`（与 r602 逐字节同：`cmp` 零差异）
- 复现命令：`bash eval/rover/r603/run_r603.sh`（含起手闸 A1/A2 + 判别力成对控制 + leak-selfcheck + 铁律 11 前置器）
- 判决：`python3 eval/rover/r603/judge_r603.py --D $HOME/.agentframework/harness/runs/r603 --pd eval/rover/r603`
- 只读并轮：`python3 eval/rover/r603/checks_r603.py --D <run根>`（L2/L3/Q1；负控 `--negctl` 有牙）· `python3 eval/rover/r603/l1_axis_probe_r603.py`（L1 可构造性）· `python3 eval/rover/r593/landing_predicate_r593.py --rounds r602,r603`（V_int）
- 轮志：`eval/rover/r603/report-r603.md` · KPI 行：`eval/capability/kpi.jsonl`（round=R603）
- **N4⑤ 真值掉线面（新器具，只读）**: `python3 eval/rover/r603/truthdrop_r603.py --rounds r602,r603` ⇒ `eval/rover/r603/truthdrop-r603.json`（r602 `{S1 884, S2 148, S3 5, S4 7}` / r603 `{S1 901, S2 119, S3 15, S4 9}`；S3 归属 15/15 `L_mixed`；POS 控制 `rows=6=expect_rows` ⇒ 有牙；rc=0）
- **归一化读数（主/负控分离）**: 主 `eval/rover/r603/checks-r603.json`（L2 pass=True，`prefix_sha256` 唯一）· 负控 `eval/rover/r603/checks-r603-negctl.json`（注入前缀漂移 ⇒ `l2_violated=true, negctl_teeth=true`）——`--negctl` 默认写主 `--out` 的坑已用显式 `--out` 分离，**两文件并列入档**
- 铁律 11 前置器：`eval/rover/r603/precond-r603.json`（`executable_and_correct=false` ⇒ rc=1；blocked 11 / 验收面 blocked_scoped 32）
