# v0.11.0 R103-R127 新增能力 (完整归档)

> 归档说明: 本文件为 README 能力段的完整历史归档 (README 30 批一滚动, 只保留最新条目)。
> 生成: R152 (批78, 2026-09-07)。数据源: eval/reports/round-log.md + data/logs/eval/rounds/。
> 制度: 用户钦定 2026-09-07 — "每隔30个批次 更新一次readme", 旧能力段按轮段归档至此。

## v0.11.0 R103-R127 新增能力
- **PGO 式全链路打点体系**: 12+ 类点位 (intent/assembly 8 源召回/llm_call/skill/loop_turn/isolated/tendency/balance_sync/compression/bge_embed/sensitive), JSONL 落盘 + Configure 前点位 pending ring (R121) + DroppedTotal 丢失可见化 — 每一轮优化由打点对比数据驱动
- **3 真实 key 余额链 E2E**: deepseek 真余额查询 (9.02→7.61 CNY) / 阈值切模实战实证 (MIN_BALANCE=100 → deepseek $1.25 不足 → 切 glm) / glm 无 scheme 诚实报错 / kimi 负样本诚实报错
- **P3 bge 真向量链**: AGENTFRAMEWORK_BGE_MODEL → EmbeddingRouter bge 优先/词袋兜底, dim512, JIT+AOT 双验收; RAG/ContextGradient/语义漂移 cos 校验全真链
- **LLamaSharp Vulkan 单入口** (fork ed89226+252b68f): dlopen libllama.so + $ORIGIN RUNPATH 自动解析全部依赖, Silk.NET.Vulkan 零 native
- **多轮会话评测 harness**: run_case_repl (REPL 型多轮用例) + 隔离/pivot/回锚全实证 (C14/C15/C16 四轮长会话) + anomaly 防护 (评分器可靠性 R120)
- **双 LLM 交叉校验**: cross_validate (glm+deepseek agree=true)
