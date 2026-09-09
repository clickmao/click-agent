# click-agent (v0.13.3)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![.NET](https://img.shields.io/badge/.NET-10.0-512BD4)
![Tests](https://img.shields.io/badge/tests-490%2F490-brightgreen)
![NativeAOT](https://img.shields.io/badge/NativeAOT-zero%20warnings-blueviolet)
![Eval](https://img.shields.io/badge/迭代评测-240批%2099%25%2B-success)

C# 工业级 Agent 框架 — 全场景覆盖、100% 托管代码。net10.0 / NativeAOT 零警告 / 490 测试全绿。
发布线: v0.13.3 — 思考链+渐进式探索 (A/B +39pt) / 兜底粘性路由 / 格式修复收敛环 / 压缩失败防护 D1-D4 /
微步骤隔离 / think-memory 跨进程联想 / 视觉理解 / bge 向量召回 0.95 / 22 模型目录 / 全链路打点。

[🇬🇧 English → README_EN.md](README_EN.md)

---

### ✅ v0.13.0/v0.13.1/v0.13.2/v0.13.3 能力 — 思考链 / 渐进式探索 / 兜底粘性 / 底座防护 (R205-R240 已落地)
- **渐进式探索** (用户钦定): ExplorationConfig (每源最大步 + 全局预算) + ExplorationPlanner (优先级队列, 上下文内 URL > 上下文外目录) + **HostExploreExecutor** (URL GET digest/页面链接发现≤5/目录文件路径穿越防护) + V2 RunThinkChainAsync (播种→4s/4步→首败即停→回注) — 探索 A/B 真机 **hit 0.45→0.64 (+18pt 零回归)**; LinkRegistry 关键文档激活链 (三信号: 锚定/稀缺出链/路径递进 ≥3 激活 + 父链保护)。
- **思考链 T3** (用户钦定): ComplexityGate + EvidenceScorer (单源封顶 medium) + **ThinkMemory bge 联想真机** (跨进程持久化 STJ source-gen, recall top_sim 0.977) + ThinkChainSession 收敛判据。
- **兜底粘性路由 v0.13.1**: FallbackConfig 性价比序逐个兜底+回复校验 + StickyRouteMemory 三门判定 (TTL 72h)。
- **格式修复 v0.13.2**: JsonRepairPlugin 栈感知修复 + FormatRepairLoop 状态机。
- **压缩失败防护 v0.13.3** (工业模式 M1-M6): D1 异常隔离 (per-snippet 回退原文) / D2 数字+URL 哨兵 (全档 URL 100% 保留实证) / D3 降级链 / D4 熔断器 / 不可变源。
- **微步骤隔离 B2**: gate=IsolatedMicro → 微问题隔离问询 → 回注 ≤200tok/条 (E2E: 2860ms)。
- **召回三口径**: bge 0.95 / 词袋长查询 0.70 (IDF 稀缺度加权) / 短查询对抗 0.45; 压缩 audit 104 篇多样态 keys 100%/指令 96%。
- 490 单测 · AOT 0 IL 警 · 评测通过率 97.9%+ (240 批)。

### ✅ v0.12.0 新增能力 — 视觉理解 / 渲染插件 / 收敛环 (已验收)
- **视觉理解链**: CLI `-img` → data URL base64 → glm-5.3-flash v4 端点 (1M ctx); text-only 模型自动重路由 + coding 端点改写 (真缺陷 63/64 修复); OpenAIMultimodalMessage 双形态 DTO (AOT-safe, 禁反射)。
- **真机验收**: T-V01~T-V04 视觉用例族 full-23 首验全绿 (含负样本诱饵: 模型识破"右下角苹果"预设陷阱); 四问真机复证 (主体/角落/位置/否定); 验收基线 docs/archive/reports-archived/v012-acceptance-baseline.md。
- **图像渲染插件体系** (用户钦定收敛环服务化): IImageRenderPlugin + SkiaSharpRenderPlugin (默认, 边缘选项 -p:DisableSkiaRenderer=true 停编) + SvgTextRenderPlugin (零依赖兜底) + Registry (无可用插件 → 跳过后续环节); LocalSvgRenderer DSL (rect/circle/line/text, XML 转义)。
- **收敛环 E2E**: LLM 生成 DSL → 渲染 → 5.3-flash 视觉校验 → 真机一轮 PASS (DSL 1039ch → SVG 843ch → 校验 6/6, 6.4s)。
- **能力矩阵**: models.yaml 25/25 模型 capabilities 回填; CogViewClient 保留 (生成路径按用户钦定弃用)。

### 📦 v0.11.0 R169-R204 能力

已归档 → [docs/changelogs/CHANGELOG-v0.11.0-R169-R185.md](docs/changelogs/CHANGELOG-v0.11.0-R169-R185.md) · [CHANGELOG-v0.11.0-R186-R204.md](docs/changelogs/CHANGELOG-v0.11.0-R186-R204.md)

### 📊 迭代评测统计 (打点对比数据驱动)

| 维度 | 基线 | 当前 (2026-09-09) | 改善 |
|---|---|---|---|
| 评测通过率 | 7354tok 基线 10 用例 | **240 批落盘, 近 30 批 99%+** (quick-11 口径) | 负面扩容后稳定 |
| 单元测试 | 325 | **490** | +165 |
| 真缺陷修复 | — | **69 项** (全部打点驱动, #21-#69) | 缺陷台账 |
| 召回率 (RAG) | 词袋 0.45 (缺陷 69 前) | **bge 0.95 / 词袋长查询 0.70** | 三口径基线 |
| 压缩关键信息保留 | SummarySentences 33-53% | **keys 100% / 指令 96%** (104 篇多样态 audit) | 健康线 ≥95% |
| 探索 A/B (可达 URL 24 案) | — | **hit 0.278→0.667 (+39pt) 零回归** | v0.13.3 探索链 |

### 批次趋势 (滚动窗口 — 最新 2 批)

**批240 (mass_460)** 11/11 quick-11 920/case / **批239 (mass_459)** 11/11 quick-11 974/case —
v0.13.3 宿主执行期: 思考链宿主链路 (think_chain 打点) + 探索 A/B 增益 +39pt + think-memory 跨进程持久化 +
LinkRegistry 激活链挂载; 批234 1402/case 单批离群定性 (C03 completion 波动非回归); 批236 XL 7/7 7008/case
(gate 三态稳定); 批238 10/11 C08 意图单批抖动 (3 连真机复现 general, 观察关闭)。

归档: [42-78](docs/changelogs/CHANGELOG-v0.11.0-R143-R152.md) · [79-108](docs/changelogs/CHANGELOG-v0.11.0-R153-R168.md) · [109-138](docs/changelogs/CHANGELOG-v0.11.0-R169-R185.md) · [139-167](docs/changelogs/CHANGELOG-v0.11.0-R186-R204.md) · [168-177](docs/changelogs/CHANGELOG-v0.11.0-R205-R218.md) · [178-187](docs/changelogs/CHANGELOG-v0.11.0-R219-R228.md)。每 30 批滚动。

专项验证: 多来源召回率 / 无关话题隔离 (score=2 独立 session) / session 长期记忆 (跨进程落盘) / JSON 格式跟随 / 双 LLM 校验 / XL 三态 gate — 全部 ✓。

完整报告: [主报告 §7](docs/reports/dynamic-telemetry-eval-rollback-strategy.md) · 阶段台账: [wave3-ledger (归档)](docs/archive/reports-archived/wave3-ledger.md)

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
- 用例族 T-V01~04 (含负样本诱饵) full 批 23/23; 验收基线 docs/archive/reports-archived/v012-acceptance-baseline.md

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

## 验证基线 (2026-09-09)

| 项 | 结果 |
|---|---|
| 单元测试 | **490/490** 通过 |
| NativeAOT (linux-x64) | **0 IL 警告** (多次复验) + full-graph AOT 冒烟通过 |
| 迭代评测 | **240 批落盘, 近 30 批 99%+** (quick-11 口径) |
| XL 大上下文族 | 7/7 通过 (gate 三态: IsolatedMicro×3 / HardDrop×3 / Normal×1) |
| 探索 A/B (可达 URL 24 案) | hit **0.278→0.667 (+39pt) 零回归** |
| think-memory 持久化 | 跨进程 recall hit top_sim 0.970 ✓ |
| 压缩 audit | 104 篇多样态: keys 100% / 因果 100% / 指令 96% / 压缩率 79-92% |
| 3 端点真机 | glm/deepseek 对话+余额 ✓; kimi 负样本诚实报错 ✓ |
| bge 真链 | JIT+AOT 双验收 ✓ |

## 文档

- [架构文档](docs/architecture.md) · [API](docs/api.md) · [CLI 指令](docs/CLI指令说明.md)
- [迭代方法论总纲](docs/reports/iteration-master-plan.md) — 宪法八条 / 5 KPI / 触发器 / 探索与负面数据源方法 / 真实性五道防线 (活文档)
- [主报告·动态打点与回滚](docs/reports/dynamic-telemetry-eval-rollback-strategy.md) — 状态层 (活文档, 每轮更新)
- [测试维度总账](docs/reports/test-dimensions-ledger.md) — 15 维度全景 + 负面族 + 防遗忘制度
- [千轮报告](docs/archive/reports/thousand-round-report.md) (§6 已冻结) · [改进记录](docs/improvements.md) · 历史计划: docs/archive/

## 下一步计划

> 详见 [主报告 §7](docs/reports/dynamic-telemetry-eval-rollback-strategy.md) 与 [方法论 §7 节奏表](docs/reports/iteration-master-plan.md)

1. **K1 效果闭环**: 画像驱动回复质量差分 (有/无画像 rel 对比) — snip 已可执行化, 待验证 LLM 行为收益
2. **批 56+ 千轮持续** (quick-10 扩容口径) + semantic_avg 档位观察 + 每 5 批审计
3. **K4 长周期观察**: skill 误吸压制稳定性 + negative-family 扩容 (八类清单向 25% 推进)
4. **Vulkan 真 GPU 实测** (需真 GPU 环境, 本机仅 llvmpipe)

## 许可证

MIT — 见 [LICENSE](LICENSE)。
