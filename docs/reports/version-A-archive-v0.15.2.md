# click-agent v0.15.2-A — 版本存档 (R326)

> 存档时间: 2026-09-10 · commit: cd149ce · 依据: 用户钦定 (R326): "大样本稳定可验收后总结全部能力,
> 查找功能重复(无重复不强归拢), 整体内存/性能优化后存档一版本A"。
> 功能地图/重复排查/性能候选全量: docs/reports/function-map-R326.md (314 行, 子代理只读审计 + grep 证据)。

## 存档基线

| 项 | 值 |
|---|---|
| 单测 | 546/546 绿 (v0.11.0 325 → +221) |
| 批测 | quick-13 13/13 (批273) · 全量 33/34 (批272, 唯一失败=断言误报已修) · 路由三案 3/3 (批274) |
| AOT | linux-x64 self-contained 12.6MB, publish 0 IL 警告 |
| 版本元数据 | csproj 全升 0.15.2 (此前停滞 0.11.0, README 唯一版本源) |
| git | 首个 tag: v0.15.2-A |

## v0.13.3 → v0.15.2 能力增量 (★ = 本文档版本新增)

### v0.14.0 输出侧经验闭环 (R318-R321)
- OutputCritic (R318): 8 条 C# 反模式静态规则 (R01-R08, 证据带行号, 只提示不改写)
- SelfCritic (R319, 用户钦定方向): LLM 自审契约 (quote 逐字锚防幻觉 + 机制解释强制)
- FixMemory (R319): 修法记忆 (反模式→修法), 来源秩 human>metric>llm; ★生成前注入链已接线 (T2d)
- CriticPipeline (T2c): 三级过滤 (静态=确认态 / 双源=去重 / LLM 单源=观察态不入上下文)
- ★审计发现: OutputCritic/SelfCritic/CriticPipeline 主链触发侧未接线 (仅 FixMemory 注入链活) — 如实登记
- GuardrailMemory (v0.15.2): 警告/铁律记忆 (逻辑三元组 + 域键 + general 全域触发语义)

### v0.15.x 任务生命周期 (R322-R326)
- TaskCharter (R322): 章程 schema + 状态机, 持久化 data/task-charters/active.json
- 新输入三态路由 (R322): charter 活跃时 supplement→pending / isolate→隔离子 / pivot→归档 failed
- Guardrail 注入链 (R325): write (警告语义 1.38) → persist → recall (域+pattern) → inject (前置) → dedup (habituation)
- C22-C31 精准样本族 (R149 真断言: task_route/guardrail_injected/guardrail_writes)

### KPI-2 常设监控 (R324)
- eval/token_report.py (每 10 批 audit 节奏) + docs/reports/kpi2-token-report-R324.md
- quick-11 同口径长期 1126 tok/case (环比 +4%) — 口径变更登记制度

## 本次存档优化 (cd149ce)

| # | 优化 | 类型 | 验证 |
|---|---|---|---|
| R-1 | pivot 词表 3 份拷贝收敛单源 (修复"不管之前"语义分裂) | 正确性/去重复 | 批274 C15/C24 3/3 |
| P16 | _queryEmbedding 实例字段→局部变量 (DI 单例并发串话) | 并发安全 | build+546 测 |
| P17 | _resultCache → ConcurrentDictionary (无锁并发写) | 并发安全 | build+546 测 |

## 功能重复排查结论 (铁律: 无重复不强归拢)

- **确认真重复 (不强归拢, 只收敛词表/退役死码)**: R-1 pivot 词表×3 (已收敛) · R-2 legacy 记忆 4 实现
  · R-3 hash 双实现+bge 双加载 (内存真重复, 待用户裁定统一) · R-4 死召回器 · R-5 压缩三实现 (主链已定一尊)
  · R-6 会话双写 (VectorStore 写侧无读者, 待评估)
- **明确无重复不强归拢**: 记忆分层 / 召回三口径 / 隔离五轴 (判定器已单点化) / 兜底域异 / host 预渲染×4 (同形不同义)
- **dormant 待退役/接线**: agent/memory 传统栈 · IVectorMemoryRecall · StickyRouteMemory (未接 Router)
  · ComplexityGate/EvidenceScorer 收敛判据 · SubAgent 池 · keywordannotation

## 待办 (版本A 后)

- P1/P2 async 化 (TendencyData + V2 coreTopic 双阻塞热路径)
- P3 bge 嵌入 lock 移出推理段 + 长文 chunk 批量化; P10 锚词提取 Span 化; P12 RAG 裁剪读 O(n)→摊还
- v0.14 critic 触发侧接线 (主链消费 OutputCritic/SelfCritic 已设计未接)
- v0.15 PendingInputs 读侧注入下游循环
- R-3 bge 双加载统一 (第二份模型驻留消除, 需用户裁定)
- R-6 VectorStore 写侧移除评估 (每轮省一次写+一次向量)
