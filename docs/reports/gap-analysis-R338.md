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

## 2. 分级原则 (待外部对比后定级)

- **P0 立即补** (影响主线价值 + 实现成本适中): G1 git、G3 MCP 客户端 (最小)、G4 计划确认
- **P1 短期补**: G2 浏览器 (或 MCP 浏览器接入替代自研)、G5 检索增强、G6 集成面
- **P2 观察/生态**: G7 A2A、G8 基准、G10
- 定级依据: 子代理市场能力清单 → 交叉验证 → 用户裁定后入计划 v0.18.0。
