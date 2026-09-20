# R597 DAG（用户 2026-09-19 DAG 先行令）

- 节点: N1 器具派生（derive_r597，串行）→ N2 预注册 prereg-r597（串行，先写后跑闸）→ N3 真机臂轮 w175..w177（launch_r597，串行独占）→ N4 后处理三件（kpi/pool/verdict，串行）→ N5 只读并轮 ②percase ③behav ④landing ⑤gate-margin（互相独立，可并行，仅读 N3 产物）
- 依赖边: N1→N2→N3→N4；N5 依赖 N4 的派生面（percase 读 snapshots + precond；behav 读 snapshots；landing 读快照+定因器）
- 并行面: N5 内部 ②③④ 并行（本 tick 顺序执行：共享 CPU 闸，避免污染内存读数）；⑤ 在起手时行使（N3 前）
- 收尾重启判据: 真机臂轮 N3 全 12 跑次落盘才算完成；中断 ⇒ 只重启 N3 未完成窗（已完成窗快照/判分件在盘复用），后处理 N4/N5 可从落盘件幂等重算（本轮实测: 全部一次完成，无重启）
- 本轮无并行子 agent（同仓写者唯一 = 本会话）
