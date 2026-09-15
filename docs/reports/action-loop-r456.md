# R456 报告 —— 动作环（Action Loop）实施 + E2E 实测

- 状态: 已收口（R456, 2026-09-15）
- 计划: `docs/plans/v0.76.0-r456-action-loop.md`
- 前序: R455 机制诊断 `docs/reports/agent-chain-diagnosis-r455.md`（**管道无动作环**）
- 判据: 同环境/同输入/同模型（deepseek-flash）模块覆盖套件；我方仅改二进制与动作环开关

## 1. 机制修复（源码事实）
| 面 | 实现 | 位置 |
|---|---|---|
| 声明面 | `ActionToolDecl.ToolsJson`（list_dir / read_file / write_file / run_command，静态常量手写 JSON） | `src/agent.modelqueue/ActionLoop.cs` |
| 解析面 | source-gen DTO `tool_calls` + `finish_reason` → `QueueResponse.ToolCalls` | `OpenAIChatResponseDtos.cs` / `ModelQueueRouter.CallEntryAsync` |
| 回灌面 | `QueuePrompt.PostUser`（追加在 messages 尾部；system/context/history/user 前缀逐字节不变） | `ModelQueueRouter.BuildMessages` / `SerializeChatRequest` |
| 执行面 | `WorkspaceActionPort`（工作区根约束、越界即拒、8 KB 输出上限、120 s 超时、进程树回收、UTF8 无 BOM 审计） | `src/agent/action/WorkspaceActionPort.cs` |
| 接线 | `ModelQueueAdapter`：`AGENTFRAMEWORK_ACTION_LOOP != off` 且注入 IActionPort 时启用（≤6 步） | `ModelQueueAdapter.cs` / `ServiceCollectionExtensions.cs` |

## 2. 器具缺陷（本轮捕获 → 修复 → 复验）
- `eval/rover/r455/adapter_tools.py::to_chat_tools` 只识别 Responses 风工具声明（`{type,name,parameters}`），**静默丢弃** chat 风（`{type,function:{...}}`）⇒ 首轮烟测显示 `tool_calls=null`，属器具假阴性（器具镐铁律：不符即 VOID，不得下结论）。
- 修复后烟测（同一声明，A 经适配器 / B 直连上游）：两侧 `finish_reason=tool_calls`，返回 `run_command` 调用 ⇒ **模型侧工具调用能力成立**，此前判断被推翻。

## 3. E2E 读数（`eval/rover/r456/run_agent_tools.sh` + `judge_r456.py`）
同夹具（两侧 md5 同源）/同 6 轮输入/同模型/零重试。

| 指标 | R455（无动作环） | **R456（动作环 on）** | codex 0.154（冻结） |
|---|---|---|---|
| 产物达成 | 0/4 | **2/4** | 4/4 |
| count.txt | 不存在 | **`4`** ✅ | `4` ✅ |
| merged.txt | 不存在 | **ALPHA/BETA/GAMMA** ✅ | 同 ✅ |
| stats.txt / first.txt | 不存在 | 缺（见 §4） | `chars=14` / `R455 fixture note` ✅ |
| 工具执行次数（审计） | 0 | **4**（run_command×3 / write_file×1） | ~8 命令 |
| 上游调用 | 7 | 9 | 13 |
| prompt token（∑） | 18,039 | 31,537 | 91,002 |
| 缓存命中 | 86.6% | 84.8% | 96.6% |
| completion（∑） | 957 | 575 | 597 |
| 轮内问询 | 1/6（+4 处伪造「已完成」） | **1/6（无伪造）** | 0/6 |

- 我方 T1 回复（工具真实回灌后）：「当前目录下共有 **4** 个 .py 文件：a.py、b.py、c.py、d.py」+「计数结论由 find 实际输出直接得出」⇒ R455 的**伪造执行记录已消失**（此前 T2 谎称「已完成 count.txt 写入」而磁盘为空）。

## 4. 残余缺口（下一轮候选，机制层）
1. **T4 未落盘 + 算错**：模型读了 merged.txt（有工具步），随后**在文本里口算** `chars=15`（真值 14）并宣称「已写入 stats.txt」——产物不存在。缺口 = 工具结果回灌后缺少「必须落盘」的收口约束（属工具描述/声明层，非关键字补丁）。
2. **T5/T6 被吞并入口吞掉**：`继续` → 澄清问句；T6 → 「答复不在该条目可选范围内…该续跑入口已作废」。可执行任务在**吞并/续跑判定**处被吃 ⇒ 与 R453「吞并轮 13.7%」同源，需在吞并前做可执行性判定。
3. **缺 key 静默空回复**：首跑（未 `. .env.local`）6 轮全 `reply_len=0`、0.04 s、零上游调用、无任何告警日志 ⇒ 远端通道不可用时**静默降级为空回复**（健壮性缺陷，须留告警）。

## 5. 诚实边界
- 两侧静态面/工具面仍不同源（codex instructions 16,979 字符 + 9 工具）；token 对比只作方向参考，不作「谁更省」结论。
- codex 侧沙箱仍为 bypass（本机 bwrap 不可用）⇒ 其读数含便利性偏差。
- 我方 2/4 产物是**单次**运行读数（无重复）；`stats.txt`/`first.txt` 缺口有明确证据链（§4）。
- 缓存 84.8% < R455 的 86.6%：前缀变长（PostUser 回灌）后首步仍全量；K2b ≥97% 红线是**长会话**口径，本轮 6 轮短会话不适用。
