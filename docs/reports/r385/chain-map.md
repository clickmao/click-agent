# R385 主执行链阶段地图 (单轮: 用户输入 → 最终回复)

> 仓库: `/home/agentuser/AgentFramework` (C#/.NET 10)
> 方法: 只读侦察 (read_file / grep / python 逐行确认)。**每条 file:line 均为实读命中**; 未能确认者标「未找到(已扫: …)」, 不臆测。
> 关键结论: 主链路**唯一必调的模型调用是 `IndustrialAgentV2.cs:1405`**, 其余 LLM 调用点全部是**条件分支**(隔离/探索微步骤/纠正 L2/产物修复), 且隔离路径与主路径**互斥**(提前 `return`)。

---

## §1 阶段清单 (单轮主链)

| 阶段号 | 阶段名 | 入口方法 file:line | 输入 / 输出 | 是否零 token | 备注 |
|---|---|---|---|---|---|
| 1 | CLI 主循环 (REPL 入口) | `src/agent.host/Program.cs:408` (`new CliSession`), `:525` (`agent.ProcessAsync`), `:557` (`session.RenderResponse`) | 用户文本/图 → `Message` → `AgentResponse` → 控制台 | 否 (经 `ProcessAsync` 间接触发 LLM) | ① 块的"真入口"在 Program.cs 主循环; `CliSession.cs` 只是步骤记录+渲染壳 |
| 1b | CLI 会话壳 (记录/渲染) | `src/agent.host/CliSession.cs:45` (`RenderResponse`), `:42` (`RecordStep`), `:63` (`AgentOutputMessage.FromLlmAnswer`) | steps/response → 双模式渲染 | 是 (纯渲染, 无模型调用) | 交付层; 步骤明细在 `:507/:520/:526` 被写入 |
| 2 | 意图识别/拆解 (规则) | `src/agent/intent/IntentDecomposer.cs:100` (`Decompose`), `:145` (`PrimaryIntent`); 调用点 `src/agent/IndustrialAgentV2.cs:870-871`; 预览 `Program.cs:504-505` | 用户文本 → `List<SubTask>` + 主意图 | **是 (纯规则, 0 token)** | ② 拆解不调 LLM; `RecognizeIntentAsync` `V2:2478-2481` 同样规则化 |
| 3 | 续跑/检查点判定 (回退入口) | `src/agent/IndustrialAgentV2.cs:861` (`TryResumePausedPlanAsync`), 定义 `:2142`; `PlanResumeService.TryLoad` `src/agent/intent/PlanResumeService.cs:113`; `ApplyReply` `:206` | 检查点 + 本轮用户答复 → 是否答复旧计划 | 是 (读盘+规则) | ⑤ 若命中: 执行 `:2179 PlanRunner.RunAsync` 并 `:2190` 渲染后 **return**, 不走主链 |
| 4 | 隔离任务判定 (旁路) | `V2:981` (门 `subTasks.Count==1`), 执行 `:1010`/`:1039` (`IsolatedTaskRunner.ExecuteAsync`), 早退 `:1020`/`:1049` | 用户文本+目标锚 → 隔离答案 | **否 (调 LLM: `IsolatedTaskRunner.cs:83`)** | 与主链**互斥**: 命中即 `return response` |
| 5 | 证据闸门 / 澄清补充 | `V2:1056` (`RunEvidenceGateAsync`), 定义 `:2238` | 子任务 → 追加说明文本 | 是 (规则/问询, 见 §4) | 低置信才触发; 非必走 |
| 6 | 计划构建 + 本地/远程路由 | `V2:1066` (`BuildRoutedPlan`), 定义 `:2046` → `RoutedPlanBuilder.Build` `src/agent/intent/PlanRoutePolicy.cs:408`; `PlanRoutePolicy.Decide` `:171`; `LocalExecutorRegistry.ForIntent` `:90` | 子任务 → `TaskPlan` (节点位置 Local/Remote) | 是 (纯规则) | ⑥ 核心; 未接线执行器→强制 Remote (`:141-146`) |
| 7 | 本地先行执行 (真并行) | `V2:1067-1072` (`AnnounceAsync`/`NewContext`/`StartLocalFirst`); `PlanRunner.StartLocalFirst` `src/agent/intent/PlanRunner.cs:411` | 无依赖本地节点 → 后台结果 | **是 (本地执行体 0 token)** | 闸门 `PlanRunner.cs:411`→`_gate()`; `AGENTFRAMEWORK_PLAN_EXEC=0` 回退哑体 |
| 8 | 出站文本扣减 (反核减) | `V2:1211-1216`; `RequestAblation.SubtractForPlan` `src/agent/intent/RequestAblation.cs:51` | 用户原文 − 框架自做子请求 → 出站正文 | 是 (纯规则) | 扣减后模型不再重算本地步骤 (`V2:1212`) |
| 9 | 上下文装配 | `V2:1090+` → `src/agent/contextassembler/ContextAssembler.cs:239` (`PromptHeader`), 定义 `:1206` | 会话/记忆/画像/工作区 → PromptHeader 文本 | 是 (检索+拼接, 无模型) | 工作区召回 `:458`; 源名映射 `:1451-1456` |
| 10 | 缓存前缀构造 (system 冻结) | `V2:1113` (`GetSystemPrompt` → `src/agent/templates/IPromptBuilder.cs:362`), `:1124-1132` (`SessionInjectionPlanner`), `:1147-1154` (`SessionBaseline.Build`), `:1164` 冻结 | 静态块+基线 → 会话内恒定 messages[0] | 是 (字符串拼装) | ⑧ 核心, 详见 §3 |
| 11 | 会话历史全量正序回放 | `V2:1110` (`GetConversationHistoryAsync`), 定义 `:2451`, 取 `SentContent` `:2473` | session.Messages → `List<Message>` | 是 (读内存/盘) | ④ 回放: 追加式前缀, 不回退截断 |
| 12 | Prompt 组装 | `V2:1218` (`_promptBuilder.BuildWithHistory`), 定义 `IPromptBuilder.cs:188`; 内联块 `:1181-1216` | SystemPrompt+History+UserMessage → `Prompt` | 是 | `ContextPrompt` 置空 `:1225` (不再发独立 system 消息, 防切前缀) |
| 13 | 探索链 (条件) | `V2:1298` (`RunThinkChainAsync`), 定义 `:189` | URL/目录线索 → digest | 是 (HTTP 抓取, 无模型) | 开关 `AGENTFRAMEWORK_EXPLORE=0` `:192` |
| 14 | 隔离微步骤 (条件) | `V2:1301` (`RunMicroStepsAsync`), 定义 `:250`; 调用 `:272` | 每子任务 → 微答案 | **否 (每子任务 1 次 LLM)** | 仅 `ContextGateMode.IsolatedMicro` 且 `subTasks.Count>0` (`:1299`) |
| 15 | **主 LLM 调用** | `V2:1405` (`_llmCaller.CallAsync`) → `ModelQueueAdapter.CallAsync` `src/agent/modelqueue/ModelQueueAdapter.cs:46` → `ModelQueueRouter.CallAsync` `src/agent.modelqueue/ModelQueueRouter.cs:211` → HTTP `:869` | Prompt → 模型答复 | 否 | ③ 唯一必调点 |
| 16 | 输出区段路由 (后处理) | `V2:1546` (`_segmentRouter.ProcessAsync`) → `src/agent/registry/SegmentKind.cs:378`; `ResponseSegmenter.Segment` `:75`; 插件 `PythonArtifactPlugin.cs:124` | 答复原文 → 分段+插件(落盘/py_compile) | **是 (插件为本机进程, 非 LLM)** | ⑦ 前半 |
| 17 | 产物回流修复 (条件) | `V2:1550` (`_artifactRepair.RunAsync`) → `src/agent/registry/ArtifactRepair.cs:187`; 调用 `:217` | 失败产物 → (至多 1 轮)修复后正文 | **否 (仅失败时调 1 次 LLM)** | 闸门 `ArtifactRepairPolicy.IsEnabled` `ArtifactRepair.cs:183/192` |
| 18 | 计划真执行 (本地节点) | `V2:1556` (`RunPlanAsync`), 定义 `:2069`; `PlanRunner.RunAsync` `PlanRunner.cs:477` | 计划 → `TaskPlanRun` (审计) | **是 (本地执行体 0 token)** | 失败不阻断主链 (`V2:1553-1556`) |
| 19 | 检查点捕获 (续跑落盘) | `V2:2086-2087` (`CheckpointStore` + `PlanResumeService.Capture` `PlanResumeService.cs:71`) → `CheckpointStore.Save` `src/agent.recovery/ExecutionCheckpoint.cs:95` | run 状态 → `checkpoint.json` (原子写) | 是 (序列化+写盘) | ⑤ 后半; `AwaitingNodeIdOf` `PlanResumeService.cs:283` |
| 20 | 赏罚/纠正检测 (后台旁路) | `V2:1503` 门 (`GrowthLedger != null`), `:1510` 后台 `Task.Run`, `:1514` (`CorrectionDetector.JudgeAsync`), `:1516` (`DetectViaLlm`); L1 `src/agent.roles/CorrectionDetector.cs:51` | 上轮答复+本轮输入 → 赏罚信号 | **L1 是 0 token; L2 调 1 次 LLM** | 不阻塞响应; 无 Role 时整链失效 (`V2:1501-1503`) |
| 21 | 交付/渲染 | `Program.cs:557` → `CliSession.RenderResponse` `CliSession.cs:45` → `AgentOutputMessage.FromLlmAnswer` `AgentOutputMessage.cs:89` | `AgentResponse`+segments → Markdown/PlainText | 是 (纯渲染) | ⑦ 后半; `OutputFormatter.ToPlainText` `:106` |

**总计**: 21 阶段; 其中 18 个零 token 阶段, 3 个"否"(阶段 15 必调, 阶段 14/17 条件调, 阶段 4 旁路调)。逐条 token 判定见 §2/§3。

---

## §2 单轮 LLM 调用点清单

### 2.1 全部调用模型的位置

| file:line | 调用方阶段 | 目的 | 是否可折叠进同一次调用 | 证据 |
|---|---|---|---|---|
| `src/agent/IndustrialAgentV2.cs:1405` | 15 主链 | 主答复生成 (唯一必调) | — (基准) | `var llmResponse = await _llmCaller.CallAsync(prompt, ct);` |
| `src/agent/IndustrialAgentV2.cs:146` | 20 L2 纠正 | 微 prompt 三分类 CORRECTION/ADOPT/NEUTRAL (~120tok) | **可省/可折叠**: 后台独立微 prompt, 与主答复无语义依赖; L1 规则已覆盖高信场景 | `DetectViaLlm` 定义 `:144`, 经 `:1516` 传入 `CorrectionDetector.JudgeAsync`; L1 `CorrectionDetector.cs:51` 命中则不调 |
| `src/agent/IndustrialAgentV2.cs:272` | 14 微步骤 | 逐子任务隔离问询 (per-subtask) | **可合并**: 同轮 N 个子任务 = N 次调用, prompt 仅微问题、上下文空 (`:260`), 可合并为 1 次批量问询 | `await _llmCaller.CallAsync(microPrompt, ct);` 在 `foreach (var st in subTasks)` `:254` 内 |
| `src/agent/registry/ArtifactRepair.cs:217` | 17 修复 | 机器校验失败 → 回灌失败事实 → 有界修复 1 轮 | **条件可省**: 仅当 `DrainArtifactChecks` 存在可修复失败 (`:195`) 且闸门开 (`:192`) | `resp = await _caller.CallAsync(prompt, ct)` (`_caller` = `ILLMCaller`) |
| `src/agent/subagent/IsolatedTaskRunner.cs:83` | 4 隔离 (旁路) | 隔离任务独立作答 (绕过 V2 会话状态) | **与主链互斥**, 不可折叠 (命中即 `V2:1020/1049 return`) | `var resp = await _llm.CallAsync(prompt, ct);` |
| `src/agent/IndustrialAgentV2.cs:2757` | 备用 ILLMCaller | `OpenAILLMCaller` 直连实现 | 仅当 DI 将 `ILLMCaller` 绑到 `OpenAILLMCaller` 时; 默认绑 `ModelQueueAdapter` | 注册 `src/agent/extensions/ServiceCollectionExtensions.cs:276-277`; `NullLLMCaller :2883/:2885` 为兜底 |
| `src/agent.modelqueue/ModelQueueRouter.cs:869` | 15 内层 HTTP | 真正的一次 HTTP POST 发送 | 单次 `CallAsync` 内可能多次进入 (重试/备份/恢复) | `using var resp = await client.SendAsync(http, ct);` |

**ModelQueueRouter 内部重发点 (逻辑 1 次调用, HTTP 可能多发)**:
- `ModelQueueRouter.cs:296` 首次 `CallEntryAsync` (firstBudget)
- `:430` 重试 `CallEntryAsync` (retried)
- `:496` 备份模型 `CallEntryAsync` (backupResp)
- `:694` 空内容恢复重发 `CallEntryAsync`
- `:791` 截断恢复重发 `CallEntryAsync`

→ `ModelQueueAdapter.CallAsync` (`:46`) 一次调用, 底层 HTTP 发送**最多 5 次** (互斥/接力触发)。

### 2.2 单轮最少/最多 LLM 调用次数推导

**分支关系 (标注互斥)**:
- 阶段 3 (续跑命中) 与阶段 4/15 **互斥** — 续跑命中 `PlanResumeService` 后 `V2:2190` 直接渲染; 隔离命中 `V2:1020/1049` 直接 `return`。
- 阶段 4 (隔离) 与阶段 15 (主链) **互斥**; 阶段 4 前置 `subTasks.Count==1` (`V2:981`) 且需目标锚 `goal != null && goalEntities.Count>0` (`:993`)。
- 阶段 14 (微步骤) 与阶段 15 **不互斥** — 微步骤在 `V2:1301` 先跑, 主链 `:1405` 后跑。
- 阶段 20 L2 与阶段 15 **不互斥** — 后台 `Task.Run` (`:1510`), 不阻塞主链。
- 阶段 17 修复依主链成功后产物校验结论触发 (`V2:1545-1550`), 与主链**同轮叠加**。

**推导**:
- **最少 = 1 次**: 走主链 (`:1405`), 无隔离/无 IsolatedMicro/`GrowthLedger==null` 或 L1 命中/产物全通过或不可修复。隔离/修复/微步骤/纠正 L2 全不触发。
- **最多 = 1 (主) + N (微步骤) + 1 (纠正 L2) + 1 (产物修复) = N + 3 次** (N = 子任务数, 仅 `ContextGateMode.IsolatedMicro` 时微步骤才逐条调用)。若走隔离旁路, 则为 **1 次 (`IsolatedTaskRunner.cs:83`)**, 不叠加主链。
- **HTTP 层面额外**: 单次逻辑调用内 `ModelQueueRouter` 最多 5 次发送 (`:296/:430/:496/:694/:791`), 属恢复语义, 理论上限 `(N+3)×5` 次 HTTP, 实际由分支条件大幅收窄 (重试/备份/恢复互斥/接力)。

---

## §3 零 token 环节与缓存前缀

### 3.1 零 token 环节

| 环节 | file:line | 零 token 判据 | 是否在稳定前缀内 |
|---|---|---|---|
| 意图拆解 (规则) | `IntentDecomposer.cs:100` (`Decompose`), `:145` (`PrimaryIntent`); `V2:2478-2481` (`RecognizeIntentAsync`) | 词界匹配, 无网络/无模型 | 否 (产出子任务, 不进 messages) |
| 会话静态块切分 | `SessionInjectionPlanner.cs:112` (`Split`), `:103` (`IsSessionStatic`) | 纯字符串按 `[` 切块+白名单判定 | **是** (静态块进 messages[0]) |
| 跨轮行级去重 | `SessionInjectionPlanner.cs:152` (`Dedupe`) | trigram Jaccard + 哈希账本, 无模型 | 部分 (去重后动态块进 user 尾部) |
| 会话基线 | `SessionBaseline.cs:23` (`Build`) | 工作区/运行时信息字符串拼装 | **是** (进 messages[0], `V2:1148`) |
| 会话历史回放 | `V2:2451-2475` (`GetConversationHistoryAsync`) | 读 `SentContent`, 全量正序 | **是** (历史段, 追加式) |
| 缓存前缀不变式机检 | `ModelQueueRouter.cs:901` (`BuildMessages`) | 离线可消费, 无需网络; `:819` 前缀分歧点定位 | 定义前缀装配 (system→history→user) |
| 缓存 KPI 归因 | `ModelQueueRouter.cs:321-332`, `:350-369` | 读用字计数, 无额外调用 | 否 (观测) |
| 本地/远程路由裁定 | `PlanRoutePolicy.cs:171` (`Decide`), `:90` (`ForIntent`), `:408` (`Build`) | 登记表查表, 未接线→Remote | 否 (计划层) |
| 运行时依赖扫描 | `RuntimeDependencyScanner.cs:33` (`FindProducer`), `:92` (`ScanPlaceholder`) | 文本/占位符扫描 | 否 |
| 出站扣减 | `RequestAblation.cs:51` (`SubtractForPlan`) | 原文片段删除, 纯文本 | 影响 user 段字节 (`V2:1212`) |
| 本地节点执行 | `PlanRunner.cs:411` (`StartLocalFirst`), `:477` (`RunAsync`) | 执行体为本地命令/文本处理, 无模型 | 否 |
| 区段切分+插件路由 | `SegmentKind.cs:75` (`Segment`), `:378` (`ProcessAsync`) | 正则分段; 插件 | 否 (后处理) |
| PY 落盘 + 机器校验 | `PythonArtifactPlugin.cs:124` (`HandleAsync`), `:107` (`DrainNewChecks`), 注释 `:53` | 真实 `python3 -m py_compile` 子进程, 非 LLM 自证 | 否 |
| 产物校验聚合 (取即清) | `SegmentKind.cs:364` (`DrainArtifactChecks`) | 汇合插件结论, 无模型 | 否 |
| 纠正规则层 L1 | `CorrectionDetector.cs:51` (`RuleJudge`) | 词表+语境豁免, 命中即结算不开 L2 | 否 |
| 检查点写/读/恢复裁定 | `ExecutionCheckpoint.cs:95` (`Save`), `:109` (`Load`), `:170` (`BuildRecoveryPlan`) | JSON 序列化+原子写+规则裁定 | 否 |
| 续跑捕获/装载/答复落地 | `PlanResumeService.cs:71` (`Capture`), `:113` (`TryLoad`), `:206` (`ApplyReply`) | 检查点比对+参数槽落位, 无模型 | 否 |
| CLI 渲染 | `CliSession.cs:45`/`:63`; `AgentOutputMessage.cs:89`/`:106` | 格式转换, 无 IO 模型 | 否 |
| 探索链抓取 | `V2:189` (`RunThinkChainAsync`) | HTTP 抓取 + 正则 seed, 无模型 | 否 (digest 进 user 尾部 `V2:1298`) |

### 3.2 静态前缀按顺序包含哪些段 (缓存前缀构造)

主链在 `V2:1113-1154` 装配、`ModelQueueRouter.cs:901` (`BuildMessages`) 最终成形。顺序契约见 `ModelQueueRouter.cs:895-899` 注释: `system(会话内恒定) → context(system,本轮) → history(追加式全量回放) → user(本轮) → [extraSystemSuffix]`。

| 段 | 内容 | 构造 file:line | 是否静态 |
|---|---|---|---|
| ① messages[0] = system 冻结体 | `IntentPromptTemplates.GetSystemPrompt(intent)` + `\n\n` + `SessionBaseline.Build(工作区)` + `\n[会话静态上下文]\n` + 静态块文本 | `V2:1113` (`IPromptBuilder.cs:362`), `V2:1147` (`SessionBaseline.cs:23`), `V2:1148-1149`, 冻结 `:1164`; 组装 `ModelQueueRouter.cs:903` | **是** (会话内恒定; 意图漂移只追加到 user `V2:1155-1159`) |
| ② 静态块 (白名单) | `[AgentContext] [Agent 画像] [可用能力] [User Preference] [Workspace Files/工作区文件]` | 白名单 `SessionInjectionPlanner.cs:20-23`; 过滤 `V2:1124-1132` | **是** (仅会话首轮入前缀 `V2:1144`) |
| ③ context system 消息 | `prompt.ContextPrompt` | `ModelQueueRouter.cs:905-909` | 主链**置空** (`V2:1225`) → 实为空 |
| ④ history | 全量正序回放的 `SentContent` | `V2:1110` → `:2451-2475` → `IPromptBuilder.cs:188` → `ModelQueueRouter.cs:911` | 追加式 (只增不改) |
| ⑤ user (本轮) | 出站正文(扣减后) + `[本轮参考上下文]` (意图提示/下轮预估/技能知识/去重后动态块) | `V2:1211-1216` (`sentUserContent`); 内联块来源 `:1181-1209` | 否 (每轮新增, 追加区) |
| ⑥ extraSystemSuffix | 仅特定分支传入 | `ModelQueueRouter.cs:840/901` | 否 (末尾追加, 注释 `:898` 警告不得前置) |

控制点: 冻结表 `V2:1141-1153`; 意图漂移拦截 `V2:1155-1163` (打点 `cache_prefix_guard`); 无会话则静态块尾部下发 `V2:1166-1170`。

---

## §4 验证与自检闸门 + 回退开关

| 闸门/开关 | file:line | 触发条件 | 失败后果 |
|---|---|---|---|
| 探索链总开关 `AGENTFRAMEWORK_EXPLORE` | `V2:192` | 值 == `"0"` → 直接返回空 | 探索链全关 (对照组语义), 主链不受影响 |
| 计划执行闸门 `AGENTFRAMEWORK_PLAN_EXEC` | `PlanRunner.cs:308` (`EnableEnvName`), `:312` (`_gate`), `:329` (`IsEnabled`) | 值 `0/false/off` | 回退哑体 (`StartLocalFirst` 返回 null `:413`; `RunAsync` 用哑执行体) |
| Python 运行验证闸门 `AGENTFRAMEWORK_PY_RUN` | `PlanRunner.cs:39-40`, `:88` | 未开 → 不跑真 PY | 本地 PY 校验降级 |
| 产物回流修复闸门 | `ArtifactRepair.cs:183` (`IsEnabled`), `:192` | `!gate()` | 不修复, 保留原文并记 `fixed=false` (`:252`) |
| 隔离任务前置门 | `V2:981`, `:993` | `_isolatedTaskRunner != null && subTasks.Count==1` 且目标锚非空 | 不隔离, 落回主链 |
| 微步骤前置门 | `V2:1299` | `gateVerdict.Mode == IsolatedMicro && subTasks.Count>0` | 不跑微步骤, 主链单次调用 |
| 赏罚链门 (无 Role 失效) | `V2:1501-1503` | `GrowthLedger is null` | 不起后台 Task / 不调 LLM / 不写失败簇 |
| 续跑拒绝闸门 (8 条常量) | `PlanResumeService.cs:58-65` | 缺检查点/缺蓝图快照/终态/非等待/无参数槽/多条目/选项不符/缺产出 | **如实拒绝, 不猜测重建** (失败不续跑, 走新任务) |
| 恢复裁定 | `ExecutionCheckpoint.cs:168-196` (`CheckpointRecovery`) | 仅 Pending/Running/Retrying 可恢复 | Succeeded 跳过; Failed/Cancelled 重跑 |
| 上下文装配失败降级 | `V2:1102-1107` | `!contextResult.Success` | 记 warning, 无上下文继续 (`continuing without context`) |
| LLM 失败降级 | `V2:1535-1542` | `!llmResponse.Success` | 内容置空 + `Error` 透传 + `AgentState.Ready` (LLM 失败≠Agent 故障) |
| 本地节点失败不阻断 | `V2:1553-1556` | 本地 plan 执行异常 | 结论只作审计/证据, 不阻断主链 |
| 缓存命中红线闸门 (95%→97%, R394) | `ModelQueueRouter.cs:350-369` | `PromptCacheRedline.Threshold` 越线 | 落盘诊断 + 响亮告警 (`:362/:366-369`), 不改请求 |
| 静态块去重上界 | `SessionInjectionPlanner.cs:32` (`MaxTrackedLines=20000`) | 账本超界 | 清空账本 (防无界增长) |
| 冻结 system 表上界 | `V2:1141` | `_frozenSystemPrompt.Count > 512` | 清表 (防长驻进程无界增长) |

**未找到 (已扫)**: 无。⑧ 块静态前缀构造已在 `V2:1113-1154` + `ModelQueueRouter.cs:895-909` 找到完整代码; 未出现需要标「未找到」的条目。

---

## 附: 证据强度说明

- 本文件所有 `file:line` 均来自本轮实读 (read_file / python 逐行 / grep -n)。
- 行号会随代码演进漂移; 引用的锚点字符串 (方法名/常量/注释) 一并给出, 便于重定位。
- 模型调用"次数"区分三层: 逻辑调用 (业务语义) → `ModelQueueRouter` 内层重发 (恢复语义, 最多 5 次) → HTTP 请求 (真 token 消耗)。三者不等价, 见 §2.1/§2.2。
