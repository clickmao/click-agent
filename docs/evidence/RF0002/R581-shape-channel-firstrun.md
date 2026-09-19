# R581 · RF0002 §3 验收面 ②③④ 真机首验（形状通道落 ≥1 条 `nlp_shape` 事件）

- **轮次**: R581 · 日期 2026-09-19 · 承 R579-tick（打点可测化）/ R577-① / R580 候选①
- **预注册**: `eval/rover/r581/prereg-r581.json`（先于任何真机跑次落盘）· **DAG**: `eval/rover/r581/dag-r581.json`
- **产品面**: **零源码改动**（只跑 + 落盘 + 读取；唯一改动是器具读法修正，见下「器具」）
- **真机二进制**: `src/agent.host/bin/Release/net10.0/agenthost`（HEAD `adbe56d` 建；sha256 记于 `pre-arm-state.txt`）
- **命令面**: `agenthost --role ./skeptic.rbin --session-id <id>` 经 stdin REPL 逐轮投递 · 三臂串行（同遥测面 / 同形状库 / 同工作树）

## 1 · 两跑次（v1 VOID → v2 重跑）

| 跑次 | 时点 | 前置 | 结果 |
|---|---|---|---|
| v1 | 18:44 | `AGENTFRAMEWORK_KEYS_DEEPSEEK` 未设置 | 每轮 `失败: 环境变量 … 未设置` ⇒ 远端调用不成功 ⇒ 依预注册 `fail_closed` 第 2 条**全臂 VOID**；原始日志留档 `eval/rover/r581/v1keys-absent/` |
| v2 | 19:57 | key 面就位（`~/.agentframework/keys.env`, 0600, 仓外）+ 远端预检 `http=200` | 三臂齐（A 18s / B 4s / N 7s），读数见下 |

v1 的 VOID **不判缺陷**（学习前提不成立）；v2 与 v1 唯一差异 = 环境变量面，臂设计 / 轮次 / 命令面逐字沿用。

## 2 · 判据裁定（预注册照原样判，未放宽）

| 判据 | 期望 | 实测 | 裁定 |
|---|---|---|---|
| P1 ② 行使面 | A 出现 `shape=1 ∧ route=local_skip ∧ face=repeat` ≥1 条 | 轮2 / 轮3 各 1 条（`basis=mechanical:repeat→local`） | **PASS** |
| P2 ④ 命中面不增远端调用 | `shape=1` 的轮零 `llm_call`（逐轮切窗） | 轮2 **4 次** / 轮3 **7 次** | **FAIL** |
| P3 ③ 学习 | 学习轮后 `shapes>=1` | 轮1 `learned=1 / shapes=1`；库落盘 1 条（40 B） | **PASS** |
| P3 ③ 淘汰路径 | B 出现 `repeat_degrade_remote(reason=no_replayable_prev)` ∧ 该轮 `hits>=1` | 事件逐字落盘 ∧ 同轮 `hits=0` | **FAIL**（合取第二项） |
| P4 泛化 | A 轮3（不同措辞）同样 `shape=1 ∧ route=local_skip` | 轮3 `msg_sha16=147757f75f39bd44`（≠轮1）仍命中 | **PASS** |
| P5 负控 | N 该轮 `learned` 增量 0 ∧ `shape=0` ∧ 库不增 | `learned=0 / shape=0 / shapes=1` | **PASS** |
| — 净下降 | 预注册已写明「同轮远端成功即重新学到」⇒ 不可观测 | — | 未测到（不作失败） |

机检前置（`mech_engaged`）：`local_turn_gate_config{turn_gate_enabled=True, local_channel_ready=True, repeat_skip=on, role=skeptic}` 三臂均落盘 ⇒ 机制已挂载（非未接线）。

## 3 · 后验归因（`posthoc-r581.json`；不改预注册判据）

- **P2 机理**：命中轮的远端调用**全部**是 `finish_reason=tool_calls` 的**工具循环**调用（`empty_cause=tool_call` / `retry_skipped=true` / `routed_to=action*`）；t1 形态的主回答调用（`finish_reason=stop`, prompt 4362）确未发生 ⇒ **「本地消化」当前只覆盖最终答复文本**（`local_gate_skip_reply` 重放），未覆盖该轮工具循环面。
- **三列口径（逐轮，同一次运行内）**：调用数 1 → 4 → 7；**新算 prompt 4234 → 1150 → 2311**（命中轮 −73% / −45%）；completion 599 → 616 → 1408；含 cache 总 prompt 4362 → 7038 → 14727。⇒ 命中轮不是单一方向的「省」或「费」，**必须三列分列**（用户钦定口径）。
- **P3_eviction 机理**：`hits` 语义 = 本地回放命中数；B 为全新会话 ⇒ 无可重放上一答复 ⇒ 该量**结构性为 0** ⇒ 预注册把「降级路径可达」与「回放命中」绑成一个合取判据 ⇒ 下轮候选 = 拆成 P3a / P3b。
- **P1/P4 的归属边界（必须与 PASS 一起读）**：四条 `nlp_shape` 事件的 `hits` **全为 0**，命中轮的决策依据字段是 `basis=mechanical:repeat→local`（规则面），不是 `learned-shape`。⇒ 本轮证实的是**「学到了」+「规则面本地化」**；**「按学到的形状命中」未测到**（未测到 ≠ 无效应，也 ≠ 已验收）。分离手法见下轮候选。

## 4 · 器具（自捕 1 件，已修，未放宽判据）

- **缺陷**：`extract_r581.py` 的 `read_slice` 用文本模式 `f.seek(off); f.read(byte_delta)` —— `read()` 入参在文本模式下是**字符数**，含多字节字符的切片被多读（arm A 多读 1 条 arm B 事件）并在切点产生 1 条**假解析失败**。
- **修法**：改字节切片（`open(TEL,"rb")` + `decode(..., errors="replace")`）。**判据逐字未动**。
- **首跑读数留档不翻案**：`readings-r581-v1textmode.json` / `verdict-r581-v1textmode.json`；修正后差异 = `events A 148→147`、`parse_fail 2→0`，**verdict 逐键相同**（⇒ 判据未受读法影响）。
- **边界件说明**：`shapes_lines` / 库文件由本轮首验创建，收尾已**复原为不存在**（内容留证 `shapes-r581.txt`）。

## 5 · 诚实边界（未测项如实记）

1. **零产品源码改动** ⇒ **不宣称任何质量 / 成本降幅**（无可比窗口）。
2. 单轮 n=1 每臂 ⇒ 只作**机制存在性**证据，不作分布结论。
3. **质量 / 轮数 / 问答计数 / codex 外部真值对照**：本轮**未测**（非质量对照窗，无同题面）。
4. P2 / P3_eviction 的 FAIL **照原样入档**，后验解释单列，不构成翻案。

## 6 · 下轮候选

① 命中轮工具循环面（调用 4/7）是否为承重项 —— **先量再改**；
② P3 合取判据拆分（P3a 降级路径 / P3b 回放命中）后**重注册**；
③ 「learned-shape 命中 vs 规则面命中」分离臂（非 repeat 面 / 同面异规则），把 `hits>0` 变 ≥1；
④ 命中轮 completion 上升（599→616→1408）归因：工具循环 vs 上游空正文；
⑤ 作业环境自备 key 面（本轮暴露：cron 会话环境缺 `AGENTFRAMEWORK_KEYS_DEEPSEEK`）。

## 7 · 轮志坐标

- 读数：`eval/rover/r581/{readings-r581.json, verdict-r581.json, posthoc-r581.json, arm-*.log, arm-meta.txt, pre-arm-state.txt, gate-pre-r581v2.json, shapes-r581.txt}`
- 台账：`eval/capability/kpi.jsonl`（R581）· 冲突登记：`docs/reports/round-collision-log.jsonl`（R581 v1 VOID）
- 预注册 / DAG：`eval/rover/r581/{prereg-r581.json, dag-r581.json}`
