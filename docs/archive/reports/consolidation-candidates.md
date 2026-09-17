# R385 — 归拢候选 (consolidation candidates)

- 仓库: `/home/agentuser/AgentFramework` @ `main` / `45a60c9`
- 来源: `docs/reports/r385/capability-inventory.md` 的零消费方(§6)与双副本(§7)扫描。
- 免责: 零消费方为**文本整词启发式**，删改前须二次人工确认（尤其序列化 DTO）。本文件仅候选，不含任何产品代码改动。

| # | 候选 (合并/删除/去重/延后) | 证据 file:line | 归拢动作 | 风险 | 不可合并/暂缓的理由 |
|---|---|---|---|---|---|
| 1 | `src/agent.recovery/ErrorInfo.cs` 9 型 (ErrorInfo/ErrorType/ErrorSeverity/RecoveryAction/RecoveryStrategy/RecoveryResult/RetryPolicy/RollbackPoint/ErrorClassifier/ErrorPattern) | `src/agent.recovery/ErrorInfo.cs:8,24,41,52,66,80,92,105,118,251`；§6.1 零消费 | 整文件删除或归档至 docs/archive | 低 | 同模块 `ExecutionCheckpoint.cs` 仍被 `PlanResumeService` 消费 → 只能删 ErrorInfo.cs 本文件 |
| 2 | `FormatRepair` 整模块 (IFormatRepairPlugin/Step/Config/Registry/Loop/JsonRepairPlugin) | `src/agent.exploration/FormatRepair.cs:8,30,40,56,76`；`src/agent.exploration/JsonRepairPlugin.cs:9`；仅 `src/agent.tests/FormatRepairTests.cs` | 模块删除 (文档留存设计) | 低 | 无生产入口; 删除后测试须同步移除 |
| 3 | `critique` 自审簇 (CriticPipeline/OutputCritic/SelfCritic/FixMemory) | `CriticPipeline.cs:11`(测试态)、`OutputCritic.cs:11`、`SelfCritic.cs:13`、`FixMemory.cs:11,13`；消费方仅 `CriticPipeline.cs:22,23` | 延后 (先决策是否接入自审链), 否则整体删除 | 中 | OutputCritic/SelfCritic/FixMemory 有非测试消费方 CriticPipeline, 但 CriticPipeline 自身死 → 三者只能随 CriticPipeline 一起删 |
| 4 | `ArtifactRepairLoop` 区段修复环 | `src/agent/registry/ArtifactRepair.cs:174`；消费方仅 `src/agent.tests/ArtifactRepairTests.cs` | 删除或去重 (与 FormatRepair 概念重叠) | 低 | — |
| 5 | `PanelData.cs` 10 个面板 DTO (GlobalStatusPanel/AgentStatusPanel/RecoveryPanel/CapabilityEntry/ProfileEntry/GoalEntry/SessionListPanel/SessionSummaryEntry/SessionDetailPanel/MessageEntry) | `src/agent/registry/PanelData.cs:229-325`；§6.1 零消费 | 延后 (不删) | 低 | 序列化载荷, 由 `PanelDataService`(`:12`) 生成 → 属误报类, 不可按零消费删除 |
| 6 | `ServiceCollectionExtensions` 静态宿主类 | `src/agent/extensions/ServiceCollectionExtensions.cs:29`；真实消费 `src/agent.host/Program.cs:389` | 不处理 (误报) | — | 扩展方法宿主类, 类名不出现在调用点 |
| 7 | `SearchResult` 双副本 | `src/agent.workspace/WorkspaceState.cs:188` vs `src/agent/search/SearchResult.cs:6` | 去重: 重命名 workspace 版为 `WorkspaceSearchResult` (或抽共享 DTO) | 低 | 不同命名空间无编译冲突, 但同名跨模块易混 |
| 8 | `MemoryEntry` 双副本 | `src/agent/memory/MemoryEntry.cs:6` (public) vs `src/agent/session/SessionMemory.cs:182` (private nested record) | 重命名嵌套 record (`SessionMemoryEntry`) | 低 | 可见性不同, 实际无冲突 |
| 9 | `src/agent/modelqueue/` 与 `src/agent.modelqueue/` 双目录同名 | `src/agent/modelqueue/ModelQueueAdapter.cs:5` (`namespace agent`) vs `src/agent.modelqueue/ModelQueueRouter.cs:5` (`namespace agent.modelqueue`) | 归拢: 把 `src/agent/modelqueue/*` 迁入 `agent.modelqueue` 项目或反之, 统一命名空间 | 中 | DI 注册点 `ServiceCollectionExtensions.cs:276-278` 及 `ModelQueueAdapter` 命名空间需同步改动; 跨项目引用需加 ProjectReference |
| 10 | `ICapabilityPlugin` + `CapabilityPluginRegistry` 未接线 | `src/agent/registry/CapabilityPlugin.cs:14,54`；零注册零消费 (§6.2) | 延后: 要么接线 (Program.cs DI) 要么删除契约 | 中 | 属对外扩展契约面, 删除影响插件 API 承诺; 接线则需真实插件 |
| 11 | `CapabilityScanner` 文档承诺的「显式注册」通道未实现 | `src/agent/registry/CapabilityScanner.cs:33` (注释) vs 无 `RegisterCapability` (§1) | 延后: 实现通道或删注释 | 低 | 仅注释-实现漂移 |
| 12 | `/help` 文案与 `Known` 命令集漂移 (`/plan` `/session`) | `src/agent/registry/LocalCommandResult.cs:76` (文案) vs `:37-50` (Known) | 修复: 文案与集合对齐 | 低 | — |
| 13 | `src/agent.pipeline/PipelineTask.cs` 6 型 (PipelineTask/PipelineContext/DecompositionResult/DecomposeOptions/ComplexityAssessment/DependencyGraph) | `src/agent/pipeline/PipelineTask.cs:6,23,126,137,147,160`；§6.1 零消费 | 延后/删除 | 低 | 整模块无入口 |
| 14 | `src/agent.codegen/CodeGenOptions.cs` 6 型 + `LanguageConfig` | `src/agent.codegen/CodeGenOptions.cs:99,143,306,320,338,350`；`CodeGenerator.cs:725` | 延后/删除 | 低 | — |
| 15 | `src/agent.modelqueue/CogViewClient.cs` 6 型 (图像渲染副线) | `src/agent.modelqueue/CogViewClient.cs:14,27,39,48,54,64`；§6.1 零消费 | 延后 | 低 | — |
| 16 | `src/agent/contextassembler/ContextAssemblerConfig.cs` 8 型 (含 IContextQualityEvaluator/IContextValidator 契约) | `src/agent/contextassembler/ContextAssemblerConfig.cs:12,81,97,138,179,197,223,244`；§6.1 零消费 | 延后 (契约面) | 中 | 含接口契约, 删除影响扩展面 |
| 17 | `src/agent.vectormemory/VectorDocument.cs` 3 型 + `src/agent.rag/RAGStats` | `VectorDocument.cs:26,37,104`；`src/agent.rag/RAGConfig.cs:125` | 延后/删除 | 低 | — |
| 18 | `src/agent.frontendapi` 契约 DTO (FrontendRequest/AskReply) | `FrontendApiContract.cs:87`；`AskEnvelope.cs:24` | 延后 | 低 | HTTP 序列化契约, 可能由前端调用 |
| 19 | `src/agent.workspace/GitChangeType.cs` 4 型 | `src/agent.workspace/GitChangeType.cs:8,44,54,68`；§6.1 零消费 | 延后/删除 | 低 | — |
| 20 | `LocalExecutorRegistry` 4 登记 / 仅 2 接线 | `src/agent/intent/PlanRoutePolicy.cs:54,57,73,79` (wire=false) | 收敛: 删除 2 项未接线登记 或 补接线 | 低 | — |
| 21 | `src/agent.exploration/ThinkChainSession.cs` 3 型 | `ThinkChainSession.cs:4,15,23`；§6.1 零消费 | 延后/删除 | 低 | — |

## 计数

- 候选总数: **21**
- 删除类 (1,2,4,13,14,15,19,21): 8
- 延后类 (3,5,10,11,16,17,18): 7
- 去重/重命名类 (7,8): 2
- 归拢/收敛类 (9,20): 2
- 修复类 (12): 1
- 误报不处理 (6): 1

