# 能力差距分析 R338 — AgentFramework v0.17.x vs 成熟上线 Agent

> 方法 (用户钦定 "不伪造"): 每项缺口必须双证据 — ①本框架现状代码事实 (文件/行) ②参照系能力来源
> (官方文档/公告, 由调研子代理 deleg_bacfc319 产出 market-agent-capabilities-R338.md)。
> 只报"成熟产品普遍具备且本框架缺失"的真缺口; 能力方向不同/不适配不算缺口 (诚实边界)。

## 0. 本框架现状基线 (v0.17.2, 619 测, 代码事实)

- 单 CLI agent 主链 (IndustrialAgentV2): 意图→TaskPlan→8 源上下文注入→LLM→输出自审链 (OutputCritic/SelfCritic/FixMemory)→回注。
- 主题牵引 (L1 steer/L3 clarify + pulled_back), 隔离 (TopicRelevanceEvaluator 三路), 任务生命周期 (TaskCharter 三态路由)。
- 记忆分层 (session/长期/RAG 向量 bge 0.95), 梯度压缩 L0-L3 + 锚词, 压缩失败防护 D1-D4, 兜底粘性路由, 429 感知。
- skills 引擎 v0.16: SKILL.md 三形态 + 外挂目录 + 动态 whitelist/blacklist + KnowledgeHint 注入。
- 执行层 v0.17: 跨进程 FileLock/AtomicFileWriter/OccupantDetector/ExecutorLessonMemory + 离线变更审批 (staging) + 活动注册表。
- 脚本插件协议 v0.17.2-b: JSON Lines 事件流 {progress|heartbeat|done|error} + py_compile 验证 + 条件定时。
- eval: run_round 批测 (37 案 quick-13), 断言绑组件真实行为 (R149), token 周报, 286 批 99%+。
- AOT 发布 0 IL 警告; agent.io 协议库 netstandard2.1。

## 1. 本地候选缺口 (代码证据, 待外部对比定级)

### G1 git 自动化操作 — 无 (证据: 全仓 grep 无 git commit/add/PR 调用)
- 现状: AgentFramework 自身**没有任何 git 操作能力** (LibGit2/CLI git 均无调用点; 仓库的 commit/push 由宿主 Hermes 工具完成, 框架内不可用)。
- 成熟参照: 上线 coding agent (Claude Code/Cursor/Copilot) 均内置 git diff/commit/branch/PR 流程。
- 影响: coding 场景无法自查 diff/自动提交/开 PR; 迭代产物落地依赖外部。

### G2 浏览器自动化 / 网页交互 — 无 (证据: 全仓无 playwright/selenium/CDP)
- 现状: 探索链只做 URL GET digest + 链接发现 (HostExploreExecutor), **无 JS 渲染/表单填写/点击/登录态**。
- 成熟参照: 上线 agent 普遍带浏览器工具或 MCP 浏览器 (Claude Computer Use / Cursor browser)。
- 影响: 动态页面 (SPA/需登录) 探索与"真机验证 web 产物"能力缺失。

### G3 MCP 生态接入 — 无 (证据: 全仓无 mcp)
- 现状: 无 Model Context Protocol 客户端/服务端; 工具生态封闭在自研 skills。
- 成熟参照: 2025-2026 事实标准, Claude Desktop/Cursor/OpenHands 全部支持 MCP server 扩展 (数千现成工具)。
- 影响: 无法复用生态 (浏览器/slack/github/db 等现成 MCP 工具), 集成成本高。

### G4 计划-执行模式 UI 分离 — 无 (证据: 无 plan mode 指令/交互)
- 现状: TaskCharter 有任务章程但无"先出计划给用户确认再执行"的交互形态 (contribute/ack 风格)。
- 成熟参照: Claude Code plan mode / Cursor plan 是先计划获批后执行的标准交互。
- 影响: 高风险操作缺少用户前置确认闸 (已有 staging 审批但无计划层)。

### G5 代码库语义检索 (符号级/索引级) — 弱 (证据: 仅 keywordannotation + 锚词启发; 无 LSP/索引)
- 现状: 工作区召回 = 关键词 Contains + 相关分 (P4 流式化); 无符号/调用图/定义跳转级检索。
- 成熟参照: Cursor/Copilot 有代码库索引 (embedding + 符号混合); Claude Code 有 grep/glob 工具 + 语义。
- 影响: 大型代码库定位精度低于成熟产品 (批测文件场景够用, 真实库不足)。

### G6 IDE/编辑器集成 — 无 (证据: 无 vscode/jetbrains/lsp server)
- 现状: CLI 单形态 (REPL/单轮), 输出走 @chatbox 流式块 (宿主前端可接), 但无编辑器内联形态。
- 成熟参照: 主流 coding agent 均为 IDE 内联或 CLI+编辑器双形态。
- 影响: 用户"边看边改"体验缺 (staging 审批已部分补偿)。

### G7 多 agent 互操作 (A2A/agent 间协议) — 无
- 现状: subagent 是宿主内委派 (IsolatedTaskRunner 并发≤2), 无跨进程 agent 间标准协议。
- 成熟参照: A2A (Google 2025) / MCP 双向成为事实标准方向; OpenHands/Devin 有多 agent 编排。
- 影响: 生态协作受限 (但单机自研场景优先级低)。

### G8 成熟基准接轨 (SWE-bench 等) — 无
- 现状: 自有 eval 批测 (37 案, 真断言), 但未跑任何公开基准。
- 成熟参照: Claude Code/Cursor 等在 SWE-bench/TERA/Terminal-bench 有公开分数。
- 影响: 无法对外横向对比能力水位 (自证自评); 用户若需行业对标缺数据。

### G9 工具结果截断/长输出治理 — 部分 (证据: 需核实)

### G10 文件系统监视 (watcher) — 无 (FileSystemWatcher 无调用)
- 影响: 无"文件变更自动触发/等待用户改完继续"能力 (v0.17.1 审批冲突检测已覆盖等待语义一部分)。


## 1.5 14 维度对照表 (外部基线 → 本框架实况; 基线来源 market-agent-capabilities-R338.md §2)

| # | 成熟基线维度 | 本框架 | 证据 |
|---|---|---|---|
| 1 | Agent 核心循环 (plan→execute→verify→iterate, 长任务不跑飞) | ~ | TaskCharter/TaskPlan 有; 代码任务内 test/lint 失败→自愈闭环无 (自迭代 verify=eval 批, 非任务内) |
| 2 | 工具/多文件编辑 (diff 级应用, linter 反馈回路) | ~ | file_operation/workspace 整文件写; 无 diff 级应用/linter 反馈回路 |
| 3 | 执行沙箱与权限 (隔离执行/命令 allow-deny) | ~ | executive 脚本超时+kill-tree (ScriptPluginRunner); 无权限分级/危险命令拦截 |
| 4 | 检查点与回滚 (修改前快照一键回退) | ~ | ExecutionCheckpoint 会话恢复 ✓; 文件修改前快照自动回滚无 |
| 5 | 会话恢复/续跑 (resume, attach) | ✓ | ExecutionCheckpoint 原子持久化 + 活动注册表跨会话 |
| 6 | 计划模式与审批 (Plan/Act 分离, 逐工具权限) | ~ | v0.17.1 staged 文件审批 ✓ (基线冲突拒绝); 计划级确认闸无 (G4); 逐工具权限无 |
| 7 | 并行/后台任务 (subagent fan-out, worktree) | ~ | IsolatedTaskRunner 并发 2 + 微隔离; 无后台 agent/worktree 隔离 |
| 8 | 上下文与记忆 (auto-compact, 项目指令文件, 跨会话记忆) | ✓ | 梯度压缩/锚词/8 源注入/多级记忆 ✓; 项目指令文件机制无 (宿主 AGENTS) |
| 9 | MCP 与扩展生态 | ✗ | G3: 全仓无 MCP; skills 自研生态 (v0.16 外挂) 可作扩展底座 |
| 10 | 评测与基准 | ✓ 自有 / ✗ 公开 | 286 批真断言 (R149, 绑组件行为, 强于多数闭源自报); 无 SWE-bench 可比分 (G8) |
| 11 | 企业/团队治理 (SSO/RBAC/审计) | ✗ 不适配 | 单机 CLI 形态, 低优先 |
| 12 | 成本控制 | ✓ | 真实余额链/模型路由/429 感知/汇率/分层 (agent.modelqueue) |
| 13 | 限流与容错 | ✓ | 429 退避/兜底粘性/熔断 D1-D4/教训记忆/时序撞车检测 (v0.17.3) |
| 14 | 多环境与远程编排 | ~ | SocketChannel TCP 47810/共享内存 (本地进程面); 无云/远程控制 |

**结论 (诚实)**: 14 维中 ✓ 3 (5/8/12/13 计 4 — 记忆/成本/容错/会话恢复), ~ 6, ✗ 5 (3 项不适配低优先 G3/G8/治理)。**最强真实短板不在"执行机制"而在"外部能力接入面" (MCP/浏览器/IDE) 与"用户在场交互层" (计划审批/检查点回滚/工具权限)** — 即框架单机引擎扎实, 缺的是成熟产品标配的"人对 agent 的监督与生态接入"面。G1-G10 分级据此调整。

## 2. 分级原则 (待外部对比后定级)

- **P0 已闭/在闭**: G1 git (已闭 R338); 用户钦定三计划: v0.18.0 路由硬化 (已闭) / v0.17.3 撞车检测 (已闭核心) / v0.19.0 前端统一接口 (P1 实施中 — 补"用户在场交互层"最大缺口: 问询/审批/轨迹/推送一次拉全)。
- **P1 短中期**: G4 计划确认闸 (接 v0.19.0 ask/审批流) / G3 MCP 客户端 (最小 client 接入生态) / G2 浏览器 (MCP 浏览器优先, 自研次之)。
- **P2 观察**: G5 检索增强 / G8 SWE-bench 公开分 (定位若需对外) / G6 IDE / G7 A2A / G10 watcher。
- 定级依据: §1.5 对照 + 用户方向 (产品迭代框架 → 监督面优先) + 子代理 14 维基线 (2026-09-10)。
- 定级依据: 子代理市场能力清单 → 交叉验证 → 用户裁定后入计划 v0.18.0。
