# R445 · 判官侧机械前置筛选的**可分性预检**（零测量轮）

轮次: R445 ｜ writer: r445-main ｜ 日期: 2026-09-15 ｜ 形态: 离线复算归档 telemetry（**未跑真机、未改产品源码、未 AOT**）

## 0. 结论（一句话）
**负结论**：在全部归档证据（541 判官行 / 244 行真机 r1 实答 / 60 个已归档 run / 13 个轮次）上，
判官（`CorrectionDetector` L2）**不存在消息面或上一轮来源面的廉价必要条件** —— 候选 ①（把门侧
`¬Ack ⇒ Pass` 的同构前置搬到判官）**在判官上不可实现**；预注册的 C1（标记面）与 C3（短消息面）被证伪。

## 1. 因果链
R444 已把门侧固定成本压掉一半（门 r1 调用 17→7；含本地真值口径 25.32% ⇒ **33.32%**）。
判官侧是剩下的固定成本（M20: 本地 1974 tok / 13 次调用，两臂同）。
若判官也有「廉价必要条件」，则可在**不调模型**的情况下把一部分行判为 Neutral（下游只吃 `Kind`，
Neutral=不罚不赏 ⇒ 与实调一次在 Kind 上等价），把 33.32% 继续往上抬。
本轮先回答**可分性**（能不能做），不问值不值。

## 2. 器具与判据（预注册于 `docs/plans/v0.65.0-r445-judge-side-prefilter-precheck.md`，先于取数）
- 器具: `eval/rover/r445/judge_prefilter_precheck.py`
  - 标记表**程序化派生**自 `src/agent.roles/CorrectionDetector.cs` 字面量（派生 CorrectMarkers=18 / AdoptMarkers=12），
    含零宽码位断言（R435 U+200B 教训）；不手打任何词表。
  - 只统计 `source=local ∧ prompt_len>0` 的行；`prompt_len` 在源码 `IndustrialAgentV2.cs:1741` 的 caller lambda 内赋值
    ⇒ `prompt_len>0` ⟺ L2 真被调用（不是配置标记）。
  - 消息全文经 `turns-*.jsonl` 以 `msg_head`（= `message.Content` 前 18 字，`IndustrialAgentV2.cs:1778`）**前缀锚点**对齐。
- 复现命令：
  ```bash
  cd /home/agentuser/AgentFramework
  python3 eval/rover/r445/judge_prefilter_precheck.py                       # 主判据
  python3 eval/rover/r445/judge_prefilter_precheck.py --neg-control \
        --out eval/rover/r445/precheck-negcontrol.json                      # 负控
  python3 eval/rover/r445/judge_prefilter_precheck.py --grid-dir eval/rover/NOPE_R445; echo rc=$?   # fail-closed
  ```

## 3. 读数（器具 stdout + `precheck-judge-prefilter.json`）
| 判据 | 内容 | 结果 | k(反例) | s(省调用) |
|---|---|---|---|---|
| C1 | ¬(含 Adopt/Correct 标记) ⇒ Neutral | **FAIL** | **124** | 116 |
| C2 | len(msg) ≤ 24 ⇒ 允许 | PASS **空心** | 0 | 0 |
| C3 | len(msg) ≤ 16 ⇒ 允许 | **FAIL** | 5 | 0 |
| C4 | M1 ∨ len≤24 | PASS **空心** | 0 | 0 |
| C5 | 负控 `len ≤ 0` 必须检出反例 | PASS | 128 | 116 |
| C6 | 正控 `signal=no_prev_reply` ⇒ Neutral ∧ prompt_len=0 | PASS | 30/30 合规 | — |
| C7 | 不存在的 `--grid-dir` | PASS (rc=2, 无产物) | — | — |

样本面：`judge_rows_total=541`、`real_local_llm_rows=244`、`stub_or_remote_rows=297`（**排除**）、
`unaligned_rows=0`、`runs_used=60`、`struct_rows=30`；真值行 Kind 分布 = Neutral 116 / Adopt 100 / Correct 28。

C2/C4 之所以 PASS 却无用：归档用户语料**全部** ≤24 字（`s=0` ⇒ 没有任何调用可省），是**空心通过**，
按 R149 口径不算证据。

## 4. 为什么 C1 会被证伪（事后探索，非判官真值，仅供 R446 定靶）
- 判官裁决**不是消息的函数**：7 条消息在跨 run 上拿到互不相同的 Kind，其中 `好，按这个来。` 同时出现
  Adopt / Correct / Neutral 三种（说明 L1 未命中的模糊消息上，r1 的字母在 run 间不稳）。
- 上一轮来源面（事后加测）也不干净：`stub_ack` n=143（Neutral 72 / 非 Neutral 71）、`gate_digest` n=37（6/31）、
  `other` n=55（38/17）、`EMPTY` n=9（0/9）——**没有任何来源类是「恒 Neutral」**，故上一轮来源面同样无廉价必要条件。
- 仪器的**已知误差带**（诚实登记）：`EMPTY` 那 9 行 Kind 非 Neutral，说明「按相邻轮 reply 重建上一轮回答」与产品里的
  `_lastReplyBySession` 在失败轮/空回复轮上会分叉（产品保留更早的成功回复）⇒ 第 4 节的 prev_class 表只作**指示性**用途，
  不作判据。消息面（第 3 节）不受此影响（只依赖 `msg_head` 锚点，unaligned=0）。

## 5. 诚实边界
- **没测到**真机：本轮零测量，未跑 `llama-server`、未跑 `dotnet test`、未 AOT ⇒ 无「实现后降幅」读数，只有可分性读数。
- 样本是**单模型**（r1-distill-1.5b-q4km）+ 该 harness 的用户语料（短句、含桩回声）；k=0/FAIL 都只是「归档内」结论，
  不外推为普适命题。
- 297 行 `source=remote|remote_fallback` 在含桩网格里是桩回声（`signal=llm:桩应答…`），**不能**当判官真值，已排除并单列。
- C2/C4 的 PASS 是空心通过（s=0），不得计入「有前置可用」。

## 6. 下轮候选（R446）
1. **判官侧改为「值/不值」而非「能不能」**：既然消息面无必要条件，改测**降级判官模型**（更短 prompt / 更小 maxTokens /
   去掉 `:143` 的空内容翻倍重试）在真机上的本地 tok 降幅与裁决一致率（对照 = 本轮 244 行归档裁决）。
2. **修判官裁决不稳**：`好，按这个来。` 三态并存 ⇒ 这是**赏罚信号质量**缺陷（R149 口径下的真缺陷），可在 L1 词表把
   高信采纳词扩到 `好，`/`行，`/`可以，` 等**前缀+短消息**形态（0 token 结算），并用本轮 244 行做回归基线。
3. 把 C5/C6/C7 三控（负控/正控/fail-closed）并入 `eval/capability/instruments-check.json` 的常规器具面。
4. 结构性短路扩展（若仍要压调用）：只在「上一轮回答为空 ∨ 会话首轮」短路（已实现）；其余需真机 A/B 才能定论，**不得**凭本轮推。
