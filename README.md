# click-agent (v0.17.2)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![.NET](https://img.shields.io/badge/.NET-10.0-512BD4)
![Tests](https://img.shields.io/badge/tests-619%2F619-brightgreen)
![NativeAOT](https://img.shields.io/badge/NativeAOT-zero%20warnings-blueviolet)
![Eval](https://img.shields.io/badge/迭代评测-286批%2099%25%2B-success)

**一个以文档驱动的全自动化产品迭代 Agent 框架。** 迭代循环由框架内生：计划文档（docs/plans）→ 代码落地 → 真实批测（eval/run_round，断言绑定组件真实行为）→ KPI 打点回授 → 验收存档（版本 tag + improvements 台账）→ 下一轮候选。文档是唯一权威源，记忆只存恢复指针。

框架本体（CLI agent）面向工业级多 agent 协作场景：跨进程执行加固（文件锁/原子写/占用者检测/教训记忆）、离线变更与用户审批（staging 区 + 基线 sha256 冲突拒绝，保护编辑器打开中的文件）、活动任务感知（多 CLI 心跳互见 + 条件调度原语）、上下文压缩/隔离/牵引/记忆分层全链。

**内部插件核心能力按需自行插入**——框架提供宿主机制与执行协议（技能三形态：executive 脚本交付 / normative 清单交付 / knowledge_hint 知识前置注入；脚本执行走 CLI 验证 → 插件服务，JSON Lines 事件流协议；像素画风锚定合成等渲染/领域能力由插件层扩展），能力边界由插入的插件/技能定义，而非框架写死。

net10.0 / NativeAOT 零 IL 警告 / 597 单测全绿 / 迭代评测 286 批通过率 99%+。
发布线: v0.17.2 — 执行层稳固化 T1-T4 (跨进程锁/占用者检测/教训记忆) / v0.17.1 离线变更用户审批 / v0.17.2-a 活动任务注册表 / v0.16 skills 引擎 (CLI 外挂+动态过滤+查询) / v0.15.2-A 存档版 / v0.14 critic 自审体系 / v0.13.3 思考链+渐进式探索 (+56pt)。

[🇬🇧 English → README_EN.md](README_EN.md)

---

### ✅ v0.20.0 LLM 服务独立进程 — llm-manager / worker (R342-R343 已落地, 真机 E2E 全通)
- **动因** (用户钦定): "将 llm 服务写成单独进程, 以免新 CLI 重新加载 LLM 到显存内"; 加载一次 LLM 成本极高 (bge 26MB 权重 → RSS ~157MB, LLM 更甚) → 0 实例时新 CLI 不得重载。
- **架构**: `llm-manager` 轻量常驻 (0 模型, 不随 CLI 生死) 对外 UDS 透明代理 → **lazy spawn** `llm-service-host` worker (真 bge) / **supervise** (worker 崩溃 → 下次请求自动重拉, 客户端无感) / **unload** (资源紧张 ∧ 无 CLI 实例 ∧ 无进行中请求 → **kill worker**, OS 回收全部 native 内存)。卸载判定不按时间 (内存充足常驻); 空闲长连接不阻止卸载; 熔断防重启风暴; SIGKILL 孤儿 worker 自动清理。
- **跨平台铁律** (用户 OOB 修正): 产品代码零 shell — `Process.Start`+`ArgumentList` / `Process.Kill(entireProcessTree)` / `Process.GetProcessById`+`HasExited`; daemon 自写日志; UDS; 非 Linux 内存探测优雅降级。
- **保留** (用户纠正): "仅是新增本机 llm host 而非全面修改当前框架 llm 使用流程" — DI/进程内路径原样, 客户端入口 `RemoteEmbedder` 显式选用。
- 真机 E2E: manager 0 模型 → lazy worker (RSS 157MB, bge 512 维) → kill -9 → 自动重拉 (pid 变化) → 阈值拉满 + 无 CLI 实例 → 卸载无残留。661 单测全绿 / AOT 13.6MB 零 IL 警告。

### ✅ v0.17.x 执行层稳固化 — 锁 / 原子写 / 审批 / 活动感知 (R334-R336 已落地, 验收批 284-286 全绿)
- **跨进程文件锁 + 原子写** (v0.17.0, 用户钦定 "2 agent 写 1 文件" 工业化): FileLock (.lock + FileShare.None=flock LOCK_EX, 崩溃内核自动放锁) / AtomicFileWriter (tmp+fsync+rename) / **OccupantDetector** (/proc/locks → "PID x (comm)") / ExecutorLessonMemory (失败→原因→**频率加权教训记忆**: 1 次摘要→3 次补方案→8 次补上下文, 24h 降级 7d 移除); 接入 TaskCharter/GuardrailMemory 写点 (同 Id 推进覆盖/异主让位/锁内条件覆盖 WriteIf 无 TOCTOU)。
- **离线变更 + 用户审批** (v0.17.1, 用户钦定 VS Code 场景): StagedFileStore (批次内容落 data/staged/ **不占真实文件地址**; 三阶段过期 TTL→expired 保留→reclaimable→显式清理, 不静默删) / ApprovalController (**锁内基线 sha256 比对 — 目标被编辑器改过 → 冲突拒绝绝不覆盖**; 多批按序合并, 后批基线过期 → partial 人工合并) / `/staged /approve /reject /cleanup` 指令 / `/staged --json` + data/staged/index.json 双通道供前端。
- **活动任务注册表** (v0.17.2-a, 用户钦定 "所有激活窗口任务"): ActivityService 心跳 data/activity/<pid>.json (pid/window/job_id/任务摘要; TTL 90s 覆盖 LLM 单轮; 优雅退出 finally 清理) / `/activity` 列出**全部激活 agent 含其他 CLI** / IsOtherAgentBusy = "无其他任务则 X 后执行" 条件原语。
- **脚本插件协议** (v0.17.2-b 计划已定): 执行层自需脚本一律 py → CLI py_compile 验证 → 插件服务执行; stdout JSON Lines 事件流 {progress|heartbeat|done|error}, 长执行 --heartbeat-secs 定时反馈, 结束前必须 done/error。

### 📦 v0.14-v0.16.x 能力 (critic 自审 / 任务生命周期 / skills 引擎 / 性能) + v0.12-v0.13.x 能力 (思考链 / 探索 / 视觉 / 渲染插件 / 底座防护)

已归档 → [CHANGELOG-v0.14-v0.16.x.md](docs/changelogs/CHANGELOG-v0.14-v0.16.x-R277-R336.md) · [CHANGELOG-v0.12-v0.13.x-R169-R268.md](docs/changelogs/CHANGELOG-v0.12-v0.13.x-R169-R268.md) · [CHANGELOG-v0.13.3-R249-R268.md](docs/changelogs/CHANGELOG-v0.13.3-R249-R268.md)

### 📊 迭代评测统计 (打点对比数据驱动)

| 维度 | 基线 | 当前 (2026-09-10) | 改善 |
|---|---|---|---|
| 评测通过率 | 7354tok 基线 10 用例 | **286 批落盘, 近 30 批 99%+** (quick-13 口径) | 负面扩容+真断言后稳定 |
| 单元测试 | 325 | **597** | +272 |
| 真缺陷修复 | — | **72+ 项** (全部打点驱动) | 含 C14 flake 根因 (R332 per-case 隔离) |
| token 使用量 (KPI-2) | era2 730 | **quick-11 1144 / quick-13 ~1765** (口径细分见报告) | 每 10 批周报 (`eval/token_report.py`) |
| 召回率 (RAG) | 词袋 0.45 | **bge 0.95 / 词袋长查询 0.70** | 三口径基线 |
| 压缩关键信息保留 | SummarySentences 33-53% | **keys 100% / 指令 96%** (104 篇多样态 audit) | 健康线 ≥95% |
| 探索 A/B (可达 URL 24 案) | — | **hit 0.167→0.722 (+56pt, R310 复跑) 零回归** | v0.13.3 探索链 |
| critic 知识前置 (skill 版) | 事后扫描 | **C33-C35 诱饵 3/3 生成时预防含例外理解** (R326g) | knowledge_hint |

### 批次趋势 (滚动窗口 — 最新 2 批)

**批286 (round 513)** 13/13 quick-13 1811/case (v0.17.2-a activity 验收) / **批285 (round 512)** 13/13 quick-13 1765/case (v0.17.1 staged 验收) —
v0.17 执行层稳固化定档: 跨进程锁+占用者检测+教训记忆 / 离线变更审批 (基线比对冲突拒绝 E2E 三场景) / 活动注册表 (双实例互见 win/job_id) —
v0.16 skills 引擎 (CLI 外挂/动态过滤//skills 指令族, 批280 37/37) — v0.15.2 guardrail 真断言 (批271 5/5, C27 否定词"不"补围栏) —
R332 eval per-case 隔离 (C14 flake 根因, run_round 每 case 前清 sessions+rag) — 探索 +56pt 历史最高 (R310) —
版本A 存档 tag v0.15.2-A (批272-273/277 验收)。

归档: [42-78](docs/changelogs/CHANGELOG-v0.11.0-R143-R152.md) · [79-108](docs/changelogs/CHANGELOG-v0.11.0-R153-R168.md) · [109-138](docs/changelogs/CHANGELOG-v0.11.0-R169-R185.md) · [139-167](docs/changelogs/CHANGELOG-v0.11.0-R186-R204.md) · [168-177](docs/changelogs/CHANGELOG-v0.11.0-R205-R218.md) · [178-187](docs/changelogs/CHANGELOG-v0.11.0-R219-R228.md) · [188-217](docs/changelogs/CHANGELOG-v0.13.x-R229-R248.md) · [218-247](docs/changelogs/CHANGELOG-v0.13.3-R249-R268.md)。每 30 批滚动; 下一点≈批307。

### 🧭 能力全景

**工程总览**: 19 csproj — agent (主链 25+ 子模块: intent/registry/memory/contextassembler/tendency/session/search/llamalocal/maf/pipeline/subagent/critique/tasks/execution/staging/activity 等) / core / config / contextgradient / modelqueue / skills / rag / vectormemory / workspace / io / logging / output / recovery / codegen / host / tests。

**文档驱动迭代循环 (框架内生, 用户钦定方向)**
- 计划 → 代码 → **真实批测** (断言绑组件真实行为, R149 标准) → 打点回授 (AgentTelemetry JSONL 全链) → 验收存档 (tag + improvements) → 下轮候选 (master-plan 触发器与宪法八条)

**执行层稳固化 (v0.17.x, 用户钦定 "2 agent 写 1 文件" 族)**
- 跨进程 FileLock (flock 内核仲裁, 崩溃自动放锁) + AtomicFileWriter (无半写) + OccupantDetector (/proc/locks 占用者 pid/comm)
- ExecutorLessonMemory 频率加权教训记忆 (失败原因→方案→上下文, TTL 衰减)
- StagedFileStore 离线变更审批 (VS Code 编辑保护: 基线 sha256 冲突绝不覆盖) + ActivityService 活动心跳 (多 CLI 互见/job_id/条件原语)

**推理与任务**
- 意图分析与子任务细分: 19 中英连接词, Sequential/Parallel/DependsOnOutput 关系; 创作类拦截
- TaskPlan 拓扑执行: Level 并发 / 节点重试 / 敏感意图 PausedForApproval; TaskCharter 任务生命周期 (三态输入路由)
- 隔离任务: 无关话题边界隔离 subagent (独立 session, 主记忆零污染), 完成即销毁; TopicRelevanceEvaluator 合并判定 (隔离/牵引/打点三路)

**模型调度 (agent.modelqueue)**
- 本地 (LocalLlamaCaller 真跑) > 官方 > 远程 API 三通道; 22+ 模型目录; auto/manual 双模; 粘性路由 (兜底性价比序 + 三门判定)
- 余额链: 真 API 同步; 余额不足自动切模; 汇率 CNY÷7.2

**视觉与图像**
- 视觉理解链: CLI `-img` → glm-5.3-flash v4 (1M ctx); text-only 自动重路由
- 图像渲染插件: IImageRenderPlugin (SkiaSharp 默认 / SVG 文本兜底) + LocalSvgRenderer DSL (像素画风锚定合成类能力由插件层扩展); 收敛环 E2E

**探索与思考链**
- 渐进式探索: ExplorationPlanner (每源最大步 config; 上下文内 URL > 上下文外目录)
- 思考链收敛: ComplexityGate + EvidenceScorer + ThinkMemory bge 联想 (跨进程持久化)
- critic 自审 (v0.14): OutputCritic 静态 8 规则 / SelfCritic quote 逐字锚 / FixMemory 来源秩 / CriticPipeline 三级过滤

**Skill 调度 (agent.skills, v0.16 增强)**
- SKILL.md 目录包三形态 (executive/normative/knowledge_hint); CLI 外挂 --skills-dir/--skills-file/--skills-blacklist; 动态 whitelist/blacklist; /skills 指令
- 四级触发: 关键词 → 正则 → 领域词 → bge 语义 (cos≥0.45)

**上下文与记忆**
- 梯度压缩 L0-L3 + 锚词 (P10 long-key 零分配) + 三重漂移校验 (bge 真向量)
- 8 源上下文注入: Memory/Session/Workspace/AgentContext/UserTendency/WebSearch/ToolOutput/SessionMemory — 各源召回明细打点

**配置与输出**
- 四层 YAML 配置 (Yamlify, 零反射) + IOutputSink 统一输出 (库内零 Console 直写)
- PGO 打点: AgentTelemetry JSONL (30+ 点位)

**工程**
- NativeAOT: 端到端 0 IL 警告 (JIT 仅测试手段, 发布形态必为 AOT — 钦定铁律)
- Session 恢复: ExecutionCheckpoint 原子持久化; agent.io 协议库 (netstandard2.1 零依赖)

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

# 外挂 skills 目录 (v0.16)
dotnet run -- --skills-dir /path/to/skills --skills-blacklist wordcount

# 环境变量
# AGENTFRAMEWORK_KEYS_BIGMODEL / AGENTFRAMEWORK_KEYS_DEEPSEEK / AGENTFRAMEWORK_KEYS_KIMI
# AGENTFRAMEWORK_BGE_MODEL=bge 模型路径 (启用真向量链)
# AGENTFRAMEWORK_MIN_BALANCE_USD=0.50 (余额阈值)
# AGENTFRAMEWORK_WINDOW / AGENTFRAMEWORK_JOB_ID (活动注册身份, v0.17.2)
```

CLI 内置命令: `/balance` · `/model` · `/status` · `/reset` · `/skills` (`/skills-only|exclude`) · `/staged` (`diff`) · `/approve` · `/reject` · `/cleanup` · `/activity` · `/exit`。

### 评测复现

```bash
cd eval
python3 run_round.py --quick 513 "label"        # quick 13 用例 (高频回归)
python3 run_round.py 513 "label"                # 全量 37 用例
python3 token_report.py                          # KPI-2 token 周报 (每 10 批)
```

## 验证基线 (2026-09-10)

| 项 | 结果 |
|---|---|
| 单元测试 | **597/597** 通过 (含 ExecutorHardening 并发/StagedApproval/ActivityService 族) |
| NativeAOT (linux-x64) | **0 IL 警告** (多次复验) + full-graph AOT 冒烟通过 |
| 迭代评测 | **286 批落盘, 近 30 批 99%+** (quick-13 口径); 批280 全量 37/37 |
| 双实例并发写文件 | 60/60 零交错 (flock 真机) + 8 线程 120 行零丢失 (单测) |
| 离线审批 E2E | VS Code 编辑中 → approve 冲突拒绝不覆盖 ✓ → 恢复基线 → 应用 ✓ |
| 活动注册 E2E | 双实例 /activity 互见 (pid/win/job_id/任务摘要) ✓ |
| 探索 A/B (24 案) | hit **0.167→0.722 (+56pt, R310 复跑) 零回归** |
| critic 知识前置 | C33-C35 诱饵 3/3 (含 R03 例外条款理解) |
| 压缩 audit | 104 篇多样态: keys 100% / 指令 96% / 压缩率 79-92% |
| 3 端点真机 | glm/deepseek 对话+余额 ✓; kimi 负样本诚实报错 ✓ |
| bge 真链 | JIT+AOT 双验收 ✓ (单实例共享 RSS 130MB) |

## 文档

- [架构文档](docs/architecture.md) · [API](docs/api.md) · [CLI 指令](docs/CLI指令说明.md)
- [迭代方法论总纲](docs/reports/iteration-master-plan.md) — 宪法八条 / 5 KPI / 触发器 / 真实性五道防线 (活文档)
- [主报告·动态打点与回滚](docs/reports/dynamic-telemetry-eval-rollback-strategy.md) — 状态层 (活文档, 每轮更新)
- [改进记录](docs/improvements.md) — R309 起逐轮补录 (活文档, 顶部最新)
- 版本计划: [v0.17.2 活动+脚本协议](docs/plans/v0.17.2-activity-script-plan.md) · [v0.17.1 审批](docs/plans/v0.17.1-staged-approval-plan.md) · [v0.17.0 执行层](docs/plans/v0.17.0-executor-hardening-plan.md)
- 历史: [CHANGELOGs](docs/changelogs/) · [测试维度总账](docs/reports/test-dimensions-ledger.md) · 千轮报告 §6 冻结版

## 下一步计划 (2026-09-10 核定)

> 详见 [主报告 §7](docs/reports/dynamic-telemetry-eval-rollback-strategy.md) 与 [方法论 §7 节奏表](docs/reports/iteration-master-plan.md)

1. **v0.17.2-b 脚本插件协议落地**: py 验证 → 插件服务执行 + JSON Lines 事件流包装 (协议已定稿 docs/plans/v0.17.2-activity-script-plan.md §2)
2. **v0.17.2-c 条件定时**: "无其他任务则 X 后执行" (IsOtherAgentBusy 原语已就绪) + 定时任务 skill
3. **产出侧 staging 接入**: `--stage-writes` 开关让 agent 文件产出默认进审批区 (v0.17.1 审批层已全通)
4. **eval 加固续**: C14 隔离族连续批观察 (R332 修复后多批验证) + 教训记忆注入效果实测

## 许可证

MIT — 见 [LICENSE](LICENSE)。
