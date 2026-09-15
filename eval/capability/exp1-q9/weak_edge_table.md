# EXP1-Q9 弱边全量抽检 (两口径)

- A 计划口径 (符号级 noncode_mention, verdict=ok): **25** 条, 上下文行 43
- B 引用图口径 (引用级 weak_noncode 边): **16** 条, 上下文行 35
- A 的符号条目落在 B 的边里: 17/25
- 名称形态分布 A: {'SCREAMING_SNAKE': 3, 'PascalCase': 5, 'snake_case': 16, 'other': 1}
- occurrence 来源分布 A: {'string_literal': 24, 'comment': 19}
- 树内他处有声明 (declared_elsewhere) 的文件数分布 A: {0: 22, 1: 3}

## A 符号级全量清单

| # | doc | line | 符号 | 形态 | 被引文件 | 出现行 | 来源 | n_decl_elsewhere |
|---|---|---|---|---|---|---|---|---|
| 1 | docs/plans/v0.22.0-exp1-local-index-and-code-graph.md | 68 | `AGENTFRAMEWORK_BGE_MODEL` | SCREAMING_SNAKE | src/agent.llamacpp/LlamaCppTextEmbedder.cs | L35:string_literal | ok | 0 |
| 2 | docs/plans/v0.22.0-exp1-local-index-and-code-graph.md | 288 | `VulkanNames` | PascalCase | src/agent.gpu/cli/GpuCli.cs | L49:string_literal,L50:string_literal,L51:string_literal,L66:string_literal | ok | 1 |
| 3 | docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md | 53 | `req_id` | snake_case | src/agent.frontendapi/FrontendApiContract.cs | L9:string_literal,L10:string_literal,L34:string_literal,L54:string_literal | ok | 0 |
| 4 | docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md | 105 | `ask_id` | snake_case | src/agent.frontendapi/FrontendPromptService.cs | L8:comment,L29:comment,L105:comment | ok | 0 |
| 5 | docs/plans/v0.22.0-exp3-step-alignment-validation.md | 59 | `plan_executor_parallel` | snake_case | src/agent/IndustrialAgentV2.cs | L1910:comment | ok | 0 |
| 6 | docs/plans/v0.22.0-exp9-subtask-plan-routing-and-local-first.md | 73 | `loop_turn` | snake_case | src/agent/IndustrialAgentV2.cs | L645:comment,L646:string_literal,L1750:comment,L1850:string_literal | ok | 0 |
| 7 | docs/plans/v0.22.0-r371-capability-probe-python-game.md | 250 | `empty_always` | snake_case | src/agent/IndustrialAgentV2.cs | L1750:comment | ok | 0 |
| 8 | docs/plans/v0.42.0-r421-polarity.md | 18 | `recall_query` | snake_case | src/agent/IndustrialAgentV2.cs | L829:string_literal | ok | 0 |
| 9 | docs/plans/v0.47.0-r426-relation-judge-localization.md | 50 | `relation_judge` | snake_case | src/agent.modelqueue/ModelCatalog.cs | L211:string_literal | ok | 0 |
| 10 | docs/plans/v0.47.0-r426-relation-judge-localization.md | 50 | `turn_gate` | snake_case | src/agent.modelqueue/ModelCatalog.cs | L210:string_literal | ok | 0 |
| 11 | docs/plans/v0.47.0-r426-relation-judge-localization.md | 53 | `correction_judge` | snake_case | src/agent/IndustrialAgentV2.cs | L1720:string_literal | ok | 0 |
| 12 | docs/plans/v0.57.0-r436-e2e-brj-token-kpi.md | 18 | `failed_or_empty` | snake_case | src/agent.modelqueue/ModelQueueRouter.cs | L227:string_literal,L310:string_literal | ok | 0 |
| 13 | docs/plans/v0.59.0-r439-domain-extension.md | 18 | `dropped_chars` | snake_case | src/agent/IndustrialAgentV2.cs | L1556:string_literal | ok | 0 |
| 14 | docs/plans/v0.59.0-r439-domain-extension.md | 18 | `local_gate_skip_history` | snake_case | src/agent/IndustrialAgentV2.cs | L1553:string_literal | ok | 0 |
| 15 | docs/plans/v0.59.0-r439-domain-extension.md | 18 | `persisted_chars` | snake_case | src/agent/IndustrialAgentV2.cs | L1554:string_literal | ok | 0 |
| 16 | docs/plans/v0.59.0-r439-domain-extension.md | 18 | `would_be_chars` | snake_case | src/agent/IndustrialAgentV2.cs | L1555:string_literal | ok | 0 |
| 17 | docs/reports/bge/model-lineage-and-inventory-2026-09-14.md | 54 | `NullTextEmbedder` | PascalCase | src/agent.llamacpp/LlamaCppTextEmbedder.cs | L34:comment,L53:comment | ok | 1 |
| 18 | docs/reports/function-map-R326.md | 288 | `_queryEmbedding` | other | src/agent/contextassembler/ContextAssembler.cs | L1420:comment | ok | 0 |
| 19 | docs/reports/r385/capability-inventory.md | 24 | `RegisterCapability` | PascalCase | src/agent/registry/CapabilityScanner.cs | L8:comment,L33:comment | ok | 0 |
| 20 | docs/reports/r385/capability-inventory.md | 56 | `text_processing` | snake_case | src/agent/intent/PlanRoutePolicy.cs | L16:string_literal,L328:comment | ok | 0 |
| 21 | docs/reports/r385/capability-inventory.md | 56 | `verify_local` | snake_case | src/agent/intent/PlanRoutePolicy.cs | L13:string_literal,L328:comment | ok | 0 |
| 22 | docs/reports/r385/chain-map.md | 51 | `OpenAILLMCaller` | PascalCase | src/agent/extensions/ServiceCollectionExtensions.cs | L43:comment | ok | 1 |
| 23 | docs/reports/r385/chain-map.md | 127 | `AGENTFRAMEWORK_PLAN_EXEC` | SCREAMING_SNAKE | src/agent/intent/PlanRunner.cs | L301:comment,L308:string_literal | ok | 0 |
| 24 | docs/reports/r385/chain-map.md | 128 | `AGENTFRAMEWORK_PY_RUN` | SCREAMING_SNAKE | src/agent/intent/PlanRunner.cs | L39:comment | ok | 0 |
| 25 | docs/reports/r385/consolidation-candidates.md | 19 | `RegisterCapability` | PascalCase | src/agent/registry/CapabilityScanner.cs | L8:comment,L33:comment | ok | 0 |

## B 引用级全量清单 (weak_noncode)

- 1. docs/plans/v0.22.0-exp1-local-index-and-code-graph.md:54 -> src/agent/registry/CapabilityScanner.cs: `AssemblyLoadContext`(absent) + `GetTypes`(noncode_mention) [上下文行 1]
- 2. docs/plans/v0.22.0-exp1-local-index-and-code-graph.md:288 -> src/agent.gpu/cli/GpuCli.cs: `VulkanNames`(noncode_mention) [上下文行 4]
- 3. docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md:51 -> src/agent.frontendapi/FrontendApiServer.cs: `ask_id`(absent) + `req_id`(noncode_mention) [上下文行 3]
- 4. docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md:53 -> src/agent.frontendapi/FrontendApiContract.cs: `req_id`(noncode_mention) [上下文行 4]
- 5. docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md:105 -> src/agent.frontendapi/FrontendPromptService.cs: `ask_id`(noncode_mention) [上下文行 3]
- 6. docs/plans/v0.22.0-exp3-step-alignment-validation.md:59 -> src/agent/IndustrialAgentV2.cs: `plan_executor_parallel`(noncode_mention) [上下文行 1]
- 7. docs/plans/v0.22.0-exp9-subtask-plan-routing-and-local-first.md:73 -> src/agent/IndustrialAgentV2.cs: `loop_turn`(noncode_mention) [上下文行 4]
- 8. docs/plans/v0.22.0-r371-capability-probe-python-game.md:250 -> src/agent/IndustrialAgentV2.cs: `empty_always`(noncode_mention) [上下文行 1]
- 9. docs/plans/v0.42.0-r421-polarity.md:18 -> src/agent/IndustrialAgentV2.cs: `recall_query`(noncode_mention) [上下文行 1]
- 10. docs/plans/v0.47.0-r426-relation-judge-localization.md:53 -> src/agent/IndustrialAgentV2.cs: `correction_judge`(noncode_mention) [上下文行 1]
- 11. docs/plans/v0.57.0-r436-e2e-brj-token-kpi.md:18 -> src/agent.modelqueue/ModelQueueRouter.cs: `failed_or_empty`(noncode_mention) [上下文行 2]
- 12. docs/plans/v0.59.0-r439-domain-extension.md:18 -> src/agent/IndustrialAgentV2.cs: `dropped_chars`(noncode_mention) + `local_gate_skip_history`(noncode_mention) + `persisted_chars`(noncode_mention) + `would_be_chars`(noncode_mention) [上下文行 4]
- 13. docs/reports/bge/model-lineage-and-inventory-2026-09-14.md:54 -> src/agent.llamacpp/LlamaCppTextEmbedder.cs: `NullTextEmbedder`(noncode_mention) [上下文行 2]
- 14. docs/reports/function-map-R326.md:288 -> src/agent/contextassembler/ContextAssembler.cs: `_queryEmbedding`(noncode_mention) [上下文行 1]
- 15. docs/reports/r385/capability-inventory.md:24 -> src/agent/registry/CapabilityScanner.cs: `RegisterCapability`(noncode_mention) [上下文行 2]
- 16. docs/reports/r385/chain-map.md:128 -> src/agent/intent/PlanRunner.cs: `AGENTFRAMEWORK_PY_RUN`(noncode_mention) [上下文行 1]

## 上下文明细 (A)

### A1 `AGENTFRAMEWORK_BGE_MODEL` @ docs/plans/v0.22.0-exp1-local-index-and-code-graph.md:68
- doc 原行: 
- 被引文件: `src/agent.llamacpp/LlamaCppTextEmbedder.cs` (sha256 35acfbb82d7b9cca, via resolved)
  - L35 [string_literal]: `var modelPath = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_BGE_MODEL")`
- 树内他处声明文件 (0): (无)
### A2 `VulkanNames` @ docs/plans/v0.22.0-exp1-local-index-and-code-graph.md:288
- doc 原行: 
- 被引文件: `src/agent.gpu/cli/GpuCli.cs` (sha256 5a284f3ac3488825, via resolved)
  - L49 [string_literal]: `o.WriteLine($"vknames{{package={VulkanNames.SilkNetPackage} version={VulkanNames.SilkNetVersion} " +`
  - L50 [string_literal]: `$"windows={VulkanNames.Windows} linux={VulkanNames.LinuxSoname} linux_fallback={VulkanNames.LinuxFallback} " +`
  - L51 [string_literal]: `$"macos={VulkanNames.MacOs} requested_api={VulkanNames.FormatVersion(VulkanNames.ApiVersion)}}}");`
  - L66 [string_literal]: `o.WriteLine($"vkdevice{{index={d.Index} name=\"{d.Name}\" api={VulkanNames.FormatVersion(d.ApiVersion)} " +`
- 树内他处声明文件 (1): src/agent.gpu/VulkanNames.cs
### A3 `req_id` @ docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md:53
- doc 原行: 
- 被引文件: `src/agent.frontendapi/FrontendApiContract.cs` (sha256 b6f75eb1336e2fde, via resolved)
  - L9 [string_literal]: `/// 请求: {"v":1,"type":"req","req_id":"r1","api":"domain.action","payload":{...}}`
  - L10 [string_literal]: `/// 响应: {"v":1,"type":"resp","req_id":"r1","ok":true|false,"payload":{...},"error":{code,msg}?}`
  - L34 [string_literal]: `if (!r.TryGetProperty("req_id", out var rid)) return null;`
  - L54 [string_literal]: `w.WriteString("req_id", reqId);`
- 树内他处声明文件 (0): (无)
### A4 `ask_id` @ docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md:105
- doc 原行: 
- 被引文件: `src/agent.frontendapi/FrontendPromptService.cs` (sha256 8b4c24774722614a, via resolved)
  - L8 [comment]: `/// 出站: 经 FrontendEventHub 发**标准信封** {v,type:event,event:ask,payload:{ask_id,service,purpose,`
  - L29 [comment]: `/// <summary>已答 ask_id 缓存 (幂等重放: 同 id 重复提交不二次投递, 也不误判 unknown)。</summary>`
  - L105 [comment]: `/// <summary>ask.reply / ask.cancel 消费点 (P1-6 幂等: 同 ask_id 重复提交不二次投递)。</summary>`
- 树内他处声明文件 (0): (无)
### A5 `plan_executor_parallel` @ docs/plans/v0.22.0-exp3-step-alignment-validation.md:59
- doc 原行: 
- 被引文件: `src/agent/IndustrialAgentV2.cs` (sha256 52f6f3747df5212b, via resolved)
  - L1910 [comment]: `/// 节点输出对比在执行器并发化 (plan_executor_parallel) 接真 nodeRunner 后进行。`
- 树内他处声明文件 (0): (无)
### A6 `loop_turn` @ docs/plans/v0.22.0-exp9-subtask-plan-routing-and-local-first.md:73
- doc 原行: 
- 被引文件: `src/agent/IndustrialAgentV2.cs` (sha256 52f6f3747df5212b, via resolved)
  - L645 [comment]: `// v0.11.0 R62: executive 直达同样进 loop_turn 打点 (原提前 return 造成度量盲区)`
  - L646 [string_literal]: `agent.config.AgentTelemetry.Emit("loop_turn", "IndustrialAgentV2",`
  - L1750 [comment]: `// 真机证据 (eval/rover/r371d7, empty_always 臂): 轮 1 reply_len=0 / loop_turn.reply_chars=0, 轮 2 才见到文案。`
  - L1850 [string_literal]: `agent.config.AgentTelemetry.Emit("loop_turn", "IndustrialAgentV2",`
- 树内他处声明文件 (0): (无)
### A7 `empty_always` @ docs/plans/v0.22.0-r371-capability-probe-python-game.md:250
- doc 原行: 
- 被引文件: `src/agent/IndustrialAgentV2.cs` (sha256 52f6f3747df5212b, via resolved)
  - L1750 [comment]: `// 真机证据 (eval/rover/r371d7, empty_always 臂): 轮 1 reply_len=0 / loop_turn.reply_chars=0, 轮 2 才见到文案。`
- 树内他处声明文件 (0): (无)
### A8 `recall_query` @ docs/plans/v0.42.0-r421-polarity.md:18
- doc 原行: 
- 被引文件: `src/agent/IndustrialAgentV2.cs` (sha256 52f6f3747df5212b, via resolved)
  - L829 [string_literal]: `agent.config.AgentTelemetry.Emit("recall_query", "IndustrialAgentV2",`
- 树内他处声明文件 (0): (无)
### A9 `relation_judge` @ docs/plans/v0.47.0-r426-relation-judge-localization.md:50
- doc 原行: 
- 被引文件: `src/agent.modelqueue/ModelCatalog.cs` (sha256 6b5a7773824e2ff3, via resolved)
  - L211 [string_literal]: `RelationJudge = ld.TryGetValue("relation_judge", out var rj) && rj is bool rjb && rjb,`
- 树内他处声明文件 (0): (无)
### A10 `turn_gate` @ docs/plans/v0.47.0-r426-relation-judge-localization.md:50
- doc 原行: 
- 被引文件: `src/agent.modelqueue/ModelCatalog.cs` (sha256 6b5a7773824e2ff3, via resolved)
  - L210 [string_literal]: `TurnGate = ld.TryGetValue("turn_gate", out var tg) && tg is bool tgb && tgb,`
- 树内他处声明文件 (0): (无)
### A11 `correction_judge` @ docs/plans/v0.47.0-r426-relation-judge-localization.md:53
- doc 原行: 
- 被引文件: `src/agent/IndustrialAgentV2.cs` (sha256 52f6f3747df5212b, via resolved)
  - L1720 [string_literal]: `agent.config.AgentTelemetry.Emit("correction_judge", "IndustrialAgentV2",`
- 树内他处声明文件 (0): (无)
### A12 `failed_or_empty` @ docs/plans/v0.57.0-r436-e2e-brj-token-kpi.md:18
- doc 原行: 
- 被引文件: `src/agent.modelqueue/ModelQueueRouter.cs` (sha256 08c6179a8af3fb21, via resolved)
  - L227 [string_literal]: `TurnGate.RecordDegraded("failed_or_empty");`
  - L310 [string_literal]: `RelationJudge.RecordFallback("failed_or_empty");`
- 树内他处声明文件 (0): (无)
### A13 `dropped_chars` @ docs/plans/v0.59.0-r439-domain-extension.md:18
- doc 原行: 
- 被引文件: `src/agent/IndustrialAgentV2.cs` (sha256 52f6f3747df5212b, via resolved)
  - L1556 [string_literal]: `("dropped_chars", (long)(sentUserContent.Length - outboundText.Length)),`
- 树内他处声明文件 (0): (无)
### A14 `local_gate_skip_history` @ docs/plans/v0.59.0-r439-domain-extension.md:18
- doc 原行: 
- 被引文件: `src/agent/IndustrialAgentV2.cs` (sha256 52f6f3747df5212b, via resolved)
  - L1553 [string_literal]: `agent.config.AgentTelemetry.Emit("local_gate_skip_history", "IndustrialAgentV2",`
- 树内他处声明文件 (0): (无)
### A15 `persisted_chars` @ docs/plans/v0.59.0-r439-domain-extension.md:18
- doc 原行: 
- 被引文件: `src/agent/IndustrialAgentV2.cs` (sha256 52f6f3747df5212b, via resolved)
  - L1554 [string_literal]: `("persisted_chars", (long)outboundText.Length),`
- 树内他处声明文件 (0): (无)
### A16 `would_be_chars` @ docs/plans/v0.59.0-r439-domain-extension.md:18
- doc 原行: 
- 被引文件: `src/agent/IndustrialAgentV2.cs` (sha256 52f6f3747df5212b, via resolved)
  - L1555 [string_literal]: `("would_be_chars", (long)sentUserContent.Length),`
- 树内他处声明文件 (0): (无)
### A17 `NullTextEmbedder` @ docs/reports/bge/model-lineage-and-inventory-2026-09-14.md:54
- doc 原行: 
- 被引文件: `src/agent.llamacpp/LlamaCppTextEmbedder.cs` (sha256 35acfbb82d7b9cca, via resolved)
  - L34 [comment]: `// 旧默认会让 IsAvailable=false 静默降级到 NullTextEmbedder(空心向量)。默认值必须与部署一致。`
  - L53 [comment]: `///    —— 调用方据此走锚词回退 (与既有 NullTextEmbedder 语义一致);`
- 树内他处声明文件 (1): src/agent.contextgradient/NullTextEmbedder.cs
### A18 `_queryEmbedding` @ docs/reports/function-map-R326.md:288
- doc 原行: 
- 被引文件: `src/agent/contextassembler/ContextAssembler.cs` (sha256 be127d15f5dbc5c3, via resolved)
  - L1420 [comment]: `// R326 (P16): _queryEmbedding 实例字段已消除 — RecallFromSessionAsync 内局部变量 (DI 单例并发串话修复)`
- 树内他处声明文件 (0): (无)
### A19 `RegisterCapability` @ docs/reports/r385/capability-inventory.md:24
- doc 原行: 
- 被引文件: `src/agent/registry/CapabilityScanner.cs` (sha256 c3e2f843b590cb1c, via resolved)
  - L8 [comment]: `///   ①显式注册: RegisterCapability 由宿主/DI 在启动时登记 (代码级技能)`
  - L33 [comment]: `// ① 显式注册通道 (AOT 安全): RegisterCapability 由宿主/DI 在启动时登记。`
- 树内他处声明文件 (0): (无)
### A20 `text_processing` @ docs/reports/r385/capability-inventory.md:56
- doc 原行: 
- 被引文件: `src/agent/intent/PlanRoutePolicy.cs` (sha256 1bea2dc7aa0d8a64, via resolved)
  - L16 [string_literal]: `public const string TextProcessing = "text_processing";`
  - L328 [comment]: `//   · 框架自产的本地节点 (verify_local/text_processing) 不再被追加 (防"验证的验证"递归)`
- 树内他处声明文件 (0): (无)
### A21 `verify_local` @ docs/reports/r385/capability-inventory.md:56
- doc 原行: 
- 被引文件: `src/agent/intent/PlanRoutePolicy.cs` (sha256 1bea2dc7aa0d8a64, via resolved)
  - L13 [string_literal]: `public const string VerifyLocal = "verify_local";`
  - L328 [comment]: `//   · 框架自产的本地节点 (verify_local/text_processing) 不再被追加 (防"验证的验证"递归)`
- 树内他处声明文件 (0): (无)
### A22 `OpenAILLMCaller` @ docs/reports/r385/chain-map.md:51
- doc 原行: 
- 被引文件: `src/agent/extensions/ServiceCollectionExtensions.cs` (sha256 3ce4f21162013205, via resolved)
  - L43 [comment]: `// HttpClient (OpenAILLMCaller/搜索插件共享)`
- 树内他处声明文件 (1): src/agent/IndustrialAgentV2.cs
### A23 `AGENTFRAMEWORK_PLAN_EXEC` @ docs/reports/r385/chain-map.md:127
- doc 原行: 
- 被引文件: `src/agent/intent/PlanRunner.cs` (sha256 f02437a7e931c01b, via resolved)
  - L301 [comment]: `/// 闸门: `AGENTFRAMEWORK_PLAN_EXEC=0|false|off` 回退哑体 (同题对照用), 缺省开启。`
  - L308 [string_literal]: `public const string EnableEnvName = "AGENTFRAMEWORK_PLAN_EXEC";`
- 树内他处声明文件 (0): (无)
### A24 `AGENTFRAMEWORK_PY_RUN` @ docs/reports/r385/chain-map.md:128
- doc 原行: 
- 被引文件: `src/agent/intent/PlanRunner.cs` (sha256 f02437a7e931c01b, via resolved)
  - L39 [comment]: `/// <summary>运行级闸门 (null = 读 AGENTFRAMEWORK_PY_RUN)</summary>`
- 树内他处声明文件 (0): (无)
### A25 `RegisterCapability` @ docs/reports/r385/consolidation-candidates.md:19
- doc 原行: 
- 被引文件: `src/agent/registry/CapabilityScanner.cs` (sha256 c3e2f843b590cb1c, via resolved)
  - L8 [comment]: `///   ①显式注册: RegisterCapability 由宿主/DI 在启动时登记 (代码级技能)`
  - L33 [comment]: `// ① 显式注册通道 (AOT 安全): RegisterCapability 由宿主/DI 在启动时登记。`
- 树内他处声明文件 (0): (无)
