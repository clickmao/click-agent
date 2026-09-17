# R477 · 真机 E2E：R475 复述回放守卫复演 + R476 分档打点实发核验 + KPI 降幅复测

- 轮号：R477（date 2026-09-16；夹具 `eval/rover/r438/grid/task-p12.json`，12 轮，臂 = Arole（门关）/ R（门开），同二进制 `db187e0eae7f26ea`）
- 预注册判据：`eval/rover/r477/prereg_r477.json`（跑前落盘）⇒ 判定 `eval/rover/r477/verdict-r477.json`（器具 `eval/rover/r477/check_r477.py`，常量源码派生 fail-closed）
- 结算命令：`python3 eval/rover/r477/check_r477.py`

## 因果链

r1 门控需要「复述轮不给用户看模板」这项用户可见质量证明（R474 发现 12 轮里 6 轮是机械模板），R475 改了回放守卫、R476 改了分档打点 —— 但两轮都只有单测/离线证据。R477 把两条修复一起放到**真机**上跑：门关臂（Arole）与门开臂（R）各 12 轮真调供应商端点，供应链侧 `finish_reason`/`empty_body` 定因字段（relay v2），再用 `check_r477.py` 对 8 条预注册判据出判。

## 本轮产出（文件 / 命令 / 读数）

| 产出 | 路径 |
|---|---|
| 预注册 | `eval/rover/r477/prereg_r477.json`（跑前） |
| 臂执行器（自 r474 派生：relay v1→v2 + 起手闸） | `eval/rover/r477/run_arm_real_r477.sh` |
| R 臂单跑（含沉降等待，修起手闸假阴性） | `eval/rover/r477/run_arm_R_only.sh` |
| 判据器 + 结算 | `eval/rover/r477/check_r477.py` → `verdict-r477.json` |
| 原始面 | `usage-{Arole,R}.jsonl`、`calls-{Arole,R}.jsonl`、`turns-{Arole,R}.jsonl`、`tel-{Arole,R}/host.jsonl`、`both.log`、`r_only.log` |

判据结果（预注册 8 条 + 事后 4 条）：C1 链 12/12 双臂 ok（阻塞 0）**pass**；C2 KPI 降幅 ≥30% **pass**；C3/C4 **字面 fail（机制假设被证伪，见下）**；C5 定因字段存在 **pass**；C6 R476 分档 7 字段实发 **pass**；C7 记账闭合 **pass**；C8 预算/身份/二进制 **pass**；事后 P1/P2/P3 **pass**、P4 记录归属漂移。

## 基线对比（同夹具 task-p12，供应商 usage 真值）

| 读数 | R474（04:22）Arole→R | R477（05:52）Arole→R | R477 变化 |
|---|---|---|---|
| 中继调用次数 | 20 → 9（−55.0%） | **21 → 10（−52.4%）** | 同量级 |
| prompt token | — | 68329 → 35600 | **−47.9%** |
| completion token | — | 5320 → 2144 | **−59.7%** |
| **总 token** | 76094 → 32769（**−56.94%**） | 73649 → 37744（**−48.75%**） | 均 ≥30% 达标 |
| 成本上界 CNY | — | 0.024301 → 0.011970（闸 0.15 未触） | — |
| 缓存命中 token | — | 58624 → 28160 | 命中率 0.858→0.791 |
| 用户可见质量 | Arole 实质 12/12 | Arole 实质 5/12（7/12 徽标）；R 实质 6/12（t2–t5 为确认轮模板，2/12 徽标） | 见「诚实边界」 |
| 测试 | — | `VerificationFormTests` 7/7 pass（登记表 143 行，`updated_round=R477`） | — |
| AOT 体积 | 15,355,520 B | 同（本轮无 C# 改动 ⇒ 未重发布，`sha16=db187e0eae7f26ea`） | 0 字节 |

门控决定（R 臂，产品遥测 `local_turn_gate`）：t1 `mechanical:pass→remote`、t2–t5 `gate:skip→local`（确认轮模板）、t6 `mechanical:repeat→local`（**逐字回放 298 字符**）、t7 `mechanical:nonack→remote`、t8 `mechanical:nonack→remote`、t9 `mechanical:repeat→local`（**逐字回放 298 字符**）、t10 `pass→remote`、t11 `nonack→remote`、t12 `pass→remote`。

## 事后判据（预注册 C3/C4 被证伪后的收窄版，单列）

- 证伪事实：预注册假设「t6/t9 无前驱实质答复 ⇒ 必须出现 `repeat_degrade_remote` 降级事件；t9 == t8 逐字」。实际 `repeat_degrade_remote` = 0 例，t9 ≠ t8 —— 因为守卫会**向前回溯到最近一条可回放者**，t2–t5 的模板不算可回放，故回放对象是 t1 的实质答案；t8 的回复本身是空正文徽标，同样不可回放。
- **P1**：R 臂复述轮用户可见回复非模板、非徽标、非空 **pass**（t6=t9=298 字符 = t1 实质答案逐字）。
- **P2**：t9 该轮供应商侧收费行 = 0（可见回复窗口 0.21s 内 usage 行 0 条）∧ 该轮产品归因的 1 条远端调用 ts 落在可见回复**之后** 68ms（因果上不可能产出该回复）**pass**。
- **P3**：回放事件按**输入指纹**对齐 —— `local_gate_skip_reply.msg_sha16 == LocalInputFingerprint.Sha16(该轮用户消息)`（t6/t9 两条 kind=`repeat_verbatim`，chars=298），且 t2–t5 四条仍是 kind=`template`（未被误升级）**pass**。
- **P4（漂移记录，不判红）**：产品遥测 `llm_call.turn` 归属与回复发出时点无因果序 —— 5 条调用的 ts 落在所记轮次窗口之外（偏移 0.07–3.4s）。

## 定因面（C5）：空正文徽标 = 上游 `tool_calls`，**非**推理预算

20/20 空正文调用的供应商侧 `finish_reason == tool_calls`，请求携带 4 个 tools，`max_tokens == None`（未被截断），`reasoning_tokens_max` 仅 395（Arole）/122（R）≪ 预算；有正文组的 `finish_reason == stop`。⇒ 徽标文案「推理过程占满输出预算（已自动放宽输出预算并重试一次仍失败）」是**误诊**（真实失败面是 tool_calls 语法下的空 content）。对照证据：R474 的 Arole 臂请求体与 R477 逐字段同源（仅 rundir 路径不同）而当时 0 徽标 ⇒ 属**上游行为漂移**，不是本轮零改动引入。

## R476 分档打点实发核验（C6）

真机每主调用遥测行均带 7 字段：Arole 13/13、R 7/7（`cache_band` / `cache_band_source` / `cache_band_growth` / `cache_ceiling` / `cache_target` / `cache_margin` / `cache_band_verdict`）；取值域合法（verdict ∈ {at_target, below_ceiling, below_target, not_applicable, unreported}，ceiling ∈ {−1} ∪ (0,1]，growth ∈ [0,348)）。**记录在案的不一致**：预注册字段名写 `cache_growth`/`cache_band_target`，源码实为 `cache_band_growth`/`cache_target` ⇒ 器具按源码派生名判定（取不到即抛 `MISS(src-const)`），漂移单列，不改源码迁就预注册。

## 本轮发现并修掉的器具缺陷（非产品缺陷）

1. **起手闸假阴性**：臂收口只 `pkill -P $HOST_PID`，本地 r1（`llama-server`，RSS 1.83GB）在 R 臂起手时尚未释放 ⇒ `MemAvailable=1318MB < 2650MB` 闸下（`rc=10`），而 **12s 后同一内存自行回落**。修：`run_arm_R_only.sh` 加「沉降等待（MemAvailable ≥ 2650 ∧ llama-server 计数 0，上限 120s）」；并按 R451 先例做跑前清理（停 MSBuild 复用节点 151MB、空闲 LSP 133MB：2634→2792→2739MB）。
2. **沿用未改**：门控归属必须显式传 `--role`、门必吃 `message.Content`（R469 教训）——本轮两条都由 `local_turn_gate` 行自证已生效。

## 诚实边界

- 单夹具（task-p12）、单次（无重复采样）；**上游在 R477 期间行为漂移**（tool_calls 空正文），故 Arole 臂不是干净基线：R477 的 −48.75% 与 R474 的 −56.94% 只能是**同向同量级**，不能当同分布复现。
- 未测「本地生成替代远端实质回答」的增益面：r1 只落在确认轮（4 轮）与复述轮（2 轮），主干实质轮（t1/t7/t8/t10/t11/t12）仍走远端 ⇒ 30% 降幅主要来自确认轮与复述轮的**零远端**，而非本地替代生成。
- C3/C4 预注册写法**未被满足**，本文不含糊：原文保留判 fail，收窄版 P1–P3 单列（判据纪律：不覆盖预注册）。
- 未重发 AOT（本轮零 C# 改动）；「AOT 可用 + IL 警告 0」本轮未取新证据，沿用 R476 的 15,355,520 B / `db187e0eae7f26ea`。

## 下轮候选（R478）

0. **台账缺口补齐**：`docs/reports/iteration-master-plan.md` 的「轮次索引」自 R474 后未再机派生刷新（R476 亦未刷），`improvements.md` 缺 R476 块 —— 属既有缺口，下轮按 R472/R474 先例机派生刷新（禁手改历史行）。
1. **修空正文误诊 + tool_calls 空正文处理**（用户可见质量最大损失项）：徽标须报真实 `finish_reason`；空 content ∧ 非空 tool_calls 不应等同「未产出正文」失败。
2. **turn 归属因果化**：把 `llm_call.turn` 绑到「该轮 reply 对应的请求 id」而非计数器（P4 的 5 条越窗）。
3. **命中率按分档口径重估**：R 臂命中率 0.791 < Arole 0.858（门控把长前缀换成短前缀），需按 R476 5 态判「哪些是口径问题（rate<0 被记 unreported）」。
4. 本地替代生成的增益面：把门控从「确认/复述轮」扩到低风险实质轮，测远端调用数与 token 的边际下降（带质量对照）。
