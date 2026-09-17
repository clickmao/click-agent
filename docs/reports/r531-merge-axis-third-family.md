# R531 轮志 —— 合批轴单变量臂 / 第三族外部对照 (窗口 w1)

- **预注册**: `eval/rover/r531/prereg-r531.json`（J1–J5 判据 / P1–P3 预测 / `window_plan.windows = [w1, w2, w3]` × 4 臂 = 声明面 12 格）
- **题集**: 第三族（F1 `games-longtask-v1` / F2 `toolkit-multimodule-v1` / F3 `mathkit-multimodule-v1`），`eval/rover/r531/taskset-r531.json`
- **单变量**: env `AGENTFRAMEWORK_ACTION_MERGE`（off=缺省 ⇒ 与 R528 文本逐字节相同；on ⇒ 追加纪律第 7 条「一次成型 (合批)」）
- **四臂**: `A0-off`（纪律关）· `A1-on`（纪律开）· `A2-merge`（纪律开 + 第 7 条）· `C-codex`（外部真值，同一真实模型）
- **运行**: `eval/rover/r531/run-0917-213234/`（起手闸 1/2 PASS，adapter 48999，AOT = `/tmp/pub_r531/agenthost`）

## 1. w1 读数（`run-0917-213234/logs/kpi-r531.json`）

| 臂 | 调用 | 新算 prompt | 命中率 | completion | 总 token | 用例 | g1 / t1 / m1 |
|---|---|---|---|---|---|---|---|
| A0-off | 80 | 54,688 | 95.62% | 28,517 | 1,276,549 | 116/118 | 56/58 · 30/30 · 30/30 |
| A1-on | 59 | 36,887 | 96.26% | 24,469 | 1,010,604 | 116/118 | 56/58 · 30/30 · 30/30 |
| A2-merge | **52** | **31,534** | 96.58% | 28,385 | **950,671** | **118/118** | **58/58** · 30/30 · 30/30 |
| C-codex | 32 | — | — | — | — | 118/118 | 58/58 · 30/30 · 30/30 |

对比（`contrasts`）：merge_vs_off 调用 **−35.0%** / 新算 −42.3% / completion +0.46%；merge_vs_on 调用 −11.86% / 新算 −14.51% / completion +16.0%；on_vs_off 调用 −26.25%。
空正文（上游未回）三臂皆 0 次。

## 2. 预注册裁决（KPI `criteria`）

| 项 | 内容 | 读数 | 裁决 |
|---|---|---|---|
| P1 | merge 相对 **A1-on** 调用降幅 ≥15% | 11.86% | **证伪** |
| P2 | 三档阈值 30/30/40 | 未达 | 证伪 |
| P3 | 质量不降（用例数不低） | 118/118 vs 116/118 | 成立 |

⇒ 合批轴在**同纪律基线**上收益有限（−11.9%），在**对纪律关**的基线上显著（−35.0%）；但 `P1` 按预注册口径**已证伪**，不得改写口径（判据纪律）。

## 3. 器具（本轮新件 / 沿用件）

| 器具 | 结果 | 负控 |
|---|---|---|
| `oracle_wythoff_r531.py`（**非同源**独立 oracle：手写 P/N 位 DP + 暴力枚举合法着法） | rc=0；15 条 wythoff 用例与冻结夹具**完全一致** | rc=0：NC1 篡改期望 ⇒ 不一致被检出；NC2 非法着法 `WIN 1 2` ⇒ 判 `illegal_move` |
| `mount_check_r531.py` v2（实发 prompt 取证） | rc=0，`MOUNT_OK=true` | rc=0：NC1 A1/A2 角色对调 ⇒ 判红；NC2 同臂自比 ⇒ 判红 |
| `eval/rover/r507pre/exec_precondition.py --round r531`（铁律 11） | **rc=1**（未可验收） | — |
| `eval/rover/r507pre/prereg_scope_gate.py` v2（读 `window_plan.windows[]`） | PASS | — |

挂载证明（`evidence/mount-r531-w1.json`）：`A0-off` 9,434 字（无纪律块）→ `A1-on` 9,968 字 → `A2-merge` 10,100 字；差量 **132 字 = `ActionLoopDiscipline.MergeText` 全文**（sha12 `9be41f32e862` 两列相同），前缀逐字节不变（M1/M4 PASS）⇒ 轴真接上。

## 4. 定因：F1 wythoff 两例失败 = **能力缺陷，非夹具缺陷**

非同源 oracle 与冻结期望 15/15 一致 ⇒ 判据无缺陷。逐例分类（`evidence/oracle-wythoff-r531.json`）：

| case | stdin | 期望 | A0-off | A1-on | A2-merge | codex | 分类 |
|---|---|---|---|---|---|---|---|
| #43 | `21 25` | `WIN 15 15` | `WIN 1 13` | `WIN 15 15` | `WIN 15 15` | `WIN 15 15` | A0-off: `illegal_move`（取两堆不等量；题面只允许单堆取或**等量双取**） |
| #57 | `25 25` | `WIN 25 25` | `WIN 2 11` | `LOSE` | `WIN 25 25` | `WIN 25 25` | A0-off: `illegal_move`；A1-on: `wrong_lose`（漏 `(t,t)` 双取分支 ⇒ 把 `(n,n)` 读成必败） |
| #55 | `1 1` | `WIN 1 1` | `WIN 1 1` | `LOSE` | `WIN 1 1` | `WIN 1 1` | A1-on: `wrong_lose`（同上） |

⇒ 两臂各 2 例失败是**两种不同**的实现缺陷（非法着法 / 漏双取分支），A2-merge 与 codex 同题全对；缺陷与「纪律/合批」无关 —— 单窗内 4 臂是 4 个独立会话，本次差异只能记为**会话内能力波动**，不可归因到轴。

## 5. 裁决与诚实边界

- **裁决：`exec_precondition --round r531` rc=1 ⇒ 本轮 token/调用降幅一律标「参考（未可验收）」，禁作验收依据。**
- 执行面 < 声明面：预注册声明 w1/w2/w3（12 格），本轮只跑出 **w1（4 格）**；`w2/w3` 已在本轮收口后**补跑中**（`run-0917-222519-w2`）。
- **单窗读数 = 噪声**（R529 教训：同臂跨窗摆动可达 4.25×）⇒ 上表轴读数标 `provisional`，逐窗极差待 w2/w3。
- AOT：本轮臂用 `/tmp/pub_r531/agenthost`（sha256 `d5848776…`，2026-09-17 21:28）。收口时对**当前树**重发布 `/tmp/pub_r532`（`d399142c…`，IL 警告 0，15,613,264 B，且与 `/tmp/pub_r532b` 逐字节相同 ⇒ 产物与输出目录无关）；两产物不同源的原因是**兄弟会话在 22:13 落地 `af8c15b`（R-N1：`src/agent/contract/*` 进 `agent` 库）**，该提交在 w1 起手之后 ⇒ 编译图变化、w1 读数不受影响；`w2/w3` 沿用 w1 二进制以保轴同源。
- 未测到：① `A2-merge` 的同题跨窗稳定性（待 w2/w3）；② codex 侧 token 计量（只记到调用数 32）；③ `t1` 任务上 merge 反而比 A1-on 多调用（33 vs 17）⇒ 轴收益**按任务分布不匀**，未作因。
- 未提交的共享台账（`eval/capability/kpi.jsonl` 的 `EXP1-Q47` 行、`eval/bge/r404/*`）**归属侧自身**，本轮不动。

## 6. 下轮候选

1. `w2/w3` 补齐 + 逐窗极差表（`reps≥3`），并重算 P1/P2。
2. **第 8 条纪律候选**（题面逐条对齐：先枚举题面每条输出约束，收尾前逐条自验）——目标把 `illegal_move` / `wrong_lose` 两类缺陷堵掉；单变量臂 + `nc` 参照 R531 的失败例。
3. codex 侧 token 计量补齐（现仅调用数）。
4. `g1` 调用数按臂摆幅大（10 / 33 / 34）⇒ 合批轴在长任务上收益最大，值得单独按任务分层报数。
