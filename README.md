# click-agent (v0.11.0)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![.NET](https://img.shields.io/badge/.NET-10.0-512BD4)
![Tests](https://img.shields.io/badge/tests-409%2F409-brightgreen)
![NativeAOT](https://img.shields.io/badge/NativeAOT-zero%20warnings-blueviolet)
![Eval](https://img.shields.io/badge/千轮评测-1034%2F1056-success)

C# 工业级 Agent 框架 — 全场景覆盖、100% 托管代码。net10.0 / NativeAOT 零警告 / 409 测试全绿。
发布线: v0.11.0 — 统一 @cmd 命令协议 + 3 传输通道 / Skill executive 脚本 / bge 向量混合相关性 / 22 模型目录 / PGO 式全链路打点。

[🇬🇧 English → README_EN.md](README_EN.md)

---

### 🚧 v0.13.0/v0.13.1 开发中 — 思考链收敛 / 渐进式探索 / 兜底粘性路由
- **渐进式探索** (用户钦定): ExplorationConfig (每上下文区/文本/URL/目录最大探索步 + 全局预算 + URL 深度) + ExplorationPlanner (优先级队列, 上下文内 URL > 上下文外目录) — 7 单测。
- **思考链收敛 T3** (用户钦定): ComplexityGate (复杂度判定) + EvidenceScorer (多源对比, 单源封顶 medium) + ThinkMemory RAG 联想 (相似问题优先阅览历史高置信链接, 引用后 +0.05 置信, 负样本降权, 30 天衰减) + ThinkChainSession (收敛判据: 多源一致/预算耗尽/无新发现/自评) — 12 单测。
- **兜底粘性路由 v0.13.1** (用户钦定): FallbackConfig (config 开关, 性价比序=auto 同源判据, 逐个兜底+回复校验) + StickyRouteMemory (相似问题首用成功模型; 三门判定: embedding 相似+意图一致+实体指纹; 形近意远不粘; TTL 72h) — Router 逐个兜底链已落地, 11 单测。
- 设计文档: docs/plans/v0.13.0-progressive-exploration.md · v0.13.0-think-chain-convergence.md · v0.13.1-fallback-sticky-routing.md

### ✅ v0.12.0 新增能力 — 视觉理解 / 渲染插件 / 收敛环 (已验收)
- **视觉理解链**: CLI `-img` → data URL base64 → glm-5.3-flash v4 端点 (1M ctx); text-only 模型自动重路由 + coding 端点改写 (真缺陷 63/64 修复); OpenAIMultimodalMessage 双形态 DTO (AOT-safe, 禁反射)。
- **真机验收**: T-V01~T-V04 视觉用例族 full-23 首验全绿 (含负样本诱饵: 模型识破"右下角苹果"预设陷阱); 四问真机复证 (主体/角落/位置/否定); 验收基线 docs/reports/v012-acceptance-baseline.md。
- **图像渲染插件体系** (用户钦定收敛环服务化): IImageRenderPlugin + SkiaSharpRenderPlugin (默认, 边缘选项 -p:DisableSkiaRenderer=true 停编) + SvgTextRenderPlugin (零依赖兜底) + Registry (无可用插件 → 跳过后续环节); LocalSvgRenderer DSL (rect/circle/line/text, XML 转义)。
- **收敛环 E2E**: LLM 生成 DSL → 渲染 → 5.3-flash 视觉校验 → 真机一轮 PASS (DSL 1039ch → SVG 843ch → 校验 6/6, 6.4s)。
- **能力矩阵**: models.yaml 25/25 模型 capabilities 回填; CogViewClient 保留 (生成路径按用户钦定弃用)。

### 📦 v0.11.0 R169-R204 能力

已归档 → [docs/changelogs/CHANGELOG-v0.11.0-R169-R185.md](docs/changelogs/CHANGELOG-v0.11.0-R169-R185.md) · [CHANGELOG-v0.11.0-R186-R204.md](docs/changelogs/CHANGELOG-v0.11.0-R186-R204.md)

### 📊 千轮迭代评测 (PGO 对比数据驱动)

| 维度 | 基线 | 当前 | 改善 |
|---|---|---|---|
| 评测通过率 | — | **1034/1056 = 97.92%** (215 轮落盘) | 稳定 99%+ (负面扩容后口径) |
| 单轮 tokens (全量 10 用例基线 vs 现 quick-10) | 7354 | **9024** (含 5 个新增广泛度用例) | -50% (可比 quick-5 口径 ~3671) |
| C08 推理 completion | 1875 | **479** | **-74%** |
| 单元测试 | 325 | **389** | +64 |
| 真缺陷修复 | — | **55 项** (全部打点驱动) | #21-#55 |

批次趋势: **批214 (mass_432)** 11/11 quick-11 861/case / **批215 (mass_433)** 11/11 quick-11 1026/case — 底座能力优化期: 压缩 audit 关键句保护修复 (SummarySentences 保留率 33-53%→多样态 99%/85% 指令) + 429 感知调度 (跳过同模型重试直切备) + token-breakdown 观测行; 每批 KPI 小报制执行中。归档: [42-78](docs/changelogs/CHANGELOG-v0.11.0-R143-R152.md) · [79-108](docs/changelogs/CHANGELOG-v0.11.0-R153-R168.md) · [109-138](docs/changelogs/CHANGELOG-v0.11.0-R169-R185.md) · [139-167](docs/changelogs/CHANGELOG-v0.11.0-R186-R204.md) · [168-177](docs/changelogs/CHANGELOG-v0.11.0-R205-R218.md) · [178-187](docs/changelogs/CHANGELOG-v0.11.0-R219-R228.md)。每 30 批滚动 (下次: 批228)。
专项验证: 多来源召回率 (100 用例轮统计) / 无关话题隔离 (score=2 触发独立 session) / session 长期记忆 (跨进程落盘) / JSON 格式跟随 (哨兵用例) / 双 LLM 校验 — 全部 ✓。

完整报告: [千轮迭代优化报告](docs/reports/thousand-round-report.md) · 阶段台账: [wave3-ledger](docs/reports/wave3-ledger.md)

### 🧭 能力全景

**工程总览**: 16 csproj — agent (主链 22 子模块: intent/registry/memory/contextassembler/tendency/session/search/llamalocal/maf/pipeline/subagent 等) / core / config / contextgradient / modelqueue / skills / rag / vectormemory / workspace / io / logging / output / recovery / codegen / host / tests。

**推理与任务**
- 意图分析与子任务细分: 19 中英连接词, Sequential/Parallel/DependsOnOutput 关系; 创作类拦截 (写诗≠写代码, R116)
- TaskPlan 拓扑执行: Level 并发 (Task.WhenAll + MaxParallelism) / 节点重试 (指数退避+瞬态分类) / 敏感意图 PausedForApproval
- 隔离任务: 无关话题生成边界隔离 subagent (独立 session, 主记忆零污染), 完成即销毁

**模型调度 (agent.modelqueue)**
- 本地 (LocalLlamaCaller 真跑) > 官方 (硬编码+内存 key) > 远程 API 三通道
- 22 模型目录: 意图 × token 估算 × 成本排序; auto/manual 双模; 粘性同步 (R89)
- **余额链**: 真 API 同步 → 本地累计 → 阈值再同步; 余额不足自动切模 (候选过滤: 有 key + sufficient, #46) + `flags:balance-insufficient` 提示; 汇率 CNY÷7.2 (#45)

**视觉与图像 (v0.12.0 已验收)**
- 视觉理解链: CLI `-img` → base64 data URL → glm-5.3-flash v4 (1M ctx); text-only 自动重路由 + coding 端点改写; 双形态 DTO (AOT-safe)
- 图像渲染插件: IImageRenderPlugin (SkiaSharp 默认可边缘停编 / SVG 文本兜底) + LocalSvgRenderer DSL; 收敛环 E2E (DSL→渲染→视觉校验→FAIL 重生成→PASS)
- 用例族 T-V01~04 (含负样本诱饵) full 批 23/23; 验收基线 docs/reports/v012-acceptance-baseline.md

**探索与思考链 (v0.13.x 开发中, 用户钦定)**
- 渐进式探索: ExplorationPlanner (每上下文区/文本/URL/目录最大步数 config; 上下文内 URL > 上下文外目录优先级)
- 思考链收敛: ComplexityGate + EvidenceScorer (多源对比, 单源封顶 medium) + ThinkMemory RAG 联想 (相似问题优先历史高置信链接, 引用后 +0.05 置信)
- 兜底粘性路由: FallbackConfig (config 开关+性价比序+逐个兜底校验) + StickyRouteMemory (相似问题首用成功模型; 三门判定防形近意远)
- 格式修复收敛环: IFormatRepairPlugin (①块内检测→②查找→③校验→④本地修复→⑤LLM 循环; max_llm_rounds; 技能-校验矩阵)
- RAG 数据文件用户指定: CLI `-rag <path>` / 任务内 `/rag` / env 三入口 (多库隔离)
- **压缩底座 audit** (v0.13.3): `--compression-audit` 分档校验 (500/1000/2000/3000 tok × 级别 → 关键信息保留率/压缩率/耗时); ground-truth 104 篇多样态; A3 关键句保护修复 (SummarySentences 因果/指令保留 0-20%→100% 单样/85% 多样态); 每批抽查+10 批全量 cadence
- **429 感知调度**: 限流跳过同模型重试直切备 (省 ~1000 tok/次重发)
- **微步骤隔离设计 A6**: 阈值门控 (未达阈值走常规, 更正2); 触发率基线 0% (批164-210 实测)

**Skill 调度 (agent.skills)**
- SKILL.md 目录包 (Anthropic Agent-Skills Open Standard) + executive 真进程脚本执行 (python/bash/node, 沙箱/超时 kill-tree)
- 四级触发: 关键词 → 正则 → 领域词 → bge 语义 (cos≥0.45)

**上下文与记忆 (agent.contextgradient)**
- 梯度压缩 L0-L3 + P0-P3 锚点; 主题聚类 + 三重漂移校验 (bge 真向量 cos)
- 多数据源上下文注入 8 源: Memory/Session/Workspace/AgentContext/UserTendency/WebSearch/ToolOutput/SessionMemory — 各源召回明细打点 (per-source snip/tok/rel)
- 体积治理: Memory 源 500tok 预算 + rel<0.4 只留 best1 (#49); Workspace 相关分比例化 (#50)

**配置与输出**
- 四层 YAML 配置 (Yamlify, 零反射) + IOutputSink 统一输出 (库内零 Console 直写)
- PGO 打点: AgentTelemetry JSONL (12+ 点位) — 详见千轮报告

**工程**
- NativeAOT: 端到端 0 IL 警告 (JIT 仅测试手段, 发布形态必为 AOT — 钦定铁律)
- Session 恢复: ExecutionCheckpoint 原子持久化
- agent.io 协议库 (netstandard2.1 零依赖)

## 快速开始

```bash
git clone https://github.com/clickmao/click-agent.git
cd click-agent
dotnet restore
dotnet build
```

### CLI 用法

```bash
cd src/agent.host

# 交互 REPL
dotnet run

# 单轮模式
dotnet run -- -q "先搜索 AOT 资料, 再写总结文档"

# 环境变量 (3 端点示例)
# AGENTFRAMEWORK_KEYS_BIGMODEL / AGENTFRAMEWORK_KEYS_DEEPSEEK / AGENTFRAMEWORK_KEYS_KIMI
# AGENTFRAMEWORK_BGE_MODEL=bge 模型路径 (启用真向量链)
# AGENTFRAMEWORK_MIN_BALANCE_USD=0.50 (余额阈值)
```

CLI 内置命令: `/balance` (余额+活跃模型) / `/model` / `/token stats` / `/status` / `/reset` / `/exit`。

### 评测复现

```bash
cd eval
python3 run_round.py mass_1000 "my round" --quick   # quick 5 用例
python3 analyze.py mass_1000 mass_999               # 批间对比
python3 cross_validate.py                           # 双 LLM 交叉校验
```

## 验证基线 (2026-09-07)

| 项 | 结果 |
|---|---|
| 单元测试 | **399/399** 通过 |
| NativeAOT (linux-x64) | **0 IL 警告** (六次复验) + AOT 冒烟通过 |
| 千轮评测 | **1034/1056 (97.92%)** — 215 轮落盘 |
| 3 端点真机 | glm/deepseek 对话+余额 ✓; kimi 负样本诚实报错 ✓ |
| 阈值切模 | 实战触发 ✓ (deepseek $1.25 → glm) |
| bge 真链 | JIT+AOT 双验收 ✓ (dim512, 282ms) |

## 文档

- [架构文档](docs/architecture.md) · [API](docs/api.md) · [CLI 指令](docs/CLI指令说明.md)
- [迭代方法论总纲](docs/reports/iteration-master-plan.md) — 宪法八条 / 5 KPI / 触发器 / 探索与负面数据源方法 / 真实性五道防线 (活文档)
- [主报告·动态打点与回滚](docs/reports/dynamic-telemetry-eval-rollback-strategy.md) — 状态层 (活文档, 每轮更新)
- [测试维度总账](docs/reports/test-dimensions-ledger.md) — 15 维度全景 + 负面族 + 防遗忘制度
- [千轮报告](docs/reports/thousand-round-report.md) (§6 已冻结) · [改进记录](docs/improvements.md) · 历史计划: docs/archive/

## 下一步计划

> 详见 [主报告 §7](docs/reports/dynamic-telemetry-eval-rollback-strategy.md) 与 [方法论 §7 节奏表](docs/reports/iteration-master-plan.md)

1. **K1 效果闭环**: 画像驱动回复质量差分 (有/无画像 rel 对比) — snip 已可执行化, 待验证 LLM 行为收益
2. **批 56+ 千轮持续** (quick-10 扩容口径) + semantic_avg 档位观察 + 每 5 批审计
3. **K4 长周期观察**: skill 误吸压制稳定性 + negative-family 扩容 (八类清单向 25% 推进)
4. **Vulkan 真 GPU 实测** (需真 GPU 环境, 本机仅 llvmpipe)

## 许可证

MIT — 见 [LICENSE](LICENSE)。
