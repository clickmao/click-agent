# click-agent (v0.11.0)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![.NET](https://img.shields.io/badge/.NET-10.0-512BD4)
![Tests](https://img.shields.io/badge/tests-386%2F386-brightgreen)
![NativeAOT](https://img.shields.io/badge/NativeAOT-zero%20warnings-blueviolet)
![Eval](https://img.shields.io/badge/千轮评测-872%2F873-success)

C# 工业级 Agent 框架 — 全场景覆盖、100% 托管代码。net10.0 / NativeAOT 零警告 / 386 测试全绿。
发布线: v0.11.0 — 统一 @cmd 命令协议 + 3 传输通道 / Skill executive 脚本 / bge 向量混合相关性 / 22 模型目录 / PGO 式全链路打点。

[🇬🇧 English → README_EN.md](README_EN.md)

---

### 🆕 v0.11.0 R103-R127 新增能力
- **PGO 式全链路打点体系**: 12+ 类点位 (intent/assembly 8 源召回/llm_call/skill/loop_turn/isolated/tendency/balance_sync/compression/bge_embed/sensitive), JSONL 落盘 + Configure 前点位 pending ring (R121) + DroppedTotal 丢失可见化 — 每一轮优化由打点对比数据驱动
- **3 真实 key 余额链 E2E**: deepseek 真余额查询 (9.02→7.61 CNY) / 阈值切模实战实证 (MIN_BALANCE=100 → deepseek $1.25 不足 → 切 glm) / glm 无 scheme 诚实报错 / kimi 负样本诚实报错
- **P3 bge 真向量链**: AGENTFRAMEWORK_BGE_MODEL → EmbeddingRouter bge 优先/词袋兜底, dim512, JIT+AOT 双验收; RAG/ContextGradient/语义漂移 cos 校验全真链
- **LLamaSharp Vulkan 单入口** (fork ed89226+252b68f): dlopen libllama.so + $ORIGIN RUNPATH 自动解析全部依赖, Silk.NET.Vulkan 零 native
- **多轮会话评测 harness**: run_case_repl (REPL 型多轮用例) + 隔离/pivot/回锚全实证 (C14/C15/C16 四轮长会话) + anomaly 防护 (评分器可靠性 R120)
- **双 LLM 交叉校验**: cross_validate (glm+deepseek agree=true)

### 📊 千轮迭代评测 (PGO 对比数据驱动)

| 维度 | 基线 | 当前 | 改善 |
|---|---|---|---|
| 评测通过率 | — | **872/873 = 99.89%** (184 轮落盘) | 稳定 99%+ |
| 单轮 tokens (quick) | 7354 | **~3671** | **-50%** |
| C08 推理 completion | 1875 | **479** | **-74%** |
| 单元测试 | 325 | **386** | +61 |
| 真缺陷修复 | — | **52 项** (全部打点驱动) | #21-#52 |

批次趋势 (批26-39): 3623/4024/4248/4106/3636/3656/3855/3597/4145/4035/3778/3765/3709/3671 — 14 批 × 25 用例全绿, 无上行漂移。
专项验证: 多来源召回率 (100 用例轮统计) / 无关话题隔离 (score=2 触发独立 session) / session 长期记忆 (跨进程落盘) / JSON 格式跟随 (哨兵用例) / 双 LLM 校验 — 全部 ✓。

完整报告: [千轮迭代优化报告](docs/reports/thousand-round-report.md) · 阶段台账: [wave3-ledger](docs/reports/wave3-ledger.md)

### 🧭 能力全景

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
| 单元测试 | **386/386** 通过 |
| NativeAOT (linux-x64) | **0 IL 警告** (六次复验) + AOT 冒烟通过 |
| 千轮评测 | **872/873 (99.89%)** — 184 轮落盘 |
| 3 端点真机 | glm/deepseek 对话+余额 ✓; kimi 负样本诚实报错 ✓ |
| 阈值切模 | 实战触发 ✓ (deepseek $1.25 → glm) |
| bge 真链 | JIT+AOT 双验收 ✓ (dim512, 282ms) |

## 文档

- [架构文档](docs/architecture.md) · [API](docs/api.md) · [CLI 指令](docs/CLI指令说明.md)
- [千轮迭代优化报告](docs/reports/thousand-round-report.md) — PGO 打点方法论/缺陷台账/PGO v2 动态打点策略/未完成事项
- [改进记录](docs/improvements.md) · [任务循环](docs/task_loop.md)

## 下一步计划

> 详见 [千轮报告·第七八节](docs/reports/thousand-round-report.md)

1. **PGO v2 动态打点** (D1-D5): 分级采样 / KPI 阈值自适应告警 / phase_timing 热路径计时 / reply_rel 语义质量 / 对比基准自动化
2. **批 40+ 千轮持续** + 数据边界参数化用例组 + 长会话 10+ 轮扩展
3. **Vulkan 真 GPU 实测** (需真 GPU 环境, 本机仅 llvmpipe)
4. **真实数据网络溯源** + 多 LLM 交叉校验管线扩展

## 许可证

MIT — 见 [LICENSE](LICENSE)。
