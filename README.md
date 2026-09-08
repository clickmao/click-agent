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

### 🚧 v0.12.0 开发中 — 视觉理解/图像生成/无头浏览器插件

- **glm-5.3-flash 图像理解** (真机验证 2026-09-08): v4 标准端点 + image_url/base64, 多图, 1M 上下文 — 4.6s 准确描述 CogView 生成图
- **capabilities 模态能力矩阵**: models.yaml 25/25 模型回填 (text/image/video/audio/pdf/xlsx/image_output) — 文本模型收图明确报错
- **CogViewClient 生图客户端**: cogview-3-flash 真机 8.1s 1024x1024 (免费档) + image_gen 打点 + 空图校验
- **VisionChat DTO**: content 双形态 (string|parts[]) 手写 AOT 安全 converter, 向后兼容纯文本链路, 5 对抗单测
- **开发计划**: docs/plans/v0.12.0-vision-plan.md (R2 版 — doubao thread 核实 + 真机证据, zcode 收敛环: 理解→生成→校验→FAIL 重生成)

### 🆕 v0.11.0 R169-R204 新增能力

- **真缺陷 59 修复 (R172)**: harness per-case 超时容错 — 单用例 180s 挂起不再崩整批 (批113 C13 实证); LLM 瞬态重试 1/1 (5 用例实测全覆盖)
- **真缺陷 60 修复 (R180)**: must_contain 升级硬 FAIL 过程中误用作用域外 req() → NameError 崩批; 改 x[pass]=False
- **真缺陷 61 修复 (R182)**: 记忆回指词 (还记得/上一条/上次…) 缺失导致 C07 repl 轮2 误隔离 (批130 实证) — +8 词一票否决
- **C07 记忆链根修 (R182)**: 记忆源破案 = 跨进程 forecast.json 单槽被中间用例竞态覆盖 (批340 丢失实证链); 用例改 repl 双轮真 session 链
- **归一化泛化 (R183)**: 去空白/标点/全半角归一化层 + 语言无关结构信号 (纯疑问短语一票否决/短问句减分) — 空格插入/其他语言免疫
- **v0.12.0 开工 (R199-R200)**: capabilities 模态矩阵 25/25 模型回填; CogViewClient 生图客户端 (真机 8.1s); OpenAIMultimodalMessage 双形态 DTO (AOT 安全); 5.3-flash 图像理解真机验证 (4.6s)

  <details><summary>批 109-167 全部明细</summary>

  [docs/changelogs/CHANGELOG-v0.11.0-R169-R185.md](docs/changelogs/CHANGELOG-v0.11.0-R169-R185.md) ·
  [docs/changelogs/CHANGELOG-v0.11.0-R186-R204.md](docs/changelogs/CHANGELOG-v0.11.0-R186-R204.md)

  </details>

### 📊 千轮迭代评测 (PGO 对比数据驱动)

| 维度 | 基线 | 当前 | 改善 |
|---|---|---|---|
| 评测通过率 | — | **1034/1056 = 97.92%** (215 轮落盘) | 稳定 99%+ (负面扩容后口径) |
| 单轮 tokens (全量 10 用例基线 vs 现 quick-10) | 7354 | **9024** (含 5 个新增广泛度用例) | -50% (可比 quick-5 口径 ~3671) |
| C08 推理 completion | 1875 | **479** | **-74%** |
| 单元测试 | 325 | **389** | +64 |
| 真缺陷修复 | — | **55 项** (全部打点驱动) | #21-#55 |

批次趋势: **批176 (mass_392)** 11/11 quick-11 8805tok (800/case) / **批177 (mass_393)** 11/11 quick-11 10386tok (944/case) — C07 repl 化后带宽 ≤1250, 近 25 批 25 绿 (含 full-20 vision 首验)。批42-78: [docs/changelogs/CHANGELOG-v0.11.0-R143-R152.md](docs/changelogs/CHANGELOG-v0.11.0-R143-R152.md); 批79-108: [docs/changelogs/CHANGELOG-v0.11.0-R153-R168.md](docs/changelogs/CHANGELOG-v0.11.0-R153-R168.md); 批109-138: [docs/changelogs/CHANGELOG-v0.11.0-R169-R185.md](docs/changelogs/CHANGELOG-v0.11.0-R169-R185.md); 批139-167: [docs/changelogs/CHANGELOG-v0.11.0-R186-R204.md](docs/changelogs/CHANGELOG-v0.11.0-R186-R204.md); 批168-177: [docs/changelogs/CHANGELOG-v0.11.0-R205-R218.md](docs/changelogs/CHANGELOG-v0.11.0-R205-R218.md)。README 批次明细每 30 批滚动更新一次 (下次: 批198)。
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
