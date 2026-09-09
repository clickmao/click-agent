# AgentFramework 全能力总结 + 功能重复排查 + 内存/性能优化候选清单 (R326, v0.15.2)

> 生成: 2026-09-10 · 只读审计 (git log @ 447b00a / 546 tests / v0.15.2)。依据:
> docs/architecture.md (§11 组件层) + docs/improvements.md + docs/api.md (§19-23,28-30) + README.md +
> src/ 实际代码逐文件核对 (grep 调用链验证接线, 非仅文档转述)。
> 铁律遵守: 功能重复**仅报已确认语义重叠者**; 无重复的组明确写"无重复不强归拢";
> 全部"死代码/未接线"结论均有 grep 消费者证据行, 供复核。
>
> **接线状态图例**: ● 主链运行 (V2 OnProcessAsync 可达) · ◐ 库面 API/设计实现+单测、主链未接线 · ○ 已注册 DI/字段注入但无消费方 (dormant)。

---

## 0. 版本与 ★ 标定口径

| 版本 | 轮段 | 主题 | 本文 ★ 覆盖 |
|---|---|---|---|
| v0.14.0 | R318-R321 | 输出侧经验闭环 (OutputCritic / SelfCritic / FixMemory / CriticPipeline / T2d 接线) | ★ |
| v0.15.0 | 规划轮 | 任务生命周期设计 (仅计划文档, 无代码) | — |
| v0.15.1-a/b | R322 | TaskCharter 任务章程 + 新输入三态路由 + 精确用例族 (C22-26) | ★ |
| v0.15.2 | R323-R326 | GuardrailMemory 警告记忆 + 域语义 + 注入链 + KPI-2 常设监控 (R324) + C27-C31 | ★ |

★ = v0.14.0–v0.15.2 新增或新接线的运行时代码 (eval/工具侧变更单列并注明非运行时代码)。

---

## 1. 全能力地图 (归组)

### 1.1 主题牵引 (上游锚 S1-S4 + 中游牵引 M + 下游 D 全链)

| 能力 | 位置 (文件/类) | 语义 | 接线 | ★ |
|---|---|---|---|---|
| S1 任务目标锚 (GoalProfile) | agent/session/SessionMemory.cs (GoalProfile/SetGoal/RenderForPrompt), Session.cs | 会话级 Goal: GoalText/KeyEntities/Constraints/Milestones; 首轮任务句锚定、pivot 重锚、里程碑滚动 | ● (V2 L632/L982-1002) | |
| S2 画像核心主题 (coreTopic) | agent/tendency/TendencyData.cs (TendencyAnalyzer.GetContextBiasAsync/BiasScores) | 用户主题倾向 top-1 作会话核心主题; max-based 置信 (R133) | ● (V2 L621-623; ContextAssembler UserTendency 源) | |
| S3 意图 | agent/intent/IntentDecomposer.cs, IntentRecognizer.cs | 规则意图识别 + 子任务拆解 (连接词/关系) | ● (V2 L519-520) | |
| S4 下轮预估 (forecast) | agent/registry (NextTurnForecast) | 上轮任务摘要/意图/倾向 → 下轮提示头 | ● (V2 L744-747) | |
| 合并相关度判定 TopicRelevanceEvaluator | agent/intent/TopicRelevanceEvaluator.cs | R308 统一 verdict (Normal/SteerHint/Isolate); 实体重叠±2/意图差+1/离题词+1; 指代绝对 veto/短询问分级 veto; 无锚词面模式 (R312/R313 精修) | ● 一份 verdict 三路消费 (V2 L647/L678/L794-808) | |
| 评分引擎 TaskRelevanceChecker | agent/intent/TaskRelevanceChecker.cs | evaluator 唯一调用方; 归一化+词表+4-gram 实体重叠+短问句元问询信号 | ● (仅 evaluator 调) | |
| L1 轻牵引 (SteerHint 尾追加) | IndustrialAgentV2.cs L922-957, L1028-1031 | 连续偏题 ≥2 轮 (env 阈值) → 回复尾一句衔接提示; 区段路由后追加 | ● | |
| L3 主动澄清 (clarify 问句) | IndustrialAgentV2.cs L944-957, L1028-1029 | 偏题 ≥ 澄清阈值 → 二选一问句; pulled_back 打点 + 2 轮撤防 (R314/R315) | ● | |
| 会话级牵引状态机 | IndustrialAgentV2.cs (_consecutiveDrift/_clarifyArmed/_clarifyTurnsLeft, static) | 进程级漂移计数与澄清武装 | ● | |

### 1.2 输出自审 (v0.14.0 第四环, 输出侧经验闭环) ★

| 能力 | 位置 (文件/类) | 语义 | 接线 | ★ |
|---|---|---|---|---|
| 静态规则自审 OutputCritic | agent/critique/OutputCritic.cs | R01-R08 C# 反模式正则静态扫描 (循环 new[]/+= /async void/.Result/空catch/Count()/double==/未using), 证据带行号, 只提示不改写 | ◐ 类+14 单测齐备; **主链无调用点** (V2 无 Review/Render 消费; C26 负样本断言零触发因此恒过 — 观测面待补) | ★ |
| LLM 自审调用器 SelfCritic | agent/critique/SelfCritic.cs | 单次额外 LLM 调用, 强制 JSON {quote,mechanism,severity,fix_hint}; quote 逐字子串反幻觉锚 | ◐ 类+7 单测; **无主链 LLM 调用点** (未接线) | ★ |
| 三级过滤装配 CriticPipeline | agent/critique/CriticPipeline.cs | 静态=确认态 / LLM+静态或+库=双源确认 / LLM 单源=观察态不入上下文 | ◐ 类+单测; 主链未接线 (仅 CriticPipelineTests) | ★ |
| 修法记忆 FixMemory | agent/critique/FixMemory.cs | (反模式→机制→修法), 来源秩 human_review>metric_delta>llm_self_confirmed, pattern 归一化合并 confirmations++, JSON 落盘 | ● 生成前预渲染注入 (V2 L1601-1624, DataSourceType.FixMemory); Write 入口现仅测试/库内 (CriticPipeline 未接 → 生产 Write 源缺失) | ★ |
| 修法记忆注入源分支 | agent/contextassembler/DataSourceType.cs + ContextAssembler.cs L167-182 | FixMemoryBlock host 预渲染 → 装配 snippet (rel 0.92) | ● (V2 L1604-1619) | ★ |
| K1 隔离对齐 | IndustrialAgentV2.cs L1543-1548 | K1_FULL_ISOLATION=1 剔除 FixMemory (经验注入属对照实验排除面) | ● | ★ |

### 1.3 任务路由 (v0.15.1, 任务生命周期) ★

| 能力 | 位置 (文件/类) | 语义 | 接线 | ★ |
|---|---|---|---|---|
| 任务章程 TaskCharter | agent/tasks/TaskCharter.cs | goal/entities/acceptance-criteria/scope-out/pending-inputs; 状态机 planning→running→accepting→done/failed; STJ source-gen 落盘 data/task-charters/active.json; Archive=先存终态再 Move (R322b) | ● 每轮 LoadActive (V2 L571) | ★ |
| 新输入三态路由 | IndustrialAgentV2.cs L565-612 (块 1.39, 隔离判定前) | 章程活跃时: supplement→PendingInputs 持久化 / isolate→既有隔离链 / pivot(词表)→Archive failed; 判定复用 TopicRelevanceEvaluator (charter 锚); 无章程零行为 | ● (task_input 打点) | ★ |
| PendingInputs 注入依据 | TaskCharter.PendingInputs | 主题补充暂存, 下轮循环注入依据 (持久化跨进程); 任务终态清空 | ● (当前只有写侧; 读侧注入下游循环尚未实现 — v0.15.1 设计遗留, 观察项) | ★ |

### 1.4 记忆类 (存储/召回按语义分层)

| 能力 | 位置 (文件/类) | 语义 | 接线 | ★ |
|---|---|---|---|---|
| 会话即时历史 | agent/session/Session.cs (Session/Message 列表) | 内存会话消息 (≤100 条裁剪), AddToSessionAsync 通道 | ● (V2 L1774-1838; 历史经 GetConversationHistoryAsync 专通道进 prompt) | |
| 会话长期记忆+目标画像 | agent/session/SessionMemory.cs + SessionMemoryStore.cs (JsonSessionMemoryStore) | 滚动摘要 ≤1000 字符 + GoalProfile + 里程碑, data/sessions/<id>_memory.json, 损坏容错 | ● (V2 L965-1009 回写; L1580-1599 预渲染注入) | |
| 情节记忆 (QA 对) | agent.rag/RAGConfig.cs (RAGRecall) + agent/vectormemory/VectorDocument.cs (VectorStore) | 每轮 Q:A 双写两库; 召回只走 RAG (R6 双写保证) | ● 写双库 (V2 L1722-1757); RAG 召回经装配 Memory 源 | |
| think-memory 联想库 | agent.exploration/ThinkMemory.cs | 问题向量库 + 负样本降权 + 30 天衰减 + 引用 boost; STJ source-gen 落盘 data/think-memory.json (进程级单例, 启动加载) | ● (V2 L824-900 recall+write+Save) | |
| 警告/铁律记忆 GuardrailMemory | agent/critique/GuardrailMemory.cs | 逻辑三元组 condition/prohibition/exception + domain + origin case; domain+pattern 双键 recall; "general" 域=全域触发 (R324b 语义); 来源秩 human_warning>review>metric; data/guardrails.json | ● | ★ |
| 警告语义写入链 (块 1.38) | IndustrialAgentV2.cs L534-563 | 用户警告词表 (不要/禁止/别再…) → 规则抽取禁令(≤40ch)+pattern(ExtractEntities top3) → Write(human_warning) | ● | ★ |
| 警告预渲染注入 | IndustrialAgentV2.cs L1626-1652 + ContextAssembler L184-199 | GoalText 域锚 + Recall(topK2) + 同会话去重 HashSet (habituation 防护) + K1 门 | ● | ★ |
| 粘性路由记忆 StickyRouteMemory | agent.exploration/StickyRouteMemory.cs | 问题 embedding+意图+实体指纹三门判定, 成功模型优先/失败回避, TTL 72h | ◐ 类+11 单测; **ModelQueueRouter 无消费点** (README/improvements 记 F2 落地, 实际未接 Router — 审计发现) | |
| 画像/档案类 | agent/tendency/TendencyData.cs (TendencyData+持久化), agent/registry (AgentProfileStore/AgentProfile) | 用户主题/风格倾向历史 (带衰减) / agent 画像任务胜率+工具亲和 | ● | |
| 遗留记忆栈 (整体 dormant) | agent/memory/*: MemoryStore, AgentMemoryStore, LongTermMemory, ShortTermMemory, Summarizer, MemoryRecall | 设计期 IMemoryStore 双实现+文件层+摘要器; DI 注册 (IMemoryStore/IAgentMemoryStore/ISummarizer) 但 **V2 主链零消费**; host 冒烟仅 GetRequiredService 探活 | ○ (无消费方 — grep 全仓验证) | |
| 向量记忆接口 (遗留) | agent/vectormemory/VectorDocument.cs (IVectorMemoryRecall/VectorMemoryRecall) | 语义召回 (词频 hash/bge), DI 注册 | ○ V2 字段 _memoryRecall 注入后**从未调用** (grep 零引用); host 探活 | |

### 1.5 上下文装配

| 能力 | 位置 (文件/类) | 语义 | 接线 | ★ |
|---|---|---|---|---|
| 多源上下文组装器 | agent/contextassembler/ContextAssembler.cs | 10 源并行召回 (DataSourceType: Memory/Session/WebSearch/UserTendency/WorkspaceFiles/SessionMemory/AgentContext/FixMemory/GuardrailMemory/ToolOutput), 相关过滤→配额→梯度压缩→分组头拼装 (≤5 源×2 条/≤200tok), per-source 打点, 5min 结果缓存 | ● (V2 L1555-1679) | |
| 源映射 | agent/intent/IntentSourceMapping.cs + IntentDecomposer.AggregateSources | 意图→启用源集合 (基础 Memory+UserTendency; search/general 加 Web/Workspace) | ● | |
| 体积治理 | ContextAssembler.cs RecallFromMemoryAsync L608-621 | Memory 源 500tok 预算 + rel<0.4 只留 best1 (R117) | ● | |
| 混合相关分 | agent.contextgradient/MessageRelevanceScorer.cs | 词面 0.6 + bge 余弦 0.4 (P3), 词面保底 | ● (Session 源内; 该源主链默认不启用) | |
| host 预渲染块×4 | V2 (SessionMemoryBlock/FixMemoryBlock/GuardrailBlock/AgentContextBlock) → DataSourceType.cs | 目标锚/经验/铁律/画像块在装配器外渲染成整块 snippet (rel 0.95/0.92/0.95/0.9, pinned 免压缩) | ● | ★ (FixMemory/GuardrailMemory 两块为 v0.14/v0.15.2) |

### 1.6 探索链 (v0.13.x)

| 能力 | 位置 (文件/类) | 语义 | 接线 | ★ |
|---|---|---|---|---|
| 上下文预算门 ContextBudgetGate | agent.exploration/ContextBudgetGate.cs | est vs WARN 6000/HARD 9000; Normal/IsolatedMicro/HardDrop 三态 + 防抖 | ● (V2 L769-774) | |
| 渐进式探索规划 | agent.exploration/ExplorationPlanner.cs + ExplorationConfig.cs | 五源 (ContextBlock/Text/Url/Directory/File) 优先级队列 + per-source/全局步数预算 + 去重 | ● (RunThinkChainAsync L113-164) | |
| 宿主执行器 | agent.exploration/HostExploreExecutor.cs | URL 只读 GET (10s, title+正文 ≤2KB digest, 页内发现 ≤5) / 目录文件路径穿越防护 / 文本直返 | ● | |
| 思考链宿主循环 | IndustrialAgentV2.RunThinkChainAsync (V2 L113) | URL 播种 (排除 example.com) → 4 步/4s 预算 → 首败即停 → digest 回注 (AGENTFRAMEWORK_EXPLORE=0 全关) | ● (think_chain 打点) | |
| 关键文档激活链 | agent.exploration/LinkRegistry.cs | 三信号预判 (锚定/稀缺出链/路径递进) ≥3 激活 + 父链保护 | ● (V2 L853-881) | |
| 微步骤隔离执行 | agent.exploration/MicroStepSession.cs + V2.RunMicroStepsAsync (L174) | gate=IsolatedMicro 时子任务→微问询 (不带主上下文) → 回注 ≤200tok/条, 连续失败升级 | ● (gate 判定后 V2 L814-817) | |
| 收敛判据 ThinkChainSession | agent.exploration/ThinkChainSession.cs | ExecuteStepAsync/EvaluateConvergence (自评/预算/无新发现×2/证据分) | ◐ ExecuteStepAsync 被 V2 循环使用; **EvaluateConvergence/SeedFromMemory 无主链调用点** | |
| 复杂度门/证据分 | ComplexityGate.cs / EvidenceScorer.cs | 复杂任务展开判据; 多源对比单源封顶 0.65 | ◐ **主链无调用点** (仅 ThinkChainTests) | |

### 1.7 隔离 (多语义轴 — 见 §3 判定"无重复不强归拢")

| 能力 | 位置 | 语义 | 接线 | ★ |
|---|---|---|---|---|
| 话题无关隔离 (1.4) | V2 L630-703 + agent/subagent/IsolatedTaskRunner.cs | verdict=Isolate → 独立 SessionId/零主记忆/一次性 Uid/静默问询/带标记返回; 并发 2 信号量 | ● | |
| 任务路由隔离 | 见 §1.3 (charter Isolate 路由点) | 复用既有 1.4 链 | ● | ★ |
| 微步骤隔离 | 见 §1.6 | 上下文预算轴 | ● | |
| K1 实验隔离 | V2 L1543-1551 + ContextAssembler L831-839 | env 剔除画像/记忆/修法源 (FULL_ISOLATION / K1_DISABLE) | ● | ★ (FixMemory 入剔除面) |
| 领域联想抑制 (guardrail) | GuardrailMemory.MatchesDomain | domain+pattern 双键, 跨域不触发 (general 例外) | ● | ★ |
| 遗留 SubAgent/池 | agent/subagent/SubAgent.cs (SubAgentPool/ISubAgentPool) | 设计期任务并行池 (MaxAgents=4) | ○ DI 注入 V2 但无消费方 (TaskPlan 主链未用池) | |

### 1.8 压缩防护 (contextgradient)

| 能力 | 位置 (文件/类) | 语义 | 接线 | ★ |
|---|---|---|---|---|
| 梯度压缩 | agent.contextgradient/ContextGradientCompressor.cs (L0-L3 + A3 关键句保护 + 主题聚类 + 三重漂移校验, bge cos) | 装配时每超限 snippet 压缩 (ContextAssembler.L1017) | ● | |
| D1 异常隔离 | ContextAssembler.cs L1028-1037 | per-snippet catch → 回退原文 + compression_error | ● | |
| D2 数字/URL 哨兵 | ContextGradientCompressor (ExtractSentinels) | 数字串/日期/SN/URL 压缩前提取, 丢失→降级 | ● (compression_sentinel) | |
| D3 降级链 | 内嵌 D2 (当前级→RuleCompress→原文) | ● | |
| D4 熔断器 | agent.contextgradient/CompressionBreaker.cs | 阈值 5/冷却 60s/半开单试/成功复位 | ● (ContextAssembler L1006-1014, L1057) | |
| 不可变源/压缩 audit | agent.host/Program.cs (--compression-audit) | ground-truth 104 篇分档校验 CLI | ● (工具) | |
| 遗留压缩器 (整体 dormant) | agent/tokencompression/ITokenCompressor.cs (TokenCompressor) | CountTokens/Truncate/Summarize/Selective/Smart/Incremental 六策略 | ◐ 主链仅用 **CountTokensAsync** (ContextAssembler L1041); 压缩本体全被梯度压缩取代 | |
| 遗留摘要器 | agent/memory/Summarizer.cs (ISummarizer) | 关键事实/决策正则摘要 | ○ 零消费 (仅 DI) | |

### 1.9 RAG

| 能力 | 位置 (文件/类) | 语义 | 接线 | ★ |
|---|---|---|---|---|
| RAG 召回主链 | agent.rag/RAGConfig.cs (RAGRecall: RecallAsync/IndexAsync/Stats) | 三口径: bge 向量 (cos) / 词袋长查询 (IDF 稀缺加权) / 短查询对抗 (RagDedup 归一化); 命中 chunk 映射回父文档 (长文 440ch 切块); JSONL 持久化 + 512 行裁剪 + 内容去重 (R109) | ● (装配 Memory 源 + V2 每轮 Index) | |
| RAG 数据文件指定 | RAGConfig.PersistPathOverride / CLI -rag / /rag / env 三入口 (V2 L380-414) | 运行时切换持久路径 | ● | |
| 用户反馈持久化 | agent.rag/UserFeedback.cs (IFeedbackPersistence/FeedbackPersistence) | 任务环 RAG 反馈写回 | ◐ (契约在, DI 注册) | |

### 1.10 兜底

| 能力 | 位置 | 语义 | 接线 |
|---|---|---|---|
| 模型兜底链 F1 | agent.modelqueue/ModelQueueRouter.cs (L464-503 段) + FallbackConfig.cs | 429/重试耗尽后按 cost_quality 序逐个备选 + VerifyReply (非空/错误模板/最短长度) + fallback_attempt/verify_fail 打点 | ● (fallback_attempt 打点在 Router) |
| 429 感知调度 | ModelQueueRouter | 限流跳过同模型重试直切备 | ● |
| 选模策略 | agent.modelqueue/ModelSelectionPolicy.cs (auto 三层: 性能不敏感→最便宜 / fitness+推理+编码−费用 / key 过滤) | ● |
| 余额链 | TokenUsageService.cs + BalanceQueryService.cs | 初始化真 API 同步→本地累计→10 万 token 阈值再同步; EstimateBalance+切模+flags | ● |
| 搜索故障转移 | agent/search/SearchFailoverService.cs (5 provider 槽位 + 熔断 + 槽位提升 + 结果缓存) | 免费源优先, 付费源有 key 参与; 问询补凭据 | ● |
| 本地推理通道 | agent/llamalocal/LocalLlamaCaller.cs + agent.modelqueue/ILocalInference.cs (LocalInferenceAdapter) | 本地 gguf > 官方 > 远端三通道首位; IsAvailable 诚实降级 | ● (批测强制 env 关闭) |
| 重试/退避 | ModelQueueRouter (瞬态分类+指数退避) | ● |

### 1.11 召回 (RAG 内部三口径已在 §1.9; 其余召回器)

| 能力 | 位置 | 语义 | 接线 |
|---|---|---|---|
| Memory 源召回 | ContextAssembler.RecallFromMemoryAsync (RAGRecall) | TopK10 → 500tok 预算/低相关收缩 | ● |
| Session 源召回 (关键词+向量混分) | ContextAssembler.RecallFromSessionAsync | 命中≤10 条或最近 5 条兜底 | ◐ 主链源默认不含 Session (IntentSourceMapping) — 历史走专通道 |
| 工作区召回 | ContextAssembler.RecallFromWorkspaceAsync | ≤300 文件/3 命中片段, rel 按命中数比例化 | ● (file 类意图) |
| 联想召回 (think-memory) | ThinkMemory.Recall | 见 §1.4 | ● |
| 规则/词面召回 | FixMemory.Recall / GuardrailMemory.Recall / 修法&铁律 (包含匹配+confirmations 序) | ● |
| 遗留召回器×2 | agent/memory/IMemoryRecall.cs (MemoryRecall) + vectormemory VectorMemoryRecall | 均为"包装底层召回→映射条目" | ○ 零消费 |

### 1.12 其余支撑能力 (简表)

| 组 | 能力要点 | 位置 | 接线 |
|---|---|---|---|
| 意图/计划 | 意图拆解(19 连接词)/创作类拦截/影子计划 (TaskPlanBuilder+TaskPlanExecutor 哑跑, /plan)/EvidenceGate→ClarificationBatch 批量问询/约束提取/敏感意图 | agent/intent/*, agent/registry/* | ● |
| 模型调度 | 三通道+22 模型目录+manual 覆盖+ModelVerify/ModelCatalog+OpenAI 兼容 DTO (视觉 parts) | agent.modelqueue, agent/modelqueue | ● |
| 视觉/渲染 | 图像理解链 (base64 data URL/重路由); IImageRenderPlugin (SkiaSharp 默认/SvgText 兜底)+LocalSvgRenderer DSL+收敛环 | agent.modelqueue/ImageRenderPlugins/* | ● (生成路径 CogViewClient 保留弃用) |
| Skill | SKILL.md 包 (Anthropic 开放标准)+四触级 (关键词/正则/领域/bge cos≥0.45)+真进程脚本执行 (沙箱/超时杀树/环境白名单) | agent.skills/* | ● |
| 搜索 | 5 provider 插件 + 内容抽取 (WebReaperContentExtractor) + SharedHttp | agent/search/* | ● |
| 会话/恢复 | SessionManager (内存会话); ExecutionCheckpoint 原子落盘+CheckpointRecovery | agent/session, agent.recovery | ● (TaskPlan 节点级) |
| 输出/日志 | IOutputSink 统一出口 (库内零 Console 直写); IChatboxSink/@cmd 协议; LogRouter 四通道; SpectreOutputRenderer; 区段路由+UiCapture/CodeReview 插件 | agent.host, agent.output, agent.logging, agent/registry (ResponseSegmentRouter) | ● |
| agent.io | @cmd 行协议 + 三传输 (Console/共享内存 mmap/TCP Socket) + @stream 流式块 | agent.io | ● |
| 配置 | 四层 YAML (base→env→modules→runtime) Yamlify 零反射; ConfigWriter L3/L4 写; ConfigModelBinder 强类型绑定 | agent.config | ● |
| 打点 | AgentTelemetry JSONL 12+ 点位 (30+ point 字段: topic_relevance/context_gate/think_chain/link_activation/compression/fix_memory/guardrail/task_input...) | agent.config/AgentTelemetry.cs | ● |
| 工具侧 (非运行时) | eval/run_round.py 断言族 C01-C31 + run_case_with_setup (R322b) + explore_eval A/B + eval/token_report.py (R324 KPI-2 每 10 批) + negation 围栏双脚本同步 | eval/* | ◐ 评测 |

---

## 2. 接线状态审计发现 (能力地图最值得注意的部分)

以下"实现存在且有单测、但主链未接线/无消费方"结论均经全仓 grep 验证:

1. **v0.14.0 输出自审三件套未进主链**: OutputCritic / SelfCritic / CriticPipeline 无任何 IndustrialAgentV2/ContextAssembler/宿主调用点 (src 全量 grep, 仅 critique/ 自身与 agent.tests/ 引用)。主链已接的只有 T2d (FixMemory 生成前预渲染, §1.2)。C26 (无代码块零触发) 由此**恒过** — 负样本断言未绑定到真实自审触发面 (观测价值待补; 触发侧接线是 v0.14 计划内的后续轮工作, 此处如实记录, 非缺陷定性)。
2. **StickyRouteMemory 未接入 ModelQueueRouter**: 全仓仅 StickyRouteMemoryTests 引用; Router 内无 sticky 消费 (README "兜底粘性路由 v0.13.1" 描述的 Router 侧接线未落地)。FallbackConfig/F1 兜底链本身已接线。
3. **ComplexityGate / EvidenceScorer / ThinkChainSession.EvaluateConvergence** 无主链调用点 (仅 ThinkChainTests); V2 探索循环用自有的 4s/4 步/首败即停收敛。
4. **agent/memory 传统记忆栈整体 dormant**: MemoryStore、AgentMemoryStore、LongTermMemory、ShortTermMemory、Summarizer、MemoryRecall (agent.memory) 均注册 DI (IMemoryStore/IAgentMemoryStore/ISummarizer), 但 V2 主链零消费; agent.host 冒烟只是 GetRequiredService 探活。主链记忆 = RAGRecall + SessionMemory + 各类进程级 JSON 库。
5. **agent.keywordannotation (KeywordIndex/KeywordTagger)** dormant: RAGRecall 自持关键词倒排 (RAGConfig.UpdateKeywordIndex), keywordannotation 无消费方。
6. **IVectorMemoryRecall (VectorMemoryRecall)** dormant: V2 构造注入 _memoryRecall 后从未调用; _vectorStore 仅写 (StoreToMemoryAsync) 无读; _subAgentPool 注入后无调用。
7. ThinkMemory 每次 Recall 命中写盘 `_thinkMemory.Save` 每轮 (V2 L896) — 见 §4.9。

> 处理建议遵循铁律: 以上**不推荐合并任何活能力**; dormant 项仅建议"要么接线、要么按清理流程退役/归档", 与活跃路径无功能冲突。

---

## 3. 功能重复排查

### 3.1 确认真实重复 (语义重叠, 有证据)

**R-1 pivot/转向词表 3 份拷贝 (已发散)**
- 位置: `IndustrialAgentV2.cs` L575 (块 1.39 routePivotMarkers)、L637 (块 1.4 pivotSkipMarkers)、L976 (SessionMemory 重锚 pivotMarkers)。
- 证据: 三表 13-14 项基本同词 (不要之前/放弃/算了/改成/换成/不要了/还是做/换一个…); **已发散**: "不管之前"仅 L637 有, L575/L976 无 — 语义分裂 (同一"用户转向"输入在三处得到不同判定)。
- 结论: **真重复**。建议收敛为单一共享 `static readonly string[] PivotMarkers` (agent.intent 或 V2 常量), 三处引用同一数组。属收敛词表非合并功能, 不违铁律。

**R-2 legacy 记忆栈内部双份内存实现**
- 位置: `agent/memory/MemoryStore.cs` (IMemoryStore, Dictionary+lock) vs `agent/memory/AgentMemoryStore.cs` (IAgentMemoryStore, Dictionary+lock), 均注册 DI 单例, 均存 MemoryEntry, 均无主链消费 (§2.4)。
- 结论: **真重复** (同一角色的两个内存存储接口+实现, 语义完全相同)。二者与 LongTermMemory/ShortTermMemory (又两个 IMemoryStore 实现, 文件化, 均 dormant) 构成 4 份"记忆存储"实现。
- 建议 (遵循铁律的清理而非强归拢): 主链记忆走 RAG+SessionMemory; legacy 四实现只服务 DI 冒烟与测试 — 建议保留其中一个接口作为公共契约或整体退役, **不合并任何在线能力**。

**R-3 HashEmbeddingProvider 同名双实现 + 双 bge 加载器**
- 位置 A: `agent.vectormemory/EmbeddingProvider.cs` HashEmbeddingProvider (dim 384);
- 位置 B: `agent/llamalocal/EmbeddingRouter.cs` L190 自带 HashEmbeddingProvider (dim 256, "hash-fallback")。
- 语义重叠: 同一"词频 hash 向量"概念两个独立实现 (维度还不同 → 若混用向量空间不一致, 幸而各走各的)。
- bge 双加载: `agent/llamalocal/BgeEmbedder.cs` (ITextEmbedder, DI 注入 ContextGradientCompressor+TriggerMatcher) 与 `EmbeddingRouter → agent.vectormemory.BgeEmbeddingProvider.Create` (RAG EmbeddingFunction, DI 注入 RAGConfig) 各自持有一个 LLamaEmbedder 实例 — 进程内**两份 bge 模型加载** (每份数百 MB 级内存)。R129 曾修"每次调用 new Router 重复加载", 但两链路的实例级重复仍在。
- 结论: hash 双实现=真重复; bge 双加载=真内存重复。建议: 统一到一个共享 embedding 服务 (DI 单例, 双接口适配), 消除第二份模型驻留。此为合并**基建重复**非功能归拢, 仍标注由用户裁定。

**R-4 死召回器与活召回器的重叠**
- 位置: `agent/memory/IMemoryRecall.cs` MemoryRecall + `vectormemory/VectorDocument.cs` VectorMemoryRecall vs 活链 `RAGRecall`。
- 语义: 三者都做"按 query 召回记忆条目"; MemoryRecall 内部即包 `_ragRecall.RecallAsync` 再按 Id 映射 (映射到无人写入的 AgentMemoryStore, 必空)。VectorMemoryRecall 包 IVectorStore。
- 结论: 功能重复 + 死链 (零消费)。建议清理/退役, 召回统一 RAGRecall + think/rule 各语义层。

**R-5 上下文压缩三实现**
- 位置: `agent/tokencompression/ITokenCompressor.cs` (TokenCompressor 六策略) vs `agent.contextgradient/ContextGradientCompressor.cs` vs `agent/memory/Summarizer.cs` (ISummarizer)。
- 语义: 都是"长文本按预算压缩/摘要"。主链压缩已全部走梯度压缩器 (ContextAssembler L1017); TokenCompressor 仅 CountTokensAsync 存活; Summarizer 零消费。
- 结论: **能力重复但主链已定于一尊** — 不存在双活竞争 (v0.11.0 曾为此做过 sync-over-async 清剿, 现存仍为历史双轨)。建议: 保留梯度压缩为唯一活实现, legacy 两压缩器按退役流程处理, 不合并逻辑。

**R-6 会话/情节记忆双写 (设计性冗余)**
- 位置: `IndustrialAgentV2.cs` L1738 `_vectorStore.StoreAsync` + L1744 `_ragRecall.IndexAsync` 每轮写同一 Q:A。
- 语义: R6 为修"召回率恒 0%"做的双写保证; 现状召回只读 RAG (VectorStore 无读侧消费者) → **写侧一半成为纯开销** (每轮一次额外 store + 潜在索引维护)。
- 结论: 记录为设计性重复; 建议评估移除 VectorStore 写侧 (或使其只服务将来真向量检索面), 每轮省一次写 + 一次向量生成。不是强制归拢。

### 3.2 机制同构、语义不同 (模板机会, 不判重复)

| 同构模式 | 实例 | 为什么不算功能重复 |
|---|---|---|
| host 预渲染注入块 ×4 | SessionMemoryBlock / AgentContextBlock / FixMemoryBlock / GuardrailBlock (V2 L1580-1652, DataSourceType.cs, ContextAssembler L133-199) | 四块内容语义各自独立 (目标锚/画像/修法/铁律), 只是共享"渲染→snippet→rel 常量"代码形; 建议抽公共 helper (含 rel/配额/pinned 语义) 而非合并数据 |
| 熔断/重试/超时模式 ×4 | ModelQueueRouter (429/退避重试) · SearchFailoverService (ProviderHealth 熔断+槽位) · CompressionBreaker (D4 半开) · HostExploreExecutor (10s 超时) | 四个不同失败域 (LLM 限流/搜索源/压缩/网络抓取), 语义各自成立; 建议未来抽通用 CircuitBreaker 组件, 现状**不归拢** (铁律) |
| 隔离语义 ×5 轴 | 话题隔离 (TaskRelevance) · charter 路由隔离 · 微步骤隔离 (BudgetGate) · K1 实验隔离 (env) · guardrail 域抑制 | 轴心完全不同 (任务无关/任务输入路由/上下文预算/对照实验/联想域), 判定器已共享 (R308 evaluator 单点 / ContextBudgetGate 单点), 属收敛完成态 → **无重复不强归拢** |
| 上下文注入"多源" | DataSourceType 10 源 + 会话历史专通道 | 各源唯一召回语义; Session 源与历史通道本为同批消息, 主链已避免双路同注 (ContextAssembler L1571 注释 + IntentSourceMapping 不含 Session) → 运行时无重复注入 |

### 3.3 明确"无重复不强归拢"组 (逐一核对后)

- **记忆存储分层**: Session 即时历史 (内存消息) / SessionMemory (滚动摘要+Goal, 每会话一文件) / RAG 情节库 (跨会话检索) / 各进程级规则库 (think/fix/guardrail/sticky) — 每层有独立存储键、召回语义与生命周期, 无两处做同一件事 → **无重复不强归拢**。
- **召回三口径** (bge 0.95/词袋长 0.70/短查询对抗 0.45): 同一 RAGRecall 内按查询形态分档, 非三个独立召回器 → 无重复。
- **上下文压缩双活核查**: 主链只活 ContextGradientCompressor (R-5 已列 legacy 为单轨死实现, 不构成双活重叠)。
- **兜底**: Router 兜底 (LLM 域) vs 搜索槽位故障转移 (搜索域) vs 429 切备 (限流域) — 域异 → 无重复。
- **隔离判定单点化已达成**: TopicRelevanceEvaluator 是唯一 Check 消费点 (R308b 审计已收口: 直调 Check=0), ContextBudgetGate 是唯一预算判定 — 无重复可报。

---

## 4. 内存/性能优化候选清单

> grep 范围: `src/*` 排除 obj/bin/tests; 模式 `.Result`/`.Wait(`/`GetAwaiter().GetResult()`、`async void`、同步 over async、循环内 string `+=`、循环内大对象 new。已排除字段名 `.Result` (数据对象)、`WaitAsync` (正确用法)、注释/接口文档。热路径=沿 V2 OnProcessAsync 调用链可达且每轮/每装配触发。

### 4.1 阻塞 (sync-over-async) — 热

| # | 文件:行 | 形态 | 调用链 / 热路径判定 | 修法建议 |
|---|---|---|---|---|
| P1 | agent/tendency/TendencyData.cs:347, **380** | `AnalyzeUserTendencyAsync(userId).GetAwaiter().GetResult()` (文件 IO + 全量历史扫描) | 每轮 2 次: V2 L621-623 (coreTopic) + ContextAssembler.RecallFromUserTendencyAsync (UserTendency 源) — **热**; 且 L347 结果未复用于 L380 → 同方法内**双算同一画像** | 1) 复用 L347 的 profile 于打点; 2) GetContextBiasAsync 链整体 async (见 P2) |
| P2 | agent/IndustrialAgentV2.cs:622 | `GetContextBiasAsync(...).GetAwaiter().GetResult()` | OnProcessAsync 每用户消息一次 — **热**; 内部再叠 P1 的同步阻塞 (双阻塞) | 改 `await` (外层即 async 方法); 同时 P1 async 化后此处自然消失 |
| P3 | agent.vectormemory/BgeEmbeddingProvider.cs:42 | `_embedder.GetEmbeddings(text).GetAwaiter().GetResult()` **在 lock 内** | 调用链: EmbeddingRouter.Embed (RAGConfig.EmbeddingFunction) → RAGRecall IndexAsync/查询嵌入/长文档逐 chunk 嵌入; bge 真链时每轮 StoreToMemoryAsync+装配召回必触发 (CPU 数百 ms) — **热 (bge 配置态)**; 阻塞发生在 Task.WhenAll 并行召回段 → 占线程池线程 | IEmbeddingProvider 加 async 版或整个链路 async 化; 至少将 lock 移出推理段; 长文档 chunk 嵌入可批量化 |
| P4 | agent/contextassembler/ContextAssembler.cs:463-476 + 478-515 | 工作区召回: 全目录枚举 ≤300 文件 × **每文件整读** (≤200KB/文件 → 单轮最多 ~60MB 文本读入 + Split 每行 + 逐行关键词 Contains) | 文件/编码类意图每轮装配触发 (recall_workspace 打点曾监控) — **中热**; 无文件内容读取预算 | 每文件只读前缀 (≤32KB) 扫描命中后再全读; 或加整轮读取字节预算; 超 100KB 文件跳过大文件; 命中即停 (现状已 3 片段上限但每文件读全量) |

### 4.2 阻塞 — 非热 (低优先)

| # | 文件:行 | 形态 | 判定 | 修法 |
|---|---|---|---|---|
| P5 | agent/tokencompression/ITokenCompressor.cs:145-162, 298, 396-422 | `CompressAsync` 同步壳内多处 `.Result` (含循环内 CountTokensAsync().Result) | **主链只调 CountTokensAsync (ContextAssembler:1041, 真 async)**; Compress* 均 dormant — 非热但属 v0.11.0"sync-over-async 清剿"漏网 (若未来启用即死锁/线程饥饿面) | 与 §3 R-5 退役决策一并处理; 保留前先整体 async 化 |
| P6 | agent/registry/PanelData.cs:44, 84, 192 | `GetAllSessionsAsync().GetAwaiter().GetResult()` ×3 | 面板/报告本地命令 (低频 UI) | await 化 (宿主命令处理器本就 async) |
| P7 | agent/keywordannotation/KeywordIndex.cs:133 | `ExtractKeywordsAsync(text).Result` | KeywordTagger 全 dormant — 不可达 | 随 legacy 退役; 若保留改 async |
| P8 | agent/contextgradient/ContextGradientCompressor.cs:26, 39 | 同步壳 `Compress()` GetAwaiter | 调用点仅 host --compression-audit 工具与测试 | 工具场景可容忍; 标注即可 |
| P9 | agent.skills/TriggerMatcher.cs:43 | `Match` 同步壳 (注释自述 "sync 边界保留兼容") | SkillDispatcher.DispatchAsync 走 **MatchAsync** (:62, 真 async) — 同步壳主链不可达 | 建议随 legacy 删除同步壳只留 async, 消除误用面 (误用会带 bge 嵌入阻塞) |

### 4.3 循环/内存分配 — 热

| # | 文件:行 | 形态 | 判定 | 修法 |
|---|---|---|---|---|
| P10 | agent/contextassembler/ContextAssembler.cs:948-974 (ExtractAnchorWords) | 中文 2/3/4 字全滑窗 + 每窗 `Substring` (≈3×n 次短串分配) × 每个待压缩 snippet | 压缩热路径 (每装配, 每超限片段一次) — **中热**; 压缩是 13s 装配历史的主要嫌疑段之一 | 单遍扫描 + Span/字典 (每位置 4 字一次判断), 或仅对 >200tok 片段做锚词提取; 缓存高频片段锚词 |
| P11 | agent/IndustrialAgentV2.cs:1722-1757 (StoreToMemoryAsync) | 每轮双写两库 (VectorStore + RAGRecall) + 长文逐 chunk 嵌入 (RAGConfig L305-344) | 每用户消息 — **热** (见 §3 R-6: VectorStore 写侧无读者) | 移除/降频 VectorStore 写侧; chunk 嵌入预算化 (现状 ≤440ch/块, 每块一次 bge 推理) |
| P12 | agent.rag/RAGConfig.cs:262-281 (PersistDocument) | 每次 Index 都 `File.AppendAllText` 后 **无条件 `File.ReadAllLines(path)`** 判 512 行裁剪 → 每轮 1 次全量读+2 次文件开合, 且随库增长 O(n) | 每用户消息 — **热** (对话库逐轮涨) | 内存近似行数, 每 append N 次 (如 64) 才做一次裁剪读; 或超限后整库重写一次而非逐条 |
| P13 | agent/IndustrialAgentV2.cs:904-910 | prompt.UserMessage += 回注块拼接 | 每轮 1 次, 体量小 — 低 | 无 (仅记录, 不构成问题) |

### 4.4 string `+=` 循环 (逐条核查后仅 2 处真串拼, 均低热)

| # | 文件:行 | 形态 | 判定 |
|---|---|---|---|
| P14 | agent.host/CliRenderer.cs:108 | `line += $"...";` 循环内 (Step 渲染 detail) | CLI 展示, 行数小, 非热 — 可改 StringBuilder, 低优先 |
| P15 | agent.workspace/GitChangeType.cs:399 / agent.codegen/CodeGenerator.cs:276 / agent.registry/ForecastRecord.cs:85-86 | 循环内小串拼 (文件参数/基类列表/表头) | 数量级 ≤ 数十, 非热 — 低优先 (CodeGenerator 276 若长列表可先 List 后 Join) |
| 排除项 | ContextAssembler 613/1137/1216、ITokenCompressor 180/229、IPromptBuilder 212、RAGConfig 414/437、VectorDocument 316、ThinkMemory 195、StickyRouteMemory 117 等 | 数值累加 (tokens/dot/score) 非字符串 | 非字符串拼接, 不报 |

### 4.5 其他观察 (非阻塞类)

| # | 项 | 说明 |
|---|---|---|
| P16 | ContextAssembler.cs:1287 `_queryEmbedding` 实例字段 | 装配器为 DI 单例, 多会话并发装配会互相覆写该字段 → Session 源相关分可能串会话 (Session 源主链默认关闭, 风险潜伏); 建议改为按调用传递的局部量 |
| P17 | ContextAssembler.cs:40 `_resultCache` Dictionary 无锁写 (L92/271) | 并发装配 (subagent/多会话) 下 Dictionary 并发写非安全 — 建议 ConcurrentDictionary 或锁 (同文件 _lock 已有先例) |
| P18 | 影子计划每轮构造 (V2 L1466) | 每用户消息跑一次完整 TaskPlanBuilder+哑执行演练 — 结构体量小 (无 LLM), 记录观察, 若批均耗时异常再做预算 |
| P19 | V2 静态跨轮状态 `_consecutiveDrift/_clarifyArmed/_injectedGuardrails` | 进程级 static (跨 V2 实例) — 有意为之 (跨会话漂移连续计数语义); 仅提示: 多用户共享同一进程时会话间串扰 (现 CLI 单用户形态可接受), 归档备查 |

---

## 5. 局限与方法说明

- 全部结论来自静态阅读 + grep 消费者链, **未做运行时 profile** (只读任务); 热路径=沿 V2 OnProcessAsync/ContextAssembler 调用链可达性判定。
- "dormant/无消费方"结论口径: grep 全仓 src (排除 obj/bin/tests) 无调用点; 但 eval/ 脚本通过 CLI 协议驱动宿主, 个别能力可能经 CLI 表面 (如 /panel) 间接调用 — P6 已按此修正, 其余以 V2/装配/模型队列为主链面的判定不受影响。
- 562 单测口径参考 improvements.md (v0.15.2 546+13=562 未逐一核验), 报告正文未依赖该数字。

## 附录: 关键审计证据行索引

| 结论 | 证据 |
|---|---|
| R-1 pivot 词表×3 | IndustrialAgentV2.cs:575-576 / :637-638 / :976-977 ("不管之前"仅 :637) |
| R-2 legacy 记忆 4 实现 | ServiceCollectionExtensions.cs:71-72,197-198 + agent/memory/{MemoryStore,AgentMemoryStore,LongTermMemory,ShortTermMemory}.cs (V2 无引用) |
| R-3 hash/bge 双实现 | vectormemory/EmbeddingProvider.cs:37-66 vs llamalocal/EmbeddingRouter.cs:190-213; BgeEmbedder.cs:12 vs BgeEmbeddingProvider.cs:35-55; DI 两处: ServiceCollectionExtensions.cs:214-217 (RAG 工厂) + :221-228 (ITextEmbedder) |
| R-4 死召回器 | agent/memory/IMemoryRecall.cs:20-59; vectormemory/VectorDocument.cs:349-390; V2 字段 :79 无调用 (grep _memoryRecall. = 0) |
| R-5 压缩三实现 | tokencompression/ITokenCompressor.cs:107-486; contextgradient/ContextGradientCompressor.cs; memory/Summarizer.cs; 主链只用 CountTokensAsync (ContextAssembler:1041) |
| R-6 双写 | IndustrialAgentV2.cs:1738 + :1744; 召回仅 RAG (ContextAssembler:603) |
| §2.1 critic 未接线 | grep OutputCritic/SelfCritic/CriticPipeline → 仅 critique/* + agent.tests/* (0 主链调用) |
| §2.2 sticky 未接线 | grep StickyRouteMemory → 仅 StickyRouteMemoryTests.cs (ModelQueueRouter 无匹配) |
| §2.3 收敛判据未接线 | grep ComplexityGate./EvidenceScorer./EvaluateConvergence → 仅 ThinkChainTests.cs |
| P12 全量读 | RAGConfig.cs:277-281 (AppendAllText 后紧接 ReadAllLines) |
