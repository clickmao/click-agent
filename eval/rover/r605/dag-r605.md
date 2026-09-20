# R605 DAG（起手先出；用户令 2026-09-19「DAG 先行令」）

意图：主线同件扩窗轮（第十一窗集 w193..w195）+ R604 三项器具面收口首次在新窗集行使；
      **零产品源码改动 / 零新增夹具语义 / 零新增开关**；外部真值 = codex 同窗同题面。

## 节点 / 依赖边 / 可并行面

| # | 节点 | 依赖 | 并行面 | 产出 |
|---|---|---|---|---|
| N0 | 前置勘察（在飞写者 / ROUND_CLAIM / key / 端口 / 内存） | — | 只读，可与 N1 并行 | `/tmp/recon*.txt` |
| N1 | 预注册 `prereg-r605.json`（先写后跑闸）+ DAG | N0 | 与 N2 并行 | `prereg-r605.json` / `dag-r605.md` |
| N2 | 派生件：`run_r605.sh`（逐条声明的差异）· `judge_r605.py`（import kpi_r599 helpers + r604 J3v2 公式模块） | N0 | 与 N1 并行 | 驱动器 / 判据器 |
| N3 | 起手闸 A1/A2（条款 REQ=2650+MARGIN，MARGIN 源 = r603 同态在飞窗 swing 285MB）+ 判别力成对控制 + leak-selfcheck | N1,N2 | 串行 | `gate-margin-r605.json` / `gate-disc-pair.json` |
| N4 | 真机臂轮：3 窗 × (codex 真值 ×1 + 产品 T ×3 + 产品 C ×3) = 21 跑次 | N3 | **禁并行**（同机内存/端口单变量） | `runs.jsonl` / 快照 / `cases.txt` |
| N5 | 逐窗判分 + KPI 汇总（J1–J5 + J3v2 + W_floor + LD） | N4 | 串行 | `kpi-table-r605.json` / `verdict-r605.json` |
| N6 | 铁律 11 前置器 `exec_precondition.py --round r605` | N4 | 可与 N7 并行（只读） | `precond-r605.json` |
| N7 | 只读并轮：L2/L3/Q1（`checks_r605.py`）· V_int 第六窗集 | N4 | 只读，可并行 | `checks-r605.json` / `vint-*.json` |
| N8 | 形式门禁 14/14（登记表/证据未改 ⇒ 仍必跑） | N5 | 串行 | 测试输出 |
| N9 | 文档回填（轮志 / §7 块 / improvements / `eval/capability/kpi.jsonl`） + 本地 commit | N5,N6,N7,N8 | 串行 | 提交 |

## 收尾重启判据（不重跑全轮）

- 起手闸未过（fail-closed `WINDOW_UNOPENABLE`）⇒ **重开窗口**（清场后重采样），不重跑 N4。
- N4 中途二进制被替换（`bin-sha-check.json` false）⇒ 废该窗集、整轮标 `ARM_INVALID`，不重跑已判窗。
- N5 判据器自捕缺陷 ⇒ **留档首跑不翻案**，只重跑**后处理**（N5/N6/N7），**不重测** N4。
- 缺派生件 ⇒ 按「缺派生件 ≠ 通过」判未完成，只补后处理。

## 候选台账（用户令：全部候选并入本轮）

① 产品侧处置裁定 = 未做（须用户放行，本作业无用户在场）· ② J3 v2 新窗集行使 = 做 ·
③ b1 列口径裁定 = 部分（已并列 v2'，降级本身须裁定 ⇒ 列 R606）· ④ 有效窗下限判据面 = 做 ·
⑤ 低区分度冻结名单 = 做 · ⑥ 起手闸余量重派生 = 做。
