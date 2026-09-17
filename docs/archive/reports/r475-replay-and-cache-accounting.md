# R475 报告 · 复述回放取实质答复 + 命中率口径禁 >1 + 记账/证据面补齐

- 轮号: R475（本侧主线轮；`updated_round=R475`）
- 计划: `docs/plans/v0.91.0-r475-replay-and-cache-accounting.md`
- 预注册: `eval/rover/r475/prereg_r475.json`（C1–C8）｜裁决: `eval/rover/r475/verdict-r475.json`
- 上游: R474（真端点首次暴露质量缺陷 + 记账缺口）

## 1 因果链

R474 把远端从桩换成真供应商后，同一条门控管道暴露出两处**同源**问题：

1. **质量**：R 臂 12 轮里 6 轮模板应答、3 轮用户可见「模型未产出正文…」徽标 ⇒ 实质回答仅 3/12（Arole 12/12）。
   机制：`t6「再讲一遍。」` / `t9「从头再说。」` 被 `IsPureRepeat` 判为纯复述 ⇒ 走本地消化 = **回放上一条答复原文**；
   但上一条要么是空正文徽标、要么取不到 ⇒ 回放路径把**失败**当成答复端给用户（或退回模板冒充答复）。
2. **记账**：产品 `llm_call` 自报 16 调用 / 55,432 prompt tokens，供应商 usage 是 20 / 70,890 ⇒ 差的 15,458（21.8%）
   全在 `llm_call_recover` 行（不带 prompt/缓存字段）⇒ 产品自记账**漏账**，而漏的那部分正是缓存决策的依据。
3. **口径**：同一份真值里 `effective_hit_rate` 出现 **3 例 >1**（1.0589 / 1.0066 / 1.0822）。
   机制：分母「同会话可缓存上界 = min(prompt, 上一条 prompt)」小于真实命中量（命中来自更长的**跨会话共享前缀**）。

## 2 改动

| # | 改动 | 单源/可机检 |
|---|---|---|
| A | `ModelQueueRouter.IsReplayableReply` 回放守卫；取不到实质答复 ⇒ **撤销 Skip 降级远端**（`gate:repeat_no_replayable_prev` + 遥测 `repeat_degrade_remote` / `prefilter_repeat_degrade`） | 用户轮判据复用 `IsPureRepeat`；Assistant 侧判据基于产品自身 `EmptyBodyBannerPrefix` 常量（**非**新增用户轮关键词表） |
| B | `llm_call_recover` 两条 emit 补 `prompt_tokens`/`cache_hit_tokens`/`cache_miss_tokens`/`cache_hit_rate`（同源 `first`，未上报 -1） | 结构门 A5/A6 反向断言 old form |
| C | `EffectiveHitRate` 钳制 `hit > cacheable ⇒ -1`；`Channel`/`SharedPrefix*` 增加 `ExceedsSameSession`（命中超过同会话上界 ⇒ 归 `shared_prefix`） | 单测 C1–C4；真实 43 条夹具（last=0 路径）零回归 |
| D | 中继 v2 `relay_real_r475.py`（**另存不改 R474 器具** = 证据↔器具绑定）：采样面 + `finish_reason`/`content_len`/`reasoning_len`/`reasoning_tokens`/`empty_body` + **逐调用**恒等式 | `selftest_relay_r475.py` S1–S7 |
| E | `join_usage_truth.py` 双列并账：真值列/自记列硬分离，唯一跨列运算 `gap.*`，缺字段 ⇒ `unreconciled`（**禁按 0**） | `--selftest` PC + NC1–NC4 |

## 3 读数

| 项 | 值 |
|---|---|
| R474 质量缺陷（R 臂） | 实质 **3/12** · 模板 **6/12** · 用户可见徽标 **3/12** |
| R474 漏账（真值 − 自记） | Arole **15,458 tok (21.81%)** ｜ R **9,171 tok (31.11%)**（只作漏账量级证据，**禁作 KPI 分母**） |
| 真值列恒等式 `prompt == hit + miss` | **20/20 ∧ 9/9** 成立（本器具重算；来源标注 `identity_checked_by=recomputed`） |
| `effective_hit_rate` >1 | 3 例 → 本轮口径后**不可能**（-1 + 归 `shared_prefix`） |
| 中继 v2 自检 | S1–S7 **7/7**（零真实调用，本地假上游） |
| 并账自检 | PC + NC1–NC4 **5/5**（NC4: 真数据必有红 ⇒ 判据非恒绿） |
| AOT | 15,343,232 B · sha16 `b03ee2bbb015e972` · IL 警告 **0** · `env -i --version` rc=0 · `ldd` 仅 libc/libm |
| 定向单测 | `R475AccountingTests` **8/8**；`UserFacingFailureTests` 通过（判据 4b 改单源形态） |
| 全量单测 ×3 | run3 **1431/1431 Failed 0**；run1/run2 各 1 例 flake（`FrontendAskSameConnTests` 10s / `TelemetryPendingTests` 3ms），**隔离复跑 ×5 全绿**（4/4 ×5）⇒ 非本轮改动（`FrontendAskSameConnTests` 在改前首跑亦红）｜日志 `eval/rover/r475/tests_x3_r475.log` |
| 台账 | registry **132 → 135 行**（L2×3，`updated_round=R475`）；taskplan **43 → 44 节点**；kpi.jsonl **73 → 74 行**；improvements +R475 段（388,649 → 391,509 B）；轮次索引 +3 行（扩到 R475，机检披露 **459/473 号未被使用**） |

## 4 诚实边界

1. 本轮**零真实供应商调用 ∧ 无 llama-server**（`MemAvailable` 1984 MB < 2650 MB 起手闸）⇒ 质量修复只经**结构门 + 单元测试**，**未做真机 E2E 复演**；`repeat_degrade_remote` 在真实流量上的首样本仍为 0。
2. `llm_call_recover` 字段补齐（fix B）在真实流量上的闭合**未验**：真数据（R474 产物）`J2/J3` 仍红 —— 那是修复前的产物，属预期，不是失败。
3. 命中率口径修复只改**归因/上报**；供应商**命中是否折价**仍未取到 ⇒ 「命中 ⇒ 省钱」仍是未验证前提。
4. 中继 v2 的空正文定因面（finish_reason/推理长度）只经本地假上游自检，**R474 空正文根因仍未定位**（本轮只把所需证据面补上）。
5. 97% 红线的真机可达性仍只有 R469 的离线界（同会话第 2 轮真实样本 = 0）。
6. **形式闸自捕**：首次全量单测红 2–3 例，全部来自 R2f「产品面证据绑定」闸（新增行未带 `evidence_generated_with`）⇒ 用 `eval/capability/bind_evidence.py --apply` 补齐；该器具把 `audited_by_round` 写死 `R473`，本轮新增行已手工改回 `R475`（该校验只要求 `^R\d+$`）。器具常量应参数化，列下轮候选。
7. **全量 ×3 未三次全零**：run1/run2 各 1 例（socket 超时 / telemetry flush 3 ms），隔离 ×5 全绿 ⇒ 定性为并行/负载 flake；本轮未改测试语义（下轮候选：降并行度或给这两族加隔离标签）。
8. 本轮为**改链轮**：`kpi.jsonl` 行以 `kind` 标注，token/命中率数值**无变化**（无真实调用）⇒ 对「token ↓≥30%」主线是**间接步**（质量 + 可复核性）。

## 5 下轮候选

1. 开内存闸后跑真机 E2E：中继 v2 让上游返回空正文 ⇒ 验「徽标轮 + 复述轮」**不再冒充答复**（fix A 的行为证据）。
2. 真机样本验 recover 字段闭合 + 双列并账 `J3` 转绿。
3. 命中率红线迁移为「分档上限 + 达成轮占比 + 分通道」（R469/R470/R471 联合口径）。
4. 供应商计价面（命中折价）取证。
