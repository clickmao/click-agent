# R457 效果收口 —— 动作环从 2/4 到 4/4，且失败可见

对应计划: `docs/plans/v0.77.0-r457-effect-closure.md` · 状态: 已实测 (R457)
器具: `/tmp/r457_run_agent_tools.sh`（同夹具/同 6 轮输入/同模型 deepseek-flash/同一适配器）
判分: `eval/rover/r457/judge_r457.py`（只读落盘证据，不采信回复文本）

## 1. 产物（同夹具逐字节比对）

| 产物 | R455 无动作环 | R456 动作环 on | **R457 收口** | codex 0.154（冻结） |
|---|---|---|---|---|
| count.txt | 不存在 ❌ | `4` ✅ | `4` ✅ | `4` ✅ |
| merged.txt | 不存在 ❌ | ALPHA/BETA/GAMMA ✅ | ALPHA/BETA/GAMMA ✅ | 同 ✅ |
| stats.txt | 不存在 ❌ | **不存在**（口算 15，真值 14）❌ | **`chars=14`** ✅ | `chars=14` ✅ |
| first.txt | 不存在 ❌ | **不存在**（被入口作废）❌ | **`R455 fixture note`** ✅ | 同 ✅ |
| 产物合计 | **0/4** | **2/4** | **4/4** | 4/4 |

## 2. 行为指标

| 指标 | R455 | R456 | **R457** |
|---|---|---|---|
| 磁盘级伪造「已完成」 | 4 处 | 0 处 | **0 处** |
| 真实工具执行（审计行） | 0 | 4 | **8**（run_command 6 / write_file 1 / read_file 1，rc 全 0） |
| 审计命令原文 | 无 | **无**（只 sha8） | **有**（`args_head` 落命令/路径原文） |
| 上游调用数 | 7 | 9 | 15 |
| prompt ∑token | 18,039 | 31,537 | 53,163 |
| 缓存命中（总口径） | 86.6% | 84.8% | **89.8%**（cached 47,744） |
| 冷启动首调用 hit% | — | 21.6% | 60.5%（**跨运行前缀缓存污染，不可与 21.6% 直接比**） |
| 稳态 2..n hit% | — | 91.4% | **91.8%** |
| 我方 `tool_calls` 落盘 | 无器具 | 静默丢（假阴性） | **15/15 有值**（器具已修） |

## 3. 三个链机制缺口的修复与对证

| 缺口（R456 实测） | 机制修复（禁关键字补丁） | 位置 | 本轮证据 |
|---|---|---|---|
| **A2** 断言不执行：宣称「已写入 stats.txt」而磁盘无文件，且文本口算 15（真值 14） | 工具结果**尾部追加本轮执行台账**（`[本轮已执行] N 次: …`），使模型自述与事实可比对 | `ActionLoop.LedgerLine` 245 行 / 回灌 225 行 | 台账出现在 **8 个实发请求**（`tail_messages`）中；`stats.txt` = `chars=14` ✅ |
| **A3** 吞并轮：`继续`→澄清问句；T6 落不到槽位 ⇒ 「入口已作废」，整轮被吃掉 | 检查点作废后**同轮转正常任务路径**（`AGENTFRAMEWORK_PLAN_RESUME_FALLTHROUGH`，默认 on），不重拆旧问题仍成立 | `IndustrialAgentV2.PlanResumeFallthrough` 2417 行 / 分支 2455 行 / 前置提示 1909 行 | `first.txt` 落地 ✅（R456 同轮为 0 产物） |
| **G3** 缺 key 静默空回复（reply_len=0、0.04s、0 上游、无告警） | 缺凭据 ⇒ **可见失败**：`Content` + `ContentIsUserFacing=true` + `model_unavailable` 遥测 | `ModelQueueRouter` 无候选 614 行 / 缺 key 1269 行 | 真机负控 C3：**修前 len=0 静默 → 修后 len=83 可见**（`⚠ 未配置模型凭据 …`），`empty_reply:false` |
| 附带：遥测 JSONL 首行 BOM 令严格读取器崩溃 | `new UTF8Encoding(false)` | `AgentTelemetry.cs` 50 行 | 负控实测 `BOM? False` ✅ |

## 4. 器具对称（R457 必修项）

- 我方侧落盘 `tool_calls`（此前只有 codex 侧有）⇒ 两侧 `tool_calls` 步数可比。
- 审计由 `args_sha8` 扩为 `args_sha8 + args_head`（≤200 字符）⇒ 命令原文可核。
- 适配器新增 `prompt_sha8` + `tail_messages`（末 4 条：role/len/head/tool_calls）⇒ 台账类断言有外部真值。
- 夹具逐字节同：两侧 md5 `fe1f5530446bd4ceb8be1b944c8ec005`。

## 5. 诚实边界

- **调用数上升（9→15）**：动作环真执行工具后每步都要回灌，属「真干活」的成本；判据是产物与 KPI，不是调用数下降。
- 冷启动首调用读数受 **provider 侧跨运行前缀缓存**影响（R457 60.5% vs R456 21.6% 前缀不同）⇒ 不作为实现优劣结论。
- codex 侧为 R455 冻结读数（未重跑，避免污染基准）。
- 未 push（推送暂停令）。
