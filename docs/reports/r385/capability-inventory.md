# R385 — 当前 Agent 能力清单 (机器可核证据)

- 仓库: `/home/agentuser/AgentFramework`
- 快照: branch `main` @ commit `45a60c9` (提交时间 2026-09-13T18:28:39+08:00)；采集时间 2026-09-13 19:0x +08:00
- 规模: `src/**/*.cs` 排除 obj/bin = **356** 个文件；`public` 顶层类型声明 = **821** 个
- 方法: 只读侦察。全部证据为 `file:line`；行号取自采集时工作区 (未 commit 的改动可能使行号漂移)。
- 计数口径: 「定义处」= 声明行；「注册处」= DI/装配/枚举登记点；「消费方」= 至少一处非定义文件的引用行。
- ⚠ 零消费方扫描为**文本整词**启发式 (排除定义文件自身)，对以下类别会误报，逐条判读时须扣除：
  - 扩展方法宿主类 (如 `ServiceCollectionExtensions`，调用点是 `services.AddAgentFramework()`，类名不出现)；
  - 纯序列化 DTO (仅在本文件内构造并交给 STJ 输出)；
  - 仅由 `using static` 引用其成员的枚举。

---

## 1. CapabilityPlugin 注册面 (能力 id 枚举)

| 名称 | 契约/类型 | 定义 file:line | 注册/装配 file:line | 消费方 file:line | 职责 |
|---|---|---|---|---|---|
| `ICapabilityPlugin` | 接口 | `src/agent/registry/CapabilityPlugin.cs:14` | 未找到(已扫: `AddSingleton<…ICapabilityPlugin>` 全 src) | 未找到(已扫: `ICapabilityPlugin` 全 src；仅 `src/agent.tests/RegistryTests.cs` FakeCapabilityPlugin) | 第三方能力插件契约 |
| `ICapabilityPlugin.ProvidedCapabilities` | 契约成员 | `src/agent/registry/CapabilityPlugin.cs:23` | — | 同上 | 插件自报能力 id 列表 |
| `CapabilityPluginRegistry` | 注册表 | `src/agent/registry/CapabilityPlugin.cs:54` (枚举 `Names()` :60 / `Register()` :70 / `ExecuteAsync()` :92) | 未找到(已扫: `CapabilityPluginRegistry` 全 src；仅测试 `RegistryTests.cs`) | 仅测试 | 运行时登记并枚举能力 id |
| **生产插件注册数 = 0** | — | — | 未找到(已扫: `ICapabilityPlugin` / `CapabilityPluginRegistry` / `.Register(` 全 src 356 文件) | — | 注册表在生产装配中**枚举不到任何能力 id** |
| `CapabilityScanner` (实际能力面) | 宿主工具枚举 | `src/agent/registry/CapabilityScanner.cs:13`；内建 id `DesiredTools` = `git`,`dotnet`,`curl`,`python3`,`vulkaninfo` @ `:22`；`Scan()` :24；`Count` :54；`Snapshot()` :57；`RenderForPrompt()` :65 | `src/agent.host/Program.cs:414` | `src/agent/IndustrialAgentV2.cs:128,433`；`src/agent/contextassembler/ContextAssembler.cs:160`；`src/agent/registry/PanelData.cs:17,26` | 走 PATH 探测 5 项宿主工具能力 (第①通道) |
| 显式注册通道 (文档承诺) | — | `src/agent/registry/CapabilityScanner.cs:33` (注释「显式注册」) | 未找到(已扫: `RegisterCapability` 全 src) | — | ⚠ 注释承诺的「显式注册」方法**不存在**，仅 PATH 探测通道已实现 |
| `PanelDataService` (/status capabilities) | 面板服务 | `src/agent/registry/PanelData.cs:12` | `src/agent.host/Program.cs:410` | `Program.cs:410` | 输出 capabilities 面板 |
| `CapabilityEntry` | DTO | `src/agent/registry/PanelData.cs:253` | 未找到 | 零消费方 (仅本文件序列化载荷) | 面板能力条目 |

**结论 (1)**: CapabilityPlugin 注册表存在于 `CapabilityPlugin.cs`，但**生产装配零注册、零消费**；注册表枚举到的能力 id 集合 = ∅。生产实际能力枚举走 `CapabilityScanner`（5 项宿主工具）。

## 2. 响应区段插件面

| 名称 | 契约/类型 | 定义 file:line | 注册/装配 file:line | 消费方 file:line | 职责 |
|---|---|---|---|---|---|
| `SegmentKind` | 枚举 (3 值) | `src/agent/registry/SegmentKind.cs:6`；`PlainText` :9 / `Code` :12 / `InlineCode` :15 | — | `SegmentKind.cs:315,326` (`ResponseSegmenter`)；`UiCapturePlugin.cs:13,48`；`PythonArtifactPlugin.cs` | 回复区段分类 |
| `ResponseSegment` | 类 | `src/agent/registry/SegmentKind.cs:22` (`Kind` :24 / `Content` :27) | — | `SegmentKind.cs:67` (`ResponseSegmenter`)、:22 全仓 | 单段文本 + 类型 |
| `IResponseSegmentPlugin` | 接口 | `src/agent/registry/SegmentKind.cs:48` (`Name` :51 / `Consumes` :54 / `HandleAsync` :60) | `src/agent/extensions/ServiceCollectionExtensions.cs:164-168` | `IndustrialAgentV2.cs:71,369` | 区段后处理器契约 |
| `ResponseSegmentRouter` | 路由器 | `src/agent/registry/SegmentKind.cs:337` (ctor :342；内部调用 `ResponseSegmenter.Segment` :380) | `ServiceCollectionExtensions.cs:164-168` (工厂 :167) | `src/agent/IndustrialAgentV2.cs:71,369,1549`；`src/agent/registry/ArtifactRepair.cs:174,178`(测试态)；`Program.cs:531` (`ResponseSegmenter.Segment`) | 按 `Consumes` 分派插件 |
| `ResponseSegmenter` | 切分器 | `src/agent/registry/SegmentKind.cs:67` | `ServiceCollectionExtensions.cs:163` | `ResponseSegmentRouter` | 文本 → 区段流 |
| `UiCapturePlugin` (impl #1) | IResponseSegmentPlugin | `src/agent/registry/UiCapturePlugin.cs:9` (`Name="ui-capture"` :11 / `Consumes={Code}` :13 / `HandleAsync` :16) | `ServiceCollectionExtensions.cs:148` | DI→Router | 捕获界面代码区段 |
| `CodeReviewPlugin` (impl #2) | IResponseSegmentPlugin | `src/agent/registry/UiCapturePlugin.cs:37` (`Name="code-review"` :46 / `Consumes={Code}` :48) | `ServiceCollectionExtensions.cs:149` | DI→Router | 代码区段审查标注 |
| `PythonArtifactPlugin` (impl #3) | IResponseSegmentPlugin + `IArtifactCheckSource` | `src/agent/registry/PythonArtifactPlugin.cs:63` | `ServiceCollectionExtensions.cs:152` | `ServiceCollectionExtensions.cs:156,162`；`Program.cs:523`；`src/agent/intent/PlanRunner.cs:311,317` | Python 产物校验区段 |
| `PythonArtifactLedger` | 账本 | `src/agent/registry/PythonArtifactPlugin.cs:37` | `ServiceCollectionExtensions.cs:151` | `ServiceCollectionExtensions.cs:156,162`；`Program.cs:523`；`PlanRunner.cs:311,317` | 产物→run 关联 |
| `ArtifactRepairLoop` (区段消费) | 修复环 | `src/agent/registry/ArtifactRepair.cs:174` | 未找到(生产) | 零消费方 (仅 `src/agent.tests/ArtifactRepairTests.cs`) | 产物修复 (测试态) |

**结论 (2)**: `IResponseSegmentPlugin` 生产实现 **3 个**，全部在 `ServiceCollectionExtensions.cs:148-158` 显式注册；`SegmentKind` 全部取值 **3 个**。

## 3. 意图 / 计划节点类型 (PlanNode 全部 kind + 逐节点执行体)

> **事实**: `PlanNode` **没有独立的 `Kind` 枚举**。节点「种类」由 1 个字符串意图 + 5 个枚举共同表达，逐节点执行体由 `Location`/`LocalExecutorId` 选择。证据: `src/agent/intent/TaskPlan.cs:71` (无 Kind 字段，字段清单 :74-125)；`src/agent/intent/TaskPlan.cs:82` `Intent`；`:122` `Location`；`:125` `LocalExecutorId`。

| 名称 | 契约/类型 | 定义 file:line | 注册/装配 file:line | 消费方 file:line | 职责 |
|---|---|---|---|---|---|
| `PlanNode` | 类 | `src/agent/intent/TaskPlan.cs:71` (Intent :82 / Location :122 / LocalExecutorId :125 / ConfidenceFlags :117) | 由 `TaskPlanBuilder` 构造 | `src/agent/intent/PlanRunner.cs`、`PlanRoutePolicy`、`PlanResumeService` | 计划节点 = 一个子任务 |
| `TaskPlan` | 类 | `src/agent/intent/TaskPlan.cs:8` | — | 计划执行链 | 节点 DAG 容器 |
| `IntentRecognizer.Intents` (节点 kind 主集合) | 字符串常量 (9 值) | `src/agent/intent/IntentRecognizer.cs:19-27`: CodeGeneration, CodeModification, CodeReview, TestGeneration, Search, FileOperation, GitOperation, MemorySearch, General (`KnownIntents` :31) | `TaskPlan.cs:82` 默认 General | `TaskPlan.cs:82`；IntentDecomposer；PlanRunner | 节点意图分类 |
| `PlanNodeIntents` (框架本地 kind, 2 值) | 字符串常量 | `src/agent/intent/PlanRoutePolicy.cs:13` = `verify_local`；`:16` = `text_processing` | `PlanRoutePolicy` | `PlanRoutePolicy`；本地执行器 | 本地优先专用节点意图 |
| `NodeExecutionLocation` | 枚举 (3 值) | `src/agent/intent/TaskPlan.cs:58` (Remote / Local / Hybrid) | 由 `PlanRoutePolicy.Decide` 写回 (`PlanRoutePolicy.cs:148`) | `TaskPlanRun.cs`、`PlanRunner.cs` | 节点执行位置 (确定性判定) |
| `PlanNodeState` | 枚举 (8 值) | `src/agent/intent/TaskPlanRun.cs:154` (Pending, Waiting, AwaitingClarification, AwaitingApproval, Running, Completed, Failed, Skipped) | — | `TaskPlanRun.cs`、`PlanRunner.cs`、UI 事件 | 单节点状态机 |
| `TaskPlanRunState` | 枚举 | `src/agent/intent/TaskPlanRun.cs:132` | — | `TaskPlanRun.cs` | 整轮计划状态机 |
| `NodeFailureKind` | 枚举 (2 值) | `src/agent/registry/NodeExecutionResult.cs:8` (Permanent / Transient) | — | `PlanRunner.cs`、重试策略 | 失败可重试性 |
| `InjectedInstructionKind` | 枚举 | `src/agent/intent/TaskPlanRun.cs:193` | — | `InjectedInstructionClassifier` :215 | 运行中注入指令分类 |
| `IntentDecomposer.ConfidenceFlags` | flags 枚举 | `src/agent/intent/IntentDecomposer.cs:38` | — | `TaskPlan.cs:117` | 拆解置信度信号 |
| `TaskPlanExecutor` | 节点执行体 | `src/agent/registry/NodeExecutionResult.cs:47` | — | `src/agent/IndustrialAgentV2.cs` | 逐节点推进执行 |
| `PlanRunner` | 执行编排体 | `src/agent/intent/PlanRunner.cs:303` (`NewExecutor` :695) | `src/agent/extensions/ServiceCollectionExtensions.cs:160-163` | `src/agent/IndustrialAgentV2.cs` | 本地优先计划执行编排 |
| `ILocalNodeExecutor` | 执行器契约 | `src/agent/intent/PlanRunner.cs:51` | 由 `LocalExecutorRegistry` 接线 | `PlanRunner.cs` | 单节点本地执行契约 |
| `PythonSelfTestExecutor` | 执行体 | `src/agent/intent/PlanRunner.cs:64` | `PlanRoutePolicy.cs:48,61` (wired=true) | `PlanRunner.cs` | `python.selftest` 节点执行 |
| `TextProcessExecutor` | 执行体 | `src/agent/intent/PlanRunner.cs:142` | `PlanRoutePolicy.cs:51,67` (wired=true) | `PlanRunner.cs` | `text.process` 节点执行 |
| `LocalExecutorRegistry` (4 项) | 登记表 | `src/agent/intent/PlanRoutePolicy.cs:45` | 条目: `python.selftest` :48 (wire…:61)、`text.process` :51 (:67)、`realmachine.replay` :54 (wire=false :73)、`command.local` :57 (wire=false :79) | `PlanRoutePolicy` | 本地执行器白名单 (**4 登记 / 2 接线**) |
| `PlanRoutePolicy` | 路由决策 | `src/agent/intent/PlanRoutePolicy.cs:148` (`Decide`；`Apply` :417) | — | `src/agent/IndustrialAgentV2.cs` | 逐节点 local-vs-remote 判定 |
| `PlanResumeService` | 续跑体 | `src/agent/intent/PlanResumeService.cs:56` | `ServiceCollectionExtensions.cs` | `src/agent/IndustrialAgentV2.cs:2087,2202` | 澄清结清后计划续跑 |
| `NodeExecutionResult` | 结果 DTO | `src/agent/registry/NodeExecutionResult.cs:20` | — | `PlanRunner.cs` | 节点执行结果 |

**结论 (3)**: 无 `PlanNode.Kind` 枚举；kind = 9 个 `IntentRecognizer.Intents` 常量 + 2 个 `PlanNodeIntents` 本地 kind。逐节点执行体 = `ILocalNodeExecutor` 的 2 个已接线实现 (`PythonSelfTestExecutor`/`TextProcessExecutor`)，远端节点由 `TaskPlanExecutor`+`PlanRunner` 驱动。`LocalExecutorRegistry` 登记 4 项、**仅 2 项接线**。

## 4. agent.host CLI 子命令 / 入口清单

| 名称 | 契约/类型 | 定义 file:line | 注册/装配 file:line | 消费方 file:line | 职责 |
|---|---|---|---|---|---|
| `Main` | 进程入口 | `src/agent.host/Program.cs:35` | — | — | CLI 总入口 |
| `--smoke` / 无参 → `RunSmokeAsync` | 冒烟模式 | 判定 `Program.cs:41`；实现 `:582`；调用 `:390` | — | `Program.cs:390` | 非交互冒烟自检 |
| 交互 REPL → `RunCliAsync` | 交互模式 | `src/agent.host/Program.cs:402`；调用 `:391` | — | `Program.cs:391` | 交互式终端主循环 |
| `--llm-manager` | 子命令 | `Program.cs:115` | — | — | 启动 llm-manager |
| `--llm-service-status` | 子命令 | `Program.cs:148` | — | — | 查询 llm worker 状态 |
| `--compression-audit <file>` | 子命令 | `Program.cs:159` | — | — | 压缩审计报告 |
| `--frontend-api <port>` | 子命令 | `Program.cs:268` (判定), `:286` (启动), `:303-306` (装配 FrontendApiServer) | `Program.cs:286` | — | 挂载 FrontendApi 独立服务 |
| `--embed <text>` | 参数 | `Program.cs:64` | — | — | 单次 embedding |
| `-q <text>` | 参数 | `Program.cs:56` | — | — | 一次性提问 (one-shot) |
| `--log` `--session-id` `--output-mode` | 参数 | `Program.cs:54 / :58 / :60` | — | — | 日志路径 / 会话覆盖 / 输出模式 |
| `-img` `-rag` | 参数 | `Program.cs:67 / :70` | — | — | 图像 / 检索增强输入 |
| `--skills-dir` `--skills-blacklist` `--skills-file` | 参数 | `Program.cs:72 / :74 / :76` | — | — | skills 目录 / 黑名单 / 文件 |
| `--role` | 参数 | `Program.cs:79` | — | — | 角色覆盖 |
| `LocalCommandRouter.KnownCommands` (斜杠命令, 23 条) | 命令集 | `src/agent/registry/LocalCommandResult.cs:37-50`；`TryRoute` :53；switch 分派 :66-147；预路由集 :29-32 | — | `Program.cs` REPL / `IndustrialAgentV2` 拦截层 | 无 LLM 本地强制指令 |

斜杠命令全集 (23): `/model` `/balance` `/official-key` `/log` `/stop` `/continue` `/pause` `/status` `/reset` `/skills` `/skills-only` `/skills-exclude` `/staged` `/approve` `/reject` `/cleanup` `/activity` `/llm-service` `/schedule-run` `/git` `/help` (`LocalCommandResult.cs:39-49`)；前置路由子集 (4): `/model` `/balance` `/official-key` `/log` (`:31`)。

**结论 (4)**: 入口 = `Main` 1 个 + 6 个 `args[0]` 子命令 (`--smoke`/`--llm-manager`/`--llm-service-status`/`--compression-audit`/`--frontend-api`/默认 REPL) + 12 个 flag 参数 + 23 条斜杠命令。⚠ `/help` 文案 (`LocalCommandResult.cs:76`) 宣传 `/plan`、`/session`，但 `Known` 集合 (`:37-50`) **不含** 二者 → 落回 LLM，属文案/实现漂移。

## 5. agent.skills — SkillType 全部取值与执行体

| 名称 | 契约/类型 | 定义 file:line | 注册/装配 file:line | 消费方 file:line | 职责 |
|---|---|---|---|---|---|
| `SkillType` | 枚举 (3 值) | `src/agent.skills/SkillDefinition.cs:4`；`Normative` :6 / `Executive` :7 / `KnowledgeHint` :9 | `SkillDefinition.Type` :22 | `SkillDispatcher.cs:107,122,213`；`SkillRegistry.cs:52` | 技能三类口径 |
| `SkillDefinition` | 定义模型 | `src/agent.skills/SkillDefinition.cs:16` (ForceTemplate :40 / ForbiddenWords :43 / Idempotent :52) | `SkillRegistry` 解析 skills/*.yaml | `SkillDispatcher`、`TriggerMatcher` | 技能元数据 |
| `SkillResult` | 结果模型 | `src/agent.skills/SkillDefinition.cs:68` (ForceUse :75 / IsKnowledgeHint :78) | — | `src/agent/IndustrialAgentV2.cs` (技能结果回填) | 技能执行输出 |
| `SkillRegistry` | 注册表 | `src/agent.skills/SkillRegistry.cs:9` | `src/agent/extensions/ServiceCollectionExtensions.cs:298-332` | `ServiceCollectionExtensions.cs:338-344`；`IndustrialAgentV2` | 技能加载/登记 |
| `TriggerMatcher` | 匹配器 | `src/agent.skills/TriggerMatcher.cs:23` (`SkillMatch` :6) | `ServiceCollectionExtensions.cs:59-60`；`SkillDispatcher.cs:29-35` | `SkillDispatcher.cs:29`；`IndustrialAgentV2` | 关键词/正则/领域词触发 |
| `SkillDispatcher` | 调度体 (**执行体入口**) | `src/agent.skills/SkillDispatcher.cs:12` (ctor :29；`Lifecycle` :19) | `ServiceCollectionExtensions.cs:338-344` | `src/agent/IndustrialAgentV2.cs:313,379` | 按 `SkillType` 三分支执行 |
| — `KnowledgeHint` 分支 | 执行路径 | `SkillDispatcher.cs:107`（结果 `IsKnowledgeHint=true` :213 → 系统侧注入，走 LLM 主链） | — | `IndustrialAgentV2` | 知识提示：不直出/不吞提问 |
| — `Normative` 分支 | 执行路径 | `SkillDispatcher.cs:122`（`ForceUse=true` :212；禁语拦截） | — | `IndustrialAgentV2` | 口径型：模板承载 + 禁语校验 |
| — `Executive` 分支 (else) | 执行路径 | `SkillDispatcher.cs:140-187`（脚本 :151 / 委托 :181） | — | `IndustrialAgentV2` | 执行型：entry 委托 / 脚本 |
| `SkillExecutor` | 执行包装体 | `src/agent.skills/SkillExecutor.cs:11` (`ExecuteAsync` :25) | `SkillDispatcher.cs:36` (new) | `SkillDispatcher.cs:151,181` | 超时/幂等/熔断包装 |
| `SkillLifecycle` | 生命周期体 | `src/agent.skills/SkillLifecycle.cs:34` (`SkillState` :6 / `SkillRuntime` :15) | `SkillDispatcher.cs:35` | `SkillDispatcher.cs:19`；`IndustrialAgentV2` | 技能状态机/退避 |
| `SkillScriptRunner` | 脚本执行体 | `src/agent.skills/SkillScriptRunner.cs:28` | `ServiceCollectionExtensions.cs:335-337` | `SkillDispatcher.cs:151` | 沙箱脚本执行 |

**结论 (5)**: `SkillType` 三值；逐值执行路径集中在 `SkillDispatcher` 单一分发点 (`:107` / `:122` / `:140`)，无第二处 type-switch；执行统一经 `SkillExecutor` 包装，脚本统一经 `SkillScriptRunner`。

## 6. 零消费方候选扫描 (定义了但全仓无引用)

方法: 821 个 `public` 顶层类型的简单名 × 全仓 356 个 .cs 整词引用扫描（排除定义文件自身）。引用数 0 = 零消费方；引用仅落 `src/agent.tests/**` = 测试态。**启发式，非语义分析**。

### 6.1 零消费方 (0 引用、定义不在 tests: **160** 个)

| 类型 | 定义 file:line | 命名空间 |
|---|---|---|
| `FrozenSystemPromptTable` | `src/agent/IndustrialAgentV2.cs:39` | `agent` |
| `AgentSnapshot` | `src/agent/IndustrialAgentV2.cs:164` | `agent` |
| `ContentPart` | `src/agent/VisionChatDtos.cs:43` | `agent` |
| `ImageUrlSpec` | `src/agent/VisionChatDtos.cs:55` | `agent` |
| `ServiceCollectionExtensions` | `src/agent/extensions/ServiceCollectionExtensions.cs:29` | `agent` |
| `AgentFrameworkOptions` | `src/agent/extensions/ServiceCollectionExtensions.cs:395` | `agent` |
| `CodeChange` | `src/agent.codegen/CodeGenOptions.cs:99` | `agent.codegen` |
| `CodeSnippet` | `src/agent.codegen/CodeGenOptions.cs:143` | `agent.codegen` |
| `CodeMember` | `src/agent.codegen/CodeGenOptions.cs:306` | `agent.codegen` |
| `MemberKind` | `src/agent.codegen/CodeGenOptions.cs:320` | `agent.codegen` |
| `Symbol` | `src/agent.codegen/CodeGenOptions.cs:338` | `agent.codegen` |
| `SymbolKind` | `src/agent.codegen/CodeGenOptions.cs:350` | `agent.codegen` |
| `LanguageConfig` | `src/agent.codegen/CodeGenerator.cs:725` | `agent.codegen` |
| `ContextAssemblerConfig` | `src/agent/contextassembler/ContextAssemblerConfig.cs:12` | `agent.context` |
| `IContextQualityEvaluator` | `src/agent/contextassembler/ContextAssemblerConfig.cs:81` | `agent.context` |
| `ContextQualityScore` | `src/agent/contextassembler/ContextAssemblerConfig.cs:97` | `agent.context` |
| `AssemblyQualityReport` | `src/agent/contextassembler/ContextAssemblerConfig.cs:138` | `agent.context` |
| `ContextPriority` | `src/agent/contextassembler/ContextAssemblerConfig.cs:179` | `agent.context` |
| `ContextExpirationPolicy` | `src/agent/contextassembler/ContextAssemblerConfig.cs:197` | `agent.context` |
| `IContextValidator` | `src/agent/contextassembler/ContextAssemblerConfig.cs:223` | `agent.context` |
| `ValidationResult` | `src/agent/contextassembler/ContextAssemblerConfig.cs:244` | `agent.context` |
| `ContentCategory` | `src/agent.core/core/AgentEnums.cs:219` | `agent.core` |
| `FixEntry` | `src/agent/critique/FixMemory.cs:13` | `agent.critique` |
| `CritiqueResult` | `src/agent/critique/SelfCritic.cs:17` | `agent.critique` |
| `DataEntry` | `src/agent/datastore/DataEntry.cs:6` | `agent.datastore` |
| `DataQuery` | `src/agent/datastore/DataEntry.cs:20` | `agent.datastore` |
| `TensorInfo` | `src/agent.embedcpu/GgufModel.cs:20` | `agent.embedcpu` |
| `ExecutorLesson` | `src/agent/execution/ExecutorLessonMemory.cs:15` | `agent.execution` |
| `FileWriteResult` | `src/agent/execution/LockedFileWriter.cs:7` | `agent.execution` |
| `ComplexityVerdict` | `src/agent.exploration/ComplexityGate.cs:7` | `agent.exploration` |
| `ContextGateVerdict` | `src/agent.exploration/ContextBudgetGate.cs:31` | `agent.exploration` |
| `FormatRepairStep` | `src/agent.exploration/FormatRepair.cs:30` | `agent.exploration` |
| `LinkEntry` | `src/agent.exploration/LinkRegistry.cs:17` | `agent.exploration` |
| `StickyRouteDecision` | `src/agent.exploration/StickyRouteMemory.cs:23` | `agent.exploration` |
| `ThinkStep` | `src/agent.exploration/ThinkChainSession.cs:4` | `agent.exploration` |
| `ConvergeReason` | `src/agent.exploration/ThinkChainSession.cs:15` | `agent.exploration` |
| `ThinkChainResult` | `src/agent.exploration/ThinkChainSession.cs:23` | `agent.exploration` |
| `AskReply` | `src/agent.frontendapi/AskEnvelope.cs:24` | `agent.frontendapi` |
| `FrontendRequest` | `src/agent.frontendapi/FrontendApiContract.cs:87` | `agent.frontendapi` |
| `AuditRow` | `src/agent.host/Program.cs:692` | `agent.host` |
| `LocalExecutorDescriptor` | `src/agent/intent/PlanRoutePolicy.cs:29` | `agent.intent` |
| `RouteDecision` | `src/agent/intent/PlanRoutePolicy.cs:134` | `agent.intent` |
| `SocketRequestWriter` | `src/agent.io/SocketChannel.cs:59` | `agent.io` |
| `SocketReportReader` | `src/agent.io/SocketChannel.cs:92` | `agent.io` |
| `KeywordIndex` | `src/agent/keywordannotation/KeywordIndex.cs:9` | `agent.keywordannotation` |
| `ChatboxJsonContext` | `src/agent.logging/ChatboxSink.cs:45` | `agent.logging` |
| `MAFConfiguration` | `src/agent/maf/MAFConfiguration.cs:9` | `agent.maf` |
| `IMAFService` | `src/agent/maf/MAFConfiguration.cs:35` | `agent.maf` |
| `IMemoryRecall` | `src/agent/memory/IMemoryRecall.cs:8` | `agent.memory` |
| `MemoryRecall` | `src/agent/memory/IMemoryRecall.cs:24` | `agent.memory` |
| `MemoryQuery` | `src/agent/memory/MemoryQuery.cs:8` | `agent.memory` |
| `ShortTermMemory` | `src/agent/memory/ShortTermMemory.cs:6` | `agent.memory` |
| `BalanceResult` | `src/agent.modelqueue/BalanceQueryService.cs:6` | `agent.modelqueue` |
| `ChannelState` | `src/agent.modelqueue/ChannelScheduler.cs:10` | `agent.modelqueue` |
| `ScoredCandidate` | `src/agent.modelqueue/ChannelScheduler.cs:149` | `agent.modelqueue` |
| `CogViewClient` | `src/agent.modelqueue/CogViewClient.cs:14` | `agent.modelqueue` |
| `CogViewRequest` | `src/agent.modelqueue/CogViewClient.cs:27` | `agent.modelqueue` |
| `CogViewResponse` | `src/agent.modelqueue/CogViewClient.cs:39` | `agent.modelqueue` |
| `CogViewImage` | `src/agent.modelqueue/CogViewClient.cs:48` | `agent.modelqueue` |
| `CogViewError` | `src/agent.modelqueue/CogViewClient.cs:54` | `agent.modelqueue` |
| `CogViewResult` | `src/agent.modelqueue/CogViewClient.cs:64` | `agent.modelqueue` |
| `ImageRenderPluginRegistry` | `src/agent.modelqueue/ImageRenderPlugins/IImageRenderPlugin.cs:37` | `agent.modelqueue` |
| `RenderResult` | `src/agent.modelqueue/LocalSvgRenderer.cs:31` | `agent.modelqueue` |
| `ModelCapabilitiesParser` | `src/agent.modelqueue/ModelCatalog.cs:7` | `agent.modelqueue` |
| `ModelCapabilities` | `src/agent.modelqueue/ModelCatalog.cs:70` | `agent.modelqueue` |
| `LocalChannelConfig` | `src/agent.modelqueue/ModelCatalog.cs:83` | `agent.modelqueue` |
| `ModelCatalogLoadResult` | `src/agent.modelqueue/ModelCatalog.cs:228` | `agent.modelqueue` |
| `IModelQueueCaller` | `src/agent.modelqueue/ModelQueueRouter.cs:62` | `agent.modelqueue` |
| `ModelSwitchRecord` | `src/agent.modelqueue/ModelQueueRouter.cs:68` | `agent.modelqueue` |
| `ModelVerifyResult` | `src/agent.modelqueue/ModelVerifyService.cs:7` | `agent.modelqueue` |
| `OpenAIChatChoice` | `src/agent.modelqueue/OpenAIChatResponseDtos.cs:78` | `agent.modelqueue` |
| `OpenAIChatResponseMessage` | `src/agent.modelqueue/OpenAIChatResponseDtos.cs:90` | `agent.modelqueue` |
| `OpenAIChatUsage` | `src/agent.modelqueue/OpenAIChatResponseDtos.cs:107` | `agent.modelqueue` |
| `UsageRecord` | `src/agent.modelqueue/TokenUsageService.cs:7` | `agent.modelqueue` |
| `BalanceSnapshot` | `src/agent.modelqueue/TokenUsageService.cs:10` | `agent.modelqueue` |
| `UsageStatsSnapshot` | `src/agent.modelqueue/TokenUsageService.cs:216` | `agent.modelqueue` |
| `PipelineTask` | `src/agent/pipeline/PipelineTask.cs:6` | `agent.pipeline` |
| `PipelineContext` | `src/agent/pipeline/PipelineTask.cs:23` | `agent.pipeline` |
| `DecompositionResult` | `src/agent/pipeline/PipelineTask.cs:126` | `agent.pipeline` |
| `DecomposeOptions` | `src/agent/pipeline/PipelineTask.cs:137` | `agent.pipeline` |
| `ComplexityAssessment` | `src/agent/pipeline/PipelineTask.cs:147` | `agent.pipeline` |
| `DependencyGraph` | `src/agent/pipeline/PipelineTask.cs:160` | `agent.pipeline` |
| `RAGStats` | `src/agent.rag/RAGConfig.cs:125` | `agent.rag` |
| `ErrorInfo` | `src/agent.recovery/ErrorInfo.cs:8` | `agent.recovery` |
| `ErrorType` | `src/agent.recovery/ErrorInfo.cs:24` | `agent.recovery` |
| `ErrorSeverity` | `src/agent.recovery/ErrorInfo.cs:41` | `agent.recovery` |
| `RecoveryAction` | `src/agent.recovery/ErrorInfo.cs:52` | `agent.recovery` |
| `RecoveryStrategy` | `src/agent.recovery/ErrorInfo.cs:66` | `agent.recovery` |
| `RecoveryResult` | `src/agent.recovery/ErrorInfo.cs:80` | `agent.recovery` |
| `RetryPolicy` | `src/agent.recovery/ErrorInfo.cs:92` | `agent.recovery` |
| `RollbackPoint` | `src/agent.recovery/ErrorInfo.cs:105` | `agent.recovery` |
| `ErrorClassifier` | `src/agent.recovery/ErrorInfo.cs:118` | `agent.recovery` |
| `ErrorPattern` | `src/agent.recovery/ErrorInfo.cs:251` | `agent.recovery` |
| `RecoveryJsonContext` | `src/agent.recovery/ExecutionCheckpoint.cs:72` | `agent.recovery` |
| `RecoveryPlan` | `src/agent.recovery/ExecutionCheckpoint.cs:144` | `agent.recovery` |
| `AgentRegistryFile` | `src/agent/registry/AgentIdentity.cs:33` | `agent.registry` |
| `AgentProfileFile` | `src/agent/registry/AgentProfile.cs:157` | `agent.registry` |
| `ArtifactRepairResult` | `src/agent/registry/ArtifactRepair.cs:154` | `agent.registry` |
| `ItemAnswer` | `src/agent/registry/ClarificationBatch.cs:13` | `agent.registry` |
| `BatchResult` | `src/agent/registry/ClarificationBatch.cs:23` | `agent.registry` |
| `EvidenceRequest` | `src/agent/registry/EvidenceGate.cs:21` | `agent.registry` |
| `GateResult` | `src/agent/registry/EvidenceGate.cs:34` | `agent.registry` |
| `LocalCommandResult` | `src/agent/registry/LocalCommandResult.cs:7` | `agent.registry` |
| `GlobalStatusPanel` | `src/agent/registry/PanelData.cs:229` | `agent.registry` |
| `RecoveryPanel` | `src/agent/registry/PanelData.cs:244` | `agent.registry` |
| `CapabilityEntry` | `src/agent/registry/PanelData.cs:253` | `agent.registry` |
| `AgentStatusPanel` | `src/agent/registry/PanelData.cs:260` | `agent.registry` |
| `ProfileEntry` | `src/agent/registry/PanelData.cs:272` | `agent.registry` |
| `GoalEntry` | `src/agent/registry/PanelData.cs:283` | `agent.registry` |
| `SessionListPanel` | `src/agent/registry/PanelData.cs:291` | `agent.registry` |
| `SessionSummaryEntry` | `src/agent/registry/PanelData.cs:298` | `agent.registry` |
| `SessionDetailPanel` | `src/agent/registry/PanelData.cs:309` | `agent.registry` |
| `MessageEntry` | `src/agent/registry/PanelData.cs:325` | `agent.registry` |
| `LessonSnapshot` | `src/agent.roles/LessonTable.cs:36` | `agent.roles` |
| `DomainStats` | `src/agent.roles/RoleGrowthLedger.cs:25` | `agent.roles` |
| `SearchSortBy` | `src/agent/search/SearchResult.cs:131` | `agent.search` |
| `BochaData` | `src/agent/search/providers/BochaSearchProvider.cs:136` | `agent.search` |
| `BochaWebPages` | `src/agent/search/providers/BochaSearchProvider.cs:142` | `agent.search` |
| `BochaPage` | `src/agent/search/providers/BochaSearchProvider.cs:148` | `agent.search` |
| `SearXngResult` | `src/agent/search/providers/SearXngSearchProvider.cs:101` | `agent.search` |
| `SessionMemoryDto` | `src/agent/session/SessionMemoryStore.cs:110` | `agent.session` |
| `ConditionalRunVerdict` | `src/agent.skills/ConditionalScriptScheduler.cs:18` | `agent.skills` |
| `PythonInterpreter` | `src/agent.skills/PythonInterpreterResolver.cs:11` | `agent.skills` |
| `PythonRunResult` | `src/agent.skills/PythonRunVerifier.cs:12` | `agent.skills` |
| `PythonValidationResult` | `src/agent.skills/PythonScriptValidator.cs:10` | `agent.skills` |
| `ScriptPluginEvent` | `src/agent.skills/ScriptPluginProtocol.cs:24` | `agent.skills` |
| `SkillWrite` | `src/agent.skills/SkillContextScope.cs:4` | `agent.skills` |
| `SkillJsonContext` | `src/agent.skills/SkillDispatcher.cs:227` | `agent.skills` |
| `SkillRuntime` | `src/agent.skills/SkillLifecycle.cs:15` | `agent.skills` |
| `SkillMatch` | `src/agent.skills/TriggerMatcher.cs:6` | `agent.skills` |
| `ApprovalResult` | `src/agent/staging/ApprovalController.cs:10` | `agent.staging` |
| `TaskBoundary` | `src/agent.core/subagent/SubAgentTask.cs:112` | `agent.subagent` |
| `IsolatedTaskResult` | `src/agent/subagent/IsolatedTaskRunner.cs:7` | `agent.subagent` |
| `PromptMessage` | `src/agent/templates/IPromptBuilder.cs:133` | `agent.templates` |
| `PatternType` | `src/agent/templates/Template.cs:102` | `agent.templates` |
| `TendencyConfig` | `src/agent/tendency/TendencyData.cs:21` | `agent.tendency` |
| `ContextBias` | `src/agent/tendency/TendencyData.cs:32` | `agent.tendency` |
| `TokenCounter` | `src/agent/tokencompression/ITokenCompressor.cs:487` | `agent.tokencompression` |
| `PromptPersistence` | `src/agent/userinteraction/PromptPersistence.cs:10` | `agent.userinteraction` |
| `ConfirmOption` | `src/agent/userinteraction/UserConfirmRequest.cs:52` | `agent.userinteraction` |
| `MessageAction` | `src/agent/userinteraction/UserConfirmRequest.cs:193` | `agent.userinteraction` |
| `MessageActionType` | `src/agent/userinteraction/UserConfirmRequest.cs:214` | `agent.userinteraction` |
| `SemanticSearchResult` | `src/agent.vectormemory/VectorDocument.cs:26` | `agent.vectormemory` |
| `SemanticSearchRequest` | `src/agent.vectormemory/VectorDocument.cs:37` | `agent.vectormemory` |
| `ConsolidationConfig` | `src/agent.vectormemory/VectorDocument.cs:104` | `agent.vectormemory` |
| `GitChangeType` | `src/agent.workspace/GitChangeType.cs:8` | `agent.workspace` |
| `GitChange` | `src/agent.workspace/GitChangeType.cs:44` | `agent.workspace` |
| `GitStatus` | `src/agent.workspace/GitChangeType.cs:54` | `agent.workspace` |
| `GitOperationResult` | `src/agent.workspace/GitChangeType.cs:68` | `agent.workspace` |
| `FileChangeType` | `src/agent.workspace/WorkspaceState.cs:20` | `agent.workspace` |
| `FileChangeEvent` | `src/agent.workspace/WorkspaceState.cs:31` | `agent.workspace` |
| `ParseError` | `src/agent.rover/formal/FormalKernel.cs:31` | `agent.rover.formal` |
| `Atom` | `src/agent.rover/formal/Formula.cs:14` | `agent.rover.formal` |
| `Or` | `src/agent.rover/formal/Formula.cs:16` | `agent.rover.formal` |
| `GgufValueKind` | `src/agent.rover/gguf/GgufReader.cs:6` | `agent.rover.gguf` |
| `GgufValue` | `src/agent.rover/gguf/GgufReader.cs:13` | `agent.rover.gguf` |
| `GgufArray` | `src/agent.rover/gguf/GgufReader.cs:44` | `agent.rover.gguf` |
| `GgufTensorInfo` | `src/agent.rover/gguf/GgufReader.cs:54` | `agent.rover.gguf` |
| `Kernels` | `src/agent.rover/gpu/spirv/Kernels.cs:4` | `agent.rover.gpu.spirv` |
| `TensorBuffer` | `src/agent.rover/runtime/TensorResidency.cs:37` | `agent.rover.runtime` |

### 6.2 仅测试态引用 (生产零消费: **49** 个)

| 类型 | 定义 file:line | 命名空间 |
|---|---|---|
| `MainAgent` | `src/agent/extensions/ServiceCollectionExtensions.cs:471` | `agent` |
| `ActivityEntry` | `src/agent/activity/ActivityService.cs:12` | `agent.activity` |
| `SyntaxError` | `src/agent.codegen/CodeGenOptions.cs:246` | `agent.codegen` |
| `ConfigModelBinder` | `src/agent.config/ConfigModelBinder.cs:19` | `agent.config` |
| `PromptHeaderFormat` | `src/agent/contextassembler/PromptHeaderFormat.cs:8` | `agent.context` |
| `ContextSnippetExtensions` | `src/agent/contextassembler/PromptHeaderFormat.cs:336` | `agent.context` |
| `CriticPipeline` | `src/agent/critique/CriticPipeline.cs:11` | `agent.critique` |
| `AnchoredFinding` | `src/agent/critique/CriticPipeline.cs:13` | `agent.critique` |
| `GuardrailEntry` | `src/agent/critique/GuardrailMemory.cs:16` | `agent.critique` |
| `CollisionDetector` | `src/agent/execution/CollisionDetector.cs:14` | `agent.execution` |
| `ComplexityGate` | `src/agent.exploration/ComplexityGate.cs:14` | `agent.exploration` |
| `FormatRepairConfig` | `src/agent.exploration/FormatRepair.cs:40` | `agent.exploration` |
| `FormatRepairRegistry` | `src/agent.exploration/FormatRepair.cs:56` | `agent.exploration` |
| `FormatRepairLoop` | `src/agent.exploration/FormatRepair.cs:76` | `agent.exploration` |
| `JsonRepairPlugin` | `src/agent.exploration/JsonRepairPlugin.cs:9` | `agent.exploration` |
| `RouteRecord` | `src/agent.exploration/StickyRouteMemory.cs:7` | `agent.exploration` |
| `StickyRouteConfig` | `src/agent.exploration/StickyRouteMemory.cs:32` | `agent.exploration` |
| `StickyRouteMemory` | `src/agent.exploration/StickyRouteMemory.cs:47` | `agent.exploration` |
| `FrontendApiRouter` | `src/agent.frontendapi/FrontendApiServer.cs:324` | `agent.frontendapi` |
| `GtDoc` | `src/agent.host/Program.cs:675` | `agent.host` |
| `PlanNodeIntents` | `src/agent/intent/PlanRoutePolicy.cs:10` | `agent.intent` |
| `LocalVerifyNodePlanner` | `src/agent/intent/PlanRoutePolicy.cs:257` | `agent.intent` |
| `ILocalNodeExecutor` | `src/agent/intent/PlanRunner.cs:51` | `agent.intent` |
| `PlanEvents` | `src/agent/intent/PlanRunner.cs:217` | `agent.intent` |
| `SharedMemoryChannel` | `src/agent.io/SharedMemoryChannel.cs:22` | `agent.io` |
| `SharedMemoryRequestWriter` | `src/agent.io/SharedMemoryChannel.cs:47` | `agent.io` |
| `SharedMemoryReportReader` | `src/agent.io/SharedMemoryChannel.cs:131` | `agent.io` |
| `SocketChannel` | `src/agent.io/SocketChannel.cs:20` | `agent.io` |
| `SocketChannelServer` | `src/agent.io/SocketChannel.cs:36` | `agent.io` |
| `EmbedderModeKind` | `src/agent/llamalocal/RemoteEmbedder.cs:349` | `agent.llamalocal` |
| `EmbedderMode` | `src/agent/llamalocal/RemoteEmbedder.cs:351` | `agent.llamalocal` |
| `ModelChannel` | `src/agent.modelqueue/ChannelScheduler.cs:4` | `agent.modelqueue` |
| `SvgTextRenderPlugin` | `src/agent.modelqueue/ImageRenderPlugins/SvgTextRenderPlugin.cs:6` | `agent.modelqueue` |
| `BalanceScheme` | `src/agent.modelqueue/ModelCatalog.cs:98` | `agent.modelqueue` |
| `ICapabilityPlugin` | `src/agent/registry/CapabilityPlugin.cs:14` | `agent.registry` |
| `PluginExecutionResult` | `src/agent/registry/CapabilityPlugin.cs:33` | `agent.registry` |
| `CapabilityPluginRegistry` | `src/agent/registry/CapabilityPlugin.cs:54` | `agent.registry` |
| `CorrectionVerdict` | `src/agent.roles/CorrectionDetector.cs:18` | `agent.roles` |
| `LessonInstance` | `src/agent.roles/LessonTable.cs:12` | `agent.roles` |
| `RoleLessons` | `src/agent.roles/RoleLessons.cs:14` | `agent.roles` |
| `SessionConfig` | `src/agent/session/Session.cs:209` | `agent.session` |
| `SessionLoop` | `src/agent/session/Session.cs:286` | `agent.session` |
| `SessionHistorySearch` | `src/agent/session/SessionHistorySearch.cs:20` | `agent.session` |
| `ISource` | `src/agent/session/SessionHistorySearch.cs:23` | `agent.session` |
| `Hit` | `src/agent/session/SessionHistorySearch.cs:30` | `agent.session` |
| `StoreSource` | `src/agent/session/SessionHistorySearch.cs:219` | `agent.session` |
| `ConditionalRunVerdictType` | `src/agent.skills/ConditionalScriptScheduler.cs:8` | `agent.skills` |
| `SkillState` | `src/agent.skills/SkillLifecycle.cs:6` | `agent.skills` |
| `CompressionOptions` | `src/agent/tokencompression/ITokenCompressor.cs:35` | `agent.tokencompression` |

### 6.3 文件级「全零」集中区 (该文件全部 public 类型零消费; 共 83 个文件, 列出 Top 40 by 数量)

| 文件 | 零消费类型数 | 样本 |
|---|---|---|
| `src/agent.recovery/ErrorInfo.cs` | 10 | `ErrorInfo`, `ErrorType`, `ErrorSeverity`, `RecoveryAction`, `RecoveryStrategy` |
| `src/agent/registry/PanelData.cs` | 10 | `GlobalStatusPanel`, `RecoveryPanel`, `CapabilityEntry`, `AgentStatusPanel`, `ProfileEntry` |
| `src/agent/contextassembler/ContextAssemblerConfig.cs` | 8 | `ContextAssemblerConfig`, `IContextQualityEvaluator`, `ContextQualityScore`, `AssemblyQualityReport`, `ContextPriority` |
| `src/agent.codegen/CodeGenOptions.cs` | 6 | `CodeChange`, `CodeSnippet`, `CodeMember`, `MemberKind`, `Symbol` |
| `src/agent.modelqueue/CogViewClient.cs` | 6 | `CogViewClient`, `CogViewRequest`, `CogViewResponse`, `CogViewImage`, `CogViewError` |
| `src/agent/pipeline/PipelineTask.cs` | 6 | `PipelineTask`, `PipelineContext`, `DecompositionResult`, `DecomposeOptions`, `ComplexityAssessment` |
| `src/agent.modelqueue/ModelCatalog.cs` | 4 | `ModelCapabilitiesParser`, `ModelCapabilities`, `LocalChannelConfig`, `ModelCatalogLoadResult` |
| `src/agent.workspace/GitChangeType.cs` | 4 | `GitChangeType`, `GitChange`, `GitStatus`, `GitOperationResult` |
| `src/agent.rover/gguf/GgufReader.cs` | 4 | `GgufValueKind`, `GgufValue`, `GgufArray`, `GgufTensorInfo` |
| `src/agent.exploration/ThinkChainSession.cs` | 3 | `ThinkStep`, `ConvergeReason`, `ThinkChainResult` |
| `src/agent.modelqueue/OpenAIChatResponseDtos.cs` | 3 | `OpenAIChatChoice`, `OpenAIChatResponseMessage`, `OpenAIChatUsage` |
| `src/agent.modelqueue/TokenUsageService.cs` | 3 | `UsageRecord`, `BalanceSnapshot`, `UsageStatsSnapshot` |
| `src/agent/search/providers/BochaSearchProvider.cs` | 3 | `BochaData`, `BochaWebPages`, `BochaPage` |
| `src/agent/userinteraction/UserConfirmRequest.cs` | 3 | `ConfirmOption`, `MessageAction`, `MessageActionType` |
| `src/agent.vectormemory/VectorDocument.cs` | 3 | `SemanticSearchResult`, `SemanticSearchRequest`, `ConsolidationConfig` |
| `src/agent/IndustrialAgentV2.cs` | 2 | `FrozenSystemPromptTable`, `AgentSnapshot` |
| `src/agent/VisionChatDtos.cs` | 2 | `ContentPart`, `ImageUrlSpec` |
| `src/agent/extensions/ServiceCollectionExtensions.cs` | 2 | `ServiceCollectionExtensions`, `AgentFrameworkOptions` |
| `src/agent/datastore/DataEntry.cs` | 2 | `DataEntry`, `DataQuery` |
| `src/agent/intent/PlanRoutePolicy.cs` | 2 | `LocalExecutorDescriptor`, `RouteDecision` |
| `src/agent.io/SocketChannel.cs` | 2 | `SocketRequestWriter`, `SocketReportReader` |
| `src/agent/maf/MAFConfiguration.cs` | 2 | `MAFConfiguration`, `IMAFService` |
| `src/agent/memory/IMemoryRecall.cs` | 2 | `IMemoryRecall`, `MemoryRecall` |
| `src/agent.modelqueue/ChannelScheduler.cs` | 2 | `ChannelState`, `ScoredCandidate` |
| `src/agent.modelqueue/ModelQueueRouter.cs` | 2 | `IModelQueueCaller`, `ModelSwitchRecord` |
| `src/agent.recovery/ExecutionCheckpoint.cs` | 2 | `RecoveryJsonContext`, `RecoveryPlan` |
| `src/agent/registry/ClarificationBatch.cs` | 2 | `ItemAnswer`, `BatchResult` |
| `src/agent/registry/EvidenceGate.cs` | 2 | `EvidenceRequest`, `GateResult` |
| `src/agent/tendency/TendencyData.cs` | 2 | `TendencyConfig`, `ContextBias` |
| `src/agent.workspace/WorkspaceState.cs` | 2 | `FileChangeType`, `FileChangeEvent` |
| `src/agent.rover/formal/Formula.cs` | 2 | `Atom`, `Or` |
| `src/agent.codegen/CodeGenerator.cs` | 1 | `LanguageConfig` |
| `src/agent.core/core/AgentEnums.cs` | 1 | `ContentCategory` |
| `src/agent/critique/FixMemory.cs` | 1 | `FixEntry` |
| `src/agent/critique/SelfCritic.cs` | 1 | `CritiqueResult` |
| `src/agent.embedcpu/GgufModel.cs` | 1 | `TensorInfo` |
| `src/agent/execution/ExecutorLessonMemory.cs` | 1 | `ExecutorLesson` |
| `src/agent/execution/LockedFileWriter.cs` | 1 | `FileWriteResult` |
| `src/agent.exploration/ComplexityGate.cs` | 1 | `ComplexityVerdict` |
| `src/agent.exploration/ContextBudgetGate.cs` | 1 | `ContextGateVerdict` |

### 6.4 用户点名候选逐条裁定

| 点名候选 | 定义 file:line | 生产消费方 file:line | 裁定 |
|---|---|---|---|
| `TaskCharter` | `src/agent/tasks/TaskCharter.cs:13` | `src/agent/IndustrialAgentV2.cs:922,935-937,944-953` | **非零消费** |
| `OutputCritic` | `src/agent/critique/OutputCritic.cs:11` | `src/agent/critique/CriticPipeline.cs:22` (唯一非测试消费方) | **传递性零消费** (消费方 CriticPipeline 自身死) |
| `SelfCritic` | `src/agent/critique/SelfCritic.cs:13` | `src/agent/critique/CriticPipeline.cs:23` | **传递性零消费** |
| `CriticPipeline` | `src/agent/critique/CriticPipeline.cs:11` | 未找到(已扫: `CriticPipeline` 全 src；仅 `src/agent.tests/CriticPipelineTests.cs`) | **零消费方(测试态)** |
| `FormatRepairLoop` | `src/agent.exploration/FormatRepair.cs:76` | 未找到(已扫: `FormatRepairLoop` 全 src；仅 `src/agent.tests/FormatRepairTests.cs`) | **零消费方(测试态)** |
| `IFormatRepairPlugin` 整模块 | `FormatRepair.cs:8`(接口) `:30`(Step) `:40`(Config) `:56`(Registry) `:76`(Loop)；`JsonRepairPlugin.cs:9` | 未找到(已扫: `IFormatRepairPlugin`/`FormatRepairRegistry`/`JsonRepairPlugin` 全 src) | **整模块零消费** |
| `FixMemory` / `FixEntry` | `src/agent/critique/FixMemory.cs:11` / `:13` | `CriticPipeline.cs` (死) | **传递性零消费** |
| `ModelQueueAdapter` | `src/agent/modelqueue/ModelQueueAdapter.cs:12` | `src/agent/extensions/ServiceCollectionExtensions.cs:276-278` (DI `ILLMCaller`) | **非零消费**，且**无双副本** |

其他高置信死簇 (整文件全部 public 类型零消费): `src/agent.recovery/ErrorInfo.cs` (10 型)、`src/agent/contextassembler/ContextAssemblerConfig.cs` (8 型)、`src/agent.codegen/CodeGenOptions.cs` (6 型)、`src/agent.modelqueue/CogViewClient.cs` (6 型)、`src/agent/pipeline/PipelineTask.cs` (6 型)、`src/agent.workspace/GitChangeType.cs` (4 型)、`src/agent/search/providers/BochaSearchProvider.cs` (3 型)、`src/agent.vectormemory/VectorDocument.cs` (3 型)、`src/agent.frontendapi/FrontendApiContract.cs`。

⚠ 误报扣除: `ServiceCollectionExtensions` (`:29`) 是扩展方法宿主类，真实消费点 `src/agent.host/Program.cs:389` (`services.AddAgentFramework(...)`)；`PanelData.cs` 10 个面板 DTO、`TokenUsageService` 快照为序列化载荷。不作为删除候选。

## 7. 双副本实现扫描 (同名类落于两个文件)

方法: 全仓 356 .cs 提取全部类型声明 (含 private/嵌套/record/enum)，按简单名分组，报告落在 ≥2 个文件的名字。

| 同名类型 | 副本 A | 副本 B | 性质 | 裁定 |
|---|---|---|---|---|
| `SearchResult` | `src/agent.workspace/WorkspaceState.cs:188` (`public class`, ns `agent.workspace`) | `src/agent/search/SearchResult.cs:6` (`public class`, ns `agent.search`) | **生产/生产, 同名不同命名空间** | 命名冲突候选 (编译无冲突; 跨命名空间易混) |
| `MemoryEntry` | `src/agent/memory/MemoryEntry.cs:6` (`public class`, ns `agent.memory`) | `src/agent/session/SessionMemory.cs:182` (`private sealed record`, 嵌套) | 生产/生产, 可见性不同 | 低风险 (一份是私有嵌套) |
| `GtDoc` | `src/agent.host/Program.cs:675` (`class`) | `src/agent.tests/RecallRateTests.cs:15` (`record`) | 生产/测试 | 低风险 |
| `Program.cs` (文件名副本) | `src/agent.host/Program.cs` | `src/agent.rover/Program.cs` | 同名文件不同项目 | 无害 |
| `ModelQueueAdapter` (用户点名) | `src/agent/modelqueue/ModelQueueAdapter.cs:12` | **未找到第二副本** (已扫: `class ModelQueueAdapter`、全仓文件名 `ModelQueueAdapter*` 全 src) | 单一定义 | **不是双副本** |
| `FakeEmbedder` / `StubAgent` / `StubHttpClientFactory` / `ThrowingSink` | 均只在 `src/agent.tests/**` 内跨文件重名 | — | 测试桩重名 | 非产品代码 |

**相邻副本 (非同名但同职责相邻目录, 归拢候选)**: `src/agent/modelqueue/` (agent 项目子目录, 命名空间 `agent`, 宿主 `ModelQueueAdapter`) 与 `src/agent.modelqueue/` (独立项目, 命名空间 `agent.modelqueue`, 宿主 `ModelQueueRouter`) — 目录名近乎同名、职责相邻。证据: `src/agent/modelqueue/ModelQueueAdapter.cs:5` (`namespace agent;`) vs `src/agent.modelqueue/ModelQueueRouter.cs:5` (`namespace agent.modelqueue;`)。

## 8. 汇总计数

| 指标 | 值 | 说明 |
|---|---|---|
| 扫描文件数 (.cs, 排 obj/bin) | 356 | src 全量 |
| public 顶层类型数 | 821 | 全仓 |
| ① 生产 CapabilityPlugin 注册数 | **0** | 注册表存在但零注册零消费 |
| ② IResponseSegmentPlugin 实现数 | **3** | 均在生产 DI 注册 |
| ② SegmentKind 取值数 | **3** | PlainText / Code / InlineCode |
| ③ PlanNode kind 来源 | **9 + 2** | IntentRecognizer.Intents (9) + PlanNodeIntents (2)；无 Kind 枚举 |
| ③ 本地节点执行体 | **2 已接线 / 4 登记** | ILocalNodeExecutor 实现 |
| ④ CLI 入口/子命令数 | **6 模式 + 12 flag + 23 斜杠** | 见 §4 |
| ⑤ SkillType 取值数 | **3** | 3 执行体统一经 SkillDispatcher |
| **零消费方候选数** | **160** | 0 引用、定义不在 tests (§6.1 全表) |
| 零消费方 (含仅测试态) | **209** | §6.1 + §6.2 |
| **双副本候选数** | **4** | SearchResult / MemoryEntry / GtDoc / modelqueue 双目录 (ModelQueueAdapter 本身未找到副本) |

