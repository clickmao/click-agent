# R444 证据书 · 廉价必要条件前置（`¬Ack ⇒ Pass`）的可证等价优化 + 短档真值补列

- 轮次: **R444**（v0.64.0）
- 被测二进制: `/tmp/pub_r444/agenthost` sha256 `e36d04d1…`（AOT, 0 IL 警告）；**粘滞修复版** `/tmp/pub_r444b/agenthost` sha256 `c28e86d3…`（AOT, 0 IL；见 §7）
- 单测: **1287/1287 绿**（含 R444 新增 G33 端口计数 / G34 源码位置不变量）
- 器具: `eval/rover/r444/{precheck_prefilter.py,run_arm_r444.sh,run_all_r444.sh,settle_r444.py,analyze_r444.py,grid/*}`
- 判据预注册: `docs/plans/v0.64.0-r444-cheap-necessary-condition-prefilter.md`（测量前落盘）

## 1. 单变量与构造性论证（本轮承重逻辑）

设 `A = MechanicalAck(message.Content)`（去标点/空白/符号后余字符全落在 `AckFamilyChars` 且长度 ≤10）。
现行代码**后置否决**：`Skip ∧ ¬A` ⇒ 改写为 `Pass`（事件 `local_turn_gate_reject`，`raw_len` 被改写为 25 = basis 串长）。因此

```
¬A ⇒ (r1 判 Skip → 被否决成 Pass) ∨ (r1 判 Pass → Pass) ⇒ 最终判决恒为 Pass, 与 r1 输出无关
```

⇒ 把 `¬A` 判定**前移**到调用之前，对 `¬A` 轮直接 `Pass "...":mechanical:nonack→remote"`，**判决路径逐位等价**，唯一差别是不再产生这次本地 r1 调用（省 token）。**默认开**（改进即生产行为），`AGENTFRAMEWORK_GATE_PREFILTER=0` 复原 R443 行为作同网格单变量对照。

## 2. R423 可分性预检（进实现的前置条件）

`precheck_prefilter.py`（负控 `--neg-control` 已实测检出 ≥1 反例、`--grid-dir /nonexistent` fail-closed rc=3）—— 用**驱动日志（外部真值）**对齐 8 个归档 BRJ 运行的门行，逐行核 `Skip ⇒ Ack`：

| 通道 | 结果 |
|---|---|
| C1 驱动日志逐轮 `actual=` | M20: t3/t18=consumed（无门行）；t7–t13 = 7 个 skip |
| C2 reject 锚点 `msg_sha16` | t2/t5/t19 三条 `local_turn_gate_reject` 精确锚定 |
| C3 块连续 + 计数 | Skip 行 7 行连续 ↔ ack 族 7 轮连续 |

**P1 反例 = 0/8 运行**（42 门行 / 41 r1 行全部满足 `Skip ⇒ Ack`）；三通道一致 7/8（1 个 W20 重跑目录遥测混合，已隔离，不影响结论）。可省 r1 调用合计 **11**（M20 单网格 10 + V2b 1）。
负控: `--neg-control` 注入 `¬Ack` 的 Skip 轮 ⇒ 必须检出 ≥1 反例；`--grid-dir /nonexistent` ⇒ 必须 fail-closed 非零（空样本不得静默通过）。

## 3. 真机读数（同网格同 NS `-s4`，三臂串行）

| 臂 | 门 | 判官 | 远端 tok（桩侧外部真值） | 门 r1 调用 | 本地真值 tok（门+判官） |
|---|---|---|---|---|---|
| A | 关 | 关 | **61256** | 0 | 0 |
| BRJ | 开（前置门**开**） | 本地优先 | **32968** | **7** | **7880**（3142+4738） |
| BRJL | 开（前置门**关**=R443 行为） | 本地优先 | 32972 | **17** | 12775（8037+4738） |

**逐轮（BRJ）**：t1 `mechanical:pass`；t2–t6 `mechanical:nonack`（0.04–0.08s，零本地成本）；**t7–t13 唯一触发本地 r1**（13.5–65.4s，`gate:skip→local`，回复 21 字=本地消化）；t14–t20 `mechanical:nonack`（0.07–0.2s）；t3/t18 = 澄清问句吞并轮（`consumed`，与 R440/R441 一致）。

## 4. 判据结果

| id | 判据 | 结果 |
|---|---|---|
| D1 | 记账恒等 `tokens_evaluated == prompt_new + cache_n` | **全绿**（门/判官违规 0；机械行按契约记 -1） |
| D2 | 真值 vs「字符/2」折算 | 门 prompt **1.395–1.398×**（复现 R443 1.398×）、判官 prompt **1.496–1.508×**、门 gen 1.04–1.27× |
| D3 | 口径三档（见 §5） | M20 远端 46.18% / +本地真值 **33.32%** / +本地折算 39.24% |
| **D4** | **等价性（承重）BRJ vs BRJL** | **逐轮差异 0 条**（20/20 轮 `actual` ∧ `G_calls` ∧ `J_calls` ∧ `reply_source/len/head` 全同）；门 r1 调用 7 vs 17 |
| D5 | 成本下降 | 省 **4895 tok / 10 次调用 = 489.5 tok/调用**（两臂判官真值同 4738 ⇒ 差额全来自门） |
| D6 | 含本地真值降幅（M20） | **33.32% ≥ 30%**（R443 同口径 25.32%） |
| D7 | 质量 | BRJ/BRJL `fn=0 fp=0 acc=1.0`；A 臂 `fp=7`（不能跳）⇒ 门判定未引入任何错跳 |
| D8 | 短档真值补列 | V2b **13.03%**、W8 **1.11%**（含本地真值口径，见 §5）；**W20 本轮排除未测** |
| **N1 正控** | BRJL 必须观测到 `gate:skip_rejected_nonack` | **3 条**，`prefilter=0` ✓ |
| N2 负控 | BRJ 无 rejected / 违规 0 / `prefilter=1` | **0 / 0 / ['1']** ✓ |
| N3 | 桩侧调用数 == 自报 G+J | 7/7 臂 `unassigned=0` ✓ |

## 5. L1 验收矩阵（本轮补列）

| 长度档 | k/N | 远端口径 | **含本地真值口径** | 质量(fn/fp/acc) | 形态 |
|---|---|---|---|---|---|
| V2b (N=4) | 1/4 | 32.24% | **13.03%** | 0/0/1.0 | AOT ✓ |
| W8 (N=8) | 1/8 | 13.76% | **1.11%** | 0/0/1.0 | AOT ✓ |
| M20 (N=20) | 7/20 | 46.18% | **33.32%** | 0/0/1.0 | AOT ✓ |
| W20 (N=20) | 1/20 | 3.20%(R441) | **未测到**（本轮排除） | — | — |

结论：**≥30% 只在「可跳比足够大」的档位成立**（7/20 中簇），且**只在计入本地 r1 真值成本后仍成立**这一点上，本轮由前置门首次做到（R443 同口径 25.32% ⇒ R444 33.32%）。

## 6. 诚实边界

- **粘滞字段缺陷（本轮的负向发现，已修并验证）**：R443 新增的真值遥测按「上次调用值」发射，机械判定轮（未建 prompt、未问 r1）会**继承**上一次 r1 的真值 ⇒ M20 BRJ 6 行虚增 2382 tok，把 33.32% 压成 **29.43%**。修 = 发射点按 `gateLocalCall` 判据（`basis` 前缀非 `mechanical`）写 -1/实测值；验证 §7。
- **两臂远端 tok 差 +4**（32968 vs 32972）= 工作区路径入 system prompt 的已知 +1.04 tok/调用混淆（R443 D2b），BRJL 目录名多 1 字符、命中 4 次调用 ⇒ 与 `per_turn` 逐位等价不矛盾（逐轮 G_tokens 全同）。
- 本地 r1 成本按 llama-server 上报真值计；**未含**时延/显存/电费；判官侧本地成本不受前置门影响（两臂同 4738）⇒ 本轮只优化门的固定成本部分。
- 短档（V2b 13.03%、W8 1.11%）**不达标**：k/N 小 ⇒ 单次 skip 相对整轮总成本太小，属结构性问题，不是前置门失效。
- `MechanicalAck` 语义未放宽（不放宽 = 不引入新跳过）；J 侧无同类机械不变量，未做前置。

## 7. 器具修复验证（见 `verdict-r444-analysis.json` 的 `D1b_sticky`）

| 构建 | 网格/臂 | 粘滞行数 | 注入 tok |
|---|---|---|---|
| `e36d04d1`（旧） | M20/BRJ | 6 | 2382 |
| `e36d04d1`（旧） | M20/BRJL | 0（正控：该臂无机械行接在本地调用之后） | 0 |
| 修复版 `c28e86d3072a…` | M20/BRJ | **0** ✓ | 0 |
| 逐轮等价 | BRJ(-s4旧) vs BRJ(-s5修复版) | 差异 **0/20 轮** ✓；远端 **32968 == 32968** ✓ | — |

## 8. 复现

```bash
export DOTNET_ROOT="$HOME/.dotnet"; cd /home/agentuser/AgentFramework
python3 eval/rover/r444/precheck_prefilter.py               # 可分性预检 (rc=0, 反例 0)
R444_NS=-s4 bash eval/rover/r444/run_all_r444.sh            # 7 臂串行真机 (~25 min)
python3 eval/rover/r444/analyze_r444.py                     # D1–D8 + N1–N3
python3 eval/capability/instruments_check.py                # L2 器具验收面
python3 eval/capability/status_gen.py --check               # L3 单一审计面
```

台账: `docs/verification-registry.json` → `r444.*`（7 行）；`eval/capability/kpi.jsonl` → R444 行。
