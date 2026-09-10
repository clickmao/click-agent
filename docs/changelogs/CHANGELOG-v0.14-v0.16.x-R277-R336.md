# CHANGELOG — v0.14.0 – v0.16.x 能力段 (R277–R336)

> 本文件为 README 能力段归档 (README 30 批滚动制度: 能力段只保留最新 2 个轮段)。
> 归档时点: v0.20.0 (R343) README 重建。原始段体内容完整保留如下。

### ✅ v0.14.0-v0.16.x 能力 — critic 自审 / 任务生命周期 / skills 引擎 / 性能 (已验收)

- **LLM 自审体系** (v0.14, 用户钦定 "LLM 数据来源=人类经验"): OutputCritic (静态反模式 8 规则带行号) / SelfCritic (quote 逐字子串防幻觉锚) / FixMemory (修法独立 schema, 来源秩 human>metric>llm) / CriticPipeline 三级过滤 (LLM 单源=观察态绝不进上下文)。
- **任务生命周期** (v0.15): TaskCharter 状态机 (planning→running→accepting→done|failed) + 三态输入路由 (补充→pendingContext / 无关→隔离 / 换任务→pivot) + GuardrailMemory (禁令提取→持久→跨域静默→habituation 去重)。
- **skills 引擎增强** (v0.16, 用户钦定): 格式统一 (6 包 frontmatter 规范) / **critic-rules 语言无关化** (R01-R08 语义级 + C#/Python/Go/Rust/Java 映射) / CLI 外挂 --skills-dir/--skills-blacklist/--skills-file (与内置不冲突) / 运行时动态 whitelist/blacklist / /skills 指令族 / KnowledgeHint 类型 (知识命中→注入 systemPrompt 生成时预防, C33-C35 3/3 精确含例外条款理解)。
- **性能/内存** (v0.15.3-v0.16.x): TendencyData 三算合一+async 化 (wall -3.5%) / bge 单实例共享 (RSS 130MB) / P4 召回流式化+4MB 预算 / P12 RAG 裁剪摊销 / P10 锚词 long-key 零分配 (语义等价 40 轮随机全等证明)。
- **版本A 存档**: git tag v0.15.2-A (仓库首 tag) + 全量验收 37/37 + 能力地图 function-map-R326。

### 相关实现文件 (归档索引)

- critic: `src/agent/critic/` (OutputCritic / SelfCritic / FixMemory / CriticPipeline)
- 任务生命周期: `src/agent/taskcharter/` (TaskCharter / GuardrailMemory)
- skills: `skills/` (6 包) + `src/agent/skills/` (SkillRegistry / SkillLoader / KnowledgeHint) + CLI 参数 `--skills-dir/--skills-blacklist/--skills-file`
- 性能: `src/agent/tendency/TendencyData.cs` (async 化) / `src/agent.vectormemory/SharedEmbedderRegistry.cs` (bge 单实例) / `src/agent/contextassembler/ContextAssembler.cs` (P10 锚词)
- 计划文档: `docs/plans/v0.14.0-master-plan.md` / `v0.14.0-t2-llm-selfcritic-plan.md` / `v0.15.0-task-lifecycle-plan.md` / `v0.15.3-perf-memory-plan.md`
- 能力地图: `docs/reports/function-map-R326.md`
