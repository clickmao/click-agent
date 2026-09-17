# CHANGELOG v0.12.x — 视觉理解 / 渲染插件 / 收敛环 (R169-R228 期能力, 2026-09-09 归档自 README)

> 归档来源: README v0.12 能力段 (2026-09-09 撤出时完整收录, archive-first)。轮次细节见主报告与 wave3-ledger。

## ✅ v0.12.0 新增能力 — 视觉理解 / 渲染插件 / 收敛环 (已验收)

- **视觉理解链**: CLI `-img` → data URL base64 → glm-5.3-flash v4 端点 (1M ctx); text-only 模型自动重路由 + coding 端点改写 (真缺陷 63/64 修复); OpenAIMultimodalMessage 双形态 DTO (AOT-safe, 禁反射)。
- **真机验收**: T-V01~T-V04 视觉用例族 full-23 首验全绿 (含负样本诱饵: 模型识破"右下角苹果"预设陷阱); 四问真机复证 (主体/角落/位置/否定); 验收基线 docs/archive/reports-archived/v012-acceptance-baseline.md。
- **图像渲染插件体系** (用户钦定收敛环服务化): IImageRenderPlugin + SkiaSharpRenderPlugin (默认, 边缘选项 -p:DisableSkiaRenderer=true 停编) + SvgTextRenderPlugin (零依赖兜底) + Registry (无可用插件 → 跳过后续环节); LocalSvgRenderer DSL (rect/circle/line/text, XML 转义)。
- **收敛环 E2E**: LLM 生成 DSL → 渲染 → 5.3-flash 视觉校验 → 真机一轮 PASS (DSL 1039ch → SVG 843ch → 校验 6/6, 6.4s)。
- **能力矩阵**: models.yaml 25/25 模型 capabilities 回填; CogViewClient 保留 (生成路径按用户钦定弃用)。

## ✅ v0.13.0/v0.13.1/v0.13.2/v0.13.3 能力 — 思考链 / 渐进式探索 / 兜底粘性 / 底座防护 (R205-R240)

> 本段与 CHANGELOG-v0.13.x-R229-R248 / CHANGELOG-v0.13.3-R249-R268 重叠 — 完整轮次记录以 changelog 为准, 此处保留能力级摘要 (README v0.13 段体撤出收录)。

- **渐进式探索** (用户钦定): ExplorationConfig (每源最大步 + 全局预算) + ExplorationPlanner (优先级队列, 上下文内 URL > 上下文外目录) + HostExploreExecutor (URL GET digest/页面链接发现≤5/目录文件路径穿越防护) + V2 RunThinkChainAsync (播种→4s/4步→首败即停→回注) — 探索 A/B 真机 hit 0.45→0.64 (+18pt 零回归); LinkRegistry 关键文档激活链 (三信号: 锚定/稀缺出链/路径递进 ≥3 激活 + 父链保护)。
- **思考链 T3**: ComplexityGate + EvidenceScorer (单源封顶 medium) + ThinkMemory bge 联想真机 (跨进程持久化 STJ source-gen, recall top_sim 0.977) + ThinkChainSession 收敛判据。
- **兜底粘性路由 v0.13.1**: FallbackConfig 性价比序逐个兜底 + 回复校验 + StickyRouteMemory 三门判定 (TTL 72h)。
- **格式修复 v0.13.2**: JsonRepairPlugin 栈感知修复 + FormatRepairLoop 状态机。
- **压缩失败防护 v0.13.3** (工业模式 M1-M6): D1 异常隔离 / D2 数字+URL 哨兵 / D3 降级链 / D4 熔断器 / 不可变源。
- **微步骤隔离 B2**: gate=IsolatedMicro → 微问题隔离问询 → 回注 ≤200tok/条。
- **召回三口径**: bge 0.95 / 词袋长查询 0.70 / 短查询对抗 0.45; 压缩 audit 104 篇 keys 100%/指令 96%。

## 批次趋势 (v0.11-v0.13 期尾, 2026-09-09)

批249-R268 段内记录 → CHANGELOG-v0.13.3-R249-R268.md; 滚动点批258 (mass_478 11/11 quick-11 1003/case) 已执行。
