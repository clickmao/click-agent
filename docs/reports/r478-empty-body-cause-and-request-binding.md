# R478 · 空正文定因机制化（finish_reason 判据）+ 请求-轮次因果绑定 + 命中率冷/稳态分列

- 状态: 已完成（验收 1/2/4/5 达成；验收 3 真机 E2E 因起手闸 MemAvailable 2293 MB < 2650 MB 未过，转入下轮候选）
- 轮号: R478（承 R477 `1ca64c0`）
- 计划: `docs/plans/v0.94.0-r478-empty-body-cause-and-request-binding.md`
- 预注册: `eval/rover/r478/prereg_r478.json`（**晚于焦点单测首跑**落盘 ⇒ 描述性数字入 `checks_posthoc`，承 R453）
- 器具: `eval/rover/r478/check_r478.py`（判据 C1–C7 + 负控 NC1–NC3）、`eval/rover/r478/band_reestimate_r477.py`（R456b 分列）
- 结论: `verdict-r478.json` = **PASS 7/7 + NC 3/3**；全量单测 **1469/1469 ×3**；AOT `499a7552897992f1`

## 因果链

1. **R477 真机事实**：20/20 空正文调用的上游 `finish_reason == tool_calls`，`max_tokens == None`（**非**预算截断），`reasoning_tokens_max` 395/122 ≪ 预算 ⇒ 产品徽标「推理过程占满了输出预算」是**误诊**，并且**白跑一次 32k 预算的重试**（调用数 + token 双浪费）。
2. **R477 事后判据 P4**：5 条 `llm_call.ts` 落在所记轮次窗口之外 ⇒ 轮次归属只能靠时间窗猜。
3. **R477 读数**：R 臂命中率 0.791 < Arole 0.858 ⇒ 需按 R456b 分列冷启动/稳态，才能判断是机制退化还是口径伪影。
4. ⇒ R478 三件事：**定因取协议字段**、**request_id 因果绑定**、**命中率分列重估**。

## 本轮产出（文件 / 命令 / 读数）

| 面 | 文件 / 命令 | 读数 |
|---|---|---|
| 定因机制 | `src/agent.modelqueue/EmptyBodyDiagnosis.cs`（`Classify`/`Banner`/`Retryable`/`RoutableToActionLoop`） | `ToolCall`/`LengthExhausted`/`UpstreamStop`/`Unknown`；判据字面量 ⊆ {`tool_calls`,`length`,`stop`} |
| 调用面接线 | `ModelQueueRouter.cs`（空正文分支 + `RecoverFromEmptyContentAsync`）、`ModelQueueAdapter.cs` | `retry_skipped=true` ×2；`ToolCall` 因**不重试**；`ResponseId = r.RequestId` 透传 |
| 链侧绑定 | `src/agent/IndustrialAgentV2.cs` | `_replyRequestId` 捕获 + 逐轮清零；`loop_turn` 打点带 `request_id` |
| 动作环出口 | `src/agent.modelqueue/ActionLoop.cs` | 出口空正文 ⇒ 单源 `Banner(` + `ContentIsUserFacing = true`，**禁静默空回复** |
| 单测 | `src/agent.tests/EmptyBodyDiagnosisTests.cs`（新增）+ `ActionLoopTests`/`UserFacingFailureTests`/`R475AccountingTests` | 焦点 **30/30 → 43/43**；全量 **1469/1469 ×3** |
| 器具 | `python3 eval/rover/r478/check_r478.py`；`python3 eval/rover/r478/band_reestimate_r477.py` | `PASS 7/7`、`NC 3/3`；`rc=0` |
| AOT | `/tmp/pub_r478b/agenthost` | 15,363,712 B / sha16 `499a7552897992f1` / IL 0 / `env -i --version` rc=0 |

## 判据结果（预注册 C1–C7）

| 判据 | 内容 | 结果 |
|---|---|---|
| C1 | 定因只取协议字段（`Classify` 体内 0 个用户文本关键词；字面量 ⊆ 协议集） | **pass** |
| C2 | 用户可见文案单源（**产品面** `Banner(` 调用点 3 处：`ActionLoop.cs:243` / `ModelQueueRouter.cs:736`（空正文）/ `:1217`（恢复通告）；旧误诊文案 0 处作为发文案） | **pass** |
| C3 | `ToolCall` 因不重试（`retry_skipped=true` ×2；恢复路径被 `LengthExhausted ∨ reasoning 非空` 守卫） | **pass** |
| C4 | 因果绑定（8 个源码派生断言的合取：签发/赋值/透传/两侧遥测/捕获/清零） | **pass** |
| C5 | 动作环出口可见（`action_loop_empty_content` 等守卫 + 单源文案 + `ContentIsUserFacing`） | **pass** |
| C6 | 全量单测 ×3 全绿（缺日志 = VOID，不静默通过） | **pass** |
| C7 | AOT（发布日志 IL 警告 0 ∧ 二进制存在） | **pass** |
| NC1 | 旧误诊文案若作为发文案出现 ⇒ C2 判红 | **ncOK** |
| NC2 | 关键词驱动分类器 ⇒ C1 判红 | **ncOK** |
| NC3 | adapter 未透传 `ResponseId` ⇒ C4 判红 | **ncOK** |

## 对比数据（R477 真机 usage，供应商 usage 真值；器具 `band_reestimate_r477.py`）

| 口径 | Arole（门关） | R（门控） | 差 |
|---|---|---|---|
| 调用数（有 usage） | 21 | 10 | −11 |
| **稳态**（rate ≥ 0.5） | **0.919019**（19 调用 / 62,397 prompt） | **0.914939**（8 调用 / 29,379 prompt） | **−0.41pp** |
| 冷启动（rate < 0.5） | 0.215779（2 调用，占比 **9.5%**） | 0.205755（2 调用，占比 **20.0%**） | +10.5pp 占比 |
| 聚合（全部调用） | 0.857967 | 0.791011 | −6.70pp |

- 恒等式 `prompt_cache_hit_tokens + prompt_cache_miss_tokens == prompt_tokens` **逐行成立 21/21 + 10/10**。
- **结论**：聚合差 −6.70pp 中 **−6.29pp 由冷启动窗口占比差解释**；稳态两臂近等 ⇒ **聚合口径不可用作机制结论**（R456b）。
- **分档轴诚实性**：该夹具每轮 `prompt` 均落 `201+` 档 ⇒ `band_note.degenerate=true`；正确轴是**用户轮 token**（R477 未落盘）⇒ 本轮**不冒充分档结论**。

## 诚实边界

1. **无真机 E2E**：起手闸 `MemAvailable ≥ 2650 MB` 未达（实测 2293 MB）⇒ 本轮机侧禁起真机测量；定因机制只经**源码派生 + 单测**背书。
2. **真机 join 未验**：`request_id` 因果绑定只证**机制存在**，未在真机遥测上按 id 对齐（本轮无真机轮）。
3. **分档轴退化**：`band_degenerate=true`，分档结论待用户轮 token 分量落盘后重做。
4. **预注册晚于首跑**：焦点单测首跑 30/30 早于 `prereg_r478.json` 落盘 ⇒ 描述性数字入 `checks_posthoc`（承 R453），不追溯粉饰。
5. **上游语义未裁**：`tool_calls` 是否该由本链路执行工具属产品策略，本轮只做到「诚实报因 + 不浪费重试 + 保留动作环通路」。

## 下轮候选

1. 真机 E2E（待 `MemAvailable ≥ 2650 MB`）：复测 `empty_cause` / `retry_skipped` 实发分布 + `request_id` 真机 join。
2. 门控扩面到低风险实质轮（需先出设计：哪些轮算低风险、质量对照怎么判）。
3. 上游 `tool_calls` 语义裁决（是否由本链路执行工具）—— 待用户裁定。
4. 提交纪律：核对 staged == 本轮 artifact 清单，**拒整树 add**（Q27 跨写者事故）。
