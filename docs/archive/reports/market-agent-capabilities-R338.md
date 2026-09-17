# 2026 年成熟上线 AI Coding Agent 产品能力清单（市场调研）

> 调研用途：与自研 C# agent 框架做诚实差距分析（gap analysis）。
> 调研日期：2026-09-10。覆盖产品/框架：Claude Code、Cursor、OpenHands、Devin、Google Jules、GitHub Copilot coding agent（含 Copilot CLI）、Cline / Roo Code、Windsurf（现 Devin Desktop）。
>
> ## 可信度图例（贯穿全文）
> - 【官方】= 官方文档 / 官方 changelog / 官方公告页面可直接查证（本次调研已抓取或搜索摘要原文可证）。
> - 【第三方】= 多家或专业第三方来源一致报道，官方页面未逐一核实；可信度中-高。
> - 【传闻】= 单一来源 / 无法核实 / 相互矛盾的社区说法，**不得当作事实用于差距判断**。
>
> 重要提醒：本领域信息变化极快，"官方"只代表该来源网页当前声称的内容；所有厂商自报能力与基准分均未独立复现。

---

## 一、逐产品能力清单

---

### 1. Claude Code（Anthropic）—— 终端/IDE/云端一体的 agentic 编码工具

**身份与形态（2025–2026 演进）**
- 2025-05（Claude 4 发布同日）从 research preview 转 GA【官方】：terminal 为主 + VS Code / JetBrains 扩展（beta）+ GitHub Actions 后台任务 + Claude Code SDK。
- 2025-09-29【官方】：原生 VS Code 扩展、终端 UI 2.0、checkpoints 上线（Sonnet 4.5 驱动），SDK 支持 subagents 与 hooks；Claude Agent SDK 提供与 Claude Code 相同的核心工具/上下文/权限框架。
- 2026 迭代（官方 changelog v2.1.x 持续）：Desktop 应用、Claude Code on the Web（cloud sessions）、Remote Control（手机/浏览器/桌面远程接管会话）、Claude Code on GitHub（PR 里 tag 触发）、agent teams、dynamic workflows、/ultrareview 等。

**核心能力（按维度）**
- **Agent 循环**【官方】：主 agent + 内置工具（Read/Write/Edit/Bash/Glob/Grep/Task 等）的 ReAct 循环；`--agent` 主线程 agent；Workflow tool（动态编排）；"How Claude Code works" 文档专门描述 agentic loop 与 prompt caching 自动管理。
- **计划模式**【官方】：Plan mode（内置 Plan subagent；权限模式之一）；permission 模式体系：default / acceptEdits / plan / auto / bypassPermissions；2026 新增 auto mode（Max 用户，Claude 代做权限决策，更少打断）。计划-执行-审批-执行的工作流成熟。
- **工具/多文件编辑**【官方】：文件工具、linter/hook 集成；`/diff`（2026-09 新增侧边 diff 面板）；`--rewind-files`；批量并行 tool calls。
- **沙箱**【官方】：sandboxed Bash tool（文件系统+网络隔离，allowlist/deniedDomains、credentials 注入）；可选 sandbox runtime、dev container、Docker、VM；权限规则按路径/命令/网络细粒度控制；Windows/macOS 覆盖。这是所有被调研产品中沙箱文档最深的之一。
- **检查点/恢复**【官方】：checkpoints 自动在每次修改前保存代码状态，Esc-Esc 或 `/rewind` 回滚；可分别选择恢复代码 / 会话 / 两者；与 git 配合；`-p --resume`/`--continue` 会话恢复；background session attach（`claude attach <id>`）。
- **后台任务/并行**【官方】：后台任务（background tasks，长跑进程不阻塞）；subagents（自定义 markdown agent，默认后台运行）；agent teams（多 agent 协作）；dynamic workflows（claude 写脚本编排几十到几百个并行 subagent，GA）；git worktrees 并行隔离会话（`--worktree`）。
- **记忆/上下文管理**【官方】：auto-compact（1M 上下文模型临近上限自动压缩）、/compact、PreCompact hooks 可阻断压缩；CLAUDE.md 层级记忆 + auto memory；Skills（自定义技能，含内置技能）；/context、/cost 可见性；prompt caching 自动管理与统计。
- **MCP 生态**【官方】：MCP 服务器接入（含 marketplace/plugins）、MCP-tool hooks、Agent MCP servers、SDK 提供 MCP server 配置。
- **评测基准**：Anthropic 模型公告（Opus 4/4.5/4.7/5、Sonnet 4.6）有内部 agentic evals 相对提升表述【官方】（如"hardest agentic coding tasks +22% over Opus 4.7"）；但具体 SWE-bench Verified 分数未见官方第一手页（"~80.9%，2026 初"系第三方 tekai 转述）【第三方，谨慎】。
- **企业/IDE 集成**【官方】：VS Code 扩展、Desktop、JetBrains（beta）、Claude Code on GitHub（PR tag）、Remote Control；Bedrock/Vertex/Foundry 认证；managed settings/组织策略/企业网关（spend limits、usage credits）。
- **审批流**：上述 permission 模式 + hooks（PreToolUse/PostToolUse 等可拦可批）【官方】；auto mode 保留"少打断但有护栏"的平衡【官方】。
- **成本控制**【官方】：/cost 逐会话成本 + prompt-cache 命中统计；/usage 用量与 spend limit 状态栏；模型/effort 切换控制 token 消耗；usage credits。
- **限流容错**【官方】：429 重试处理（含 Bedrock/Vertex 侧修复）、API timeout（API_TIMEOUT_MS 默认 10 分钟）、retry watchdog、stalled subagent 10 分钟超时报错、被 kill 的 background session 可恢复、SDK MCP handshake 70s 超时等——changelog 大量条目证明其对长跑任务可靠性的投入。

**一句话定位**：终端原生的"全栈 agent runtime"，能力面最全、文档最透明；沙箱/权限/检查点体系是行业参照系之一。

---

### 2. Cursor（Anysphere）—— AI 原生 IDE + 云端后台 agent（Composer/Background→Cloud Agents）

**身份与形态（官方 changelog 时间线）**
- 0.48（2025-04）【官方】：Agent 可自动跑终端命令、读 linter 错误自修复、多位置并行编辑、Composer 检查点跨重启持久化。
- 0.50（2025-05）【官方】：Background Agent preview——agent 在**独立远端环境**运行，多 agent 并行，可查看状态/发跟进/接管。
- 1.0（2025-06-04）【官方】：BugBot（自动 PR 代码评审）GA、Background Agent 全员可用、一键 MCP 安装、memories 首秀、Jupyter 支持。
- 1.1（2025-06）【官方】：Slack 内 @Cursor 启动 Background Agents。
- 1.2（2025-07）【官方】：Agent To-dos、PR 语义索引/检索、合并冲突可由 agent 解决。
- 1.4（2025-08）【官方】：GitHub PR 内 @Cursor（读 prompt→修复→push commit）。
- 1.7（2025-09）【官方】：Plan Mode（先写详细计划再执行，支持更长任务）、浏览器控制、hooks、终端沙箱化（1.7.26）。
- 2.0（2025-10-29）【官方】：自研 Composer 编码模型；Multi-Agents（单 prompt 最多 **8 个并行 agent**，git worktrees 或远端机器隔离）；Sandboxed Terminals GA；团队级 commands/rules；Voice mode；后台 Plan Mode；Background Agents **改名 Cloud Agents**（宣称 99.9% 可靠性、秒级启动）；audit log；会话/计划管理侧栏。
- 3.0（2026-04-02，官方 changelog 页确认）【官方】：Agent-first 重构——Agents Window（本地 / worktree / 云 / 远端 SSH 并行跑多个 agent）、Design Mode（浏览器内 UI 标注）、Agent Tabs、`/worktree`、`/best-of-n`（多模型并行跑同一任务对比）、`Await` 工具（等后台命令/subagent 输出）、MCP Apps 结构化内容、企业审计与 admin 控制增强。
- 3.5 及 Cloud Agents 的 computer-use/桌面/浏览器全环境升级【第三方】（社区称 2026-05-20；官方 changelog 未在本次调研中核实到该条目）——**详见盲区**。

**核心能力**
- **Agent 循环/工具**【官方】：Agent 模式工具面 = 文件编辑、grep+语义检索（代码库索引）、终端、浏览器；Yolo mode 自动批准（0.48）；Tab 模型。
- **计划模式**【官方】：1.7 Plan Mode；2.0 可在后台计划、并行多计划评审；3.0 plans 随共享会话导出。
- **多文件编辑**【官方】：0.48 起多位置并行编辑 + 智能 apply 模型；多文件 diff 评审视图。
- **检查点**【官方】：Composer/agent 检查点持久化（0.48）、跨重启保留；(修复类条目见 0.50.2)。**注意**：Cursor 的 checkpoint 更多是"会话内可回滚 + 持久化"，没有 Claude Code 那种全自动代码快照/双 Esc 回滚的显式公开功能表述。
- **后台/并行**【官方】：Cloud/Background Agents（独立远端 Ubuntu 环境、异步、PR 产出）；2.0 最多 8 并行 agent（本地 worktree/远端）；3.0 Agents Window + `/best-of-n` + worktree 命令；Slack/GitHub 触发入口。
- **记忆/上下文**【官方】：代码库向量索引（语义检索）；memories（1.0 首秀）；团队级 rules/commands 云端管理（2.0）。无类似 CLAUDE.md 的开放文件标准，偏向 IDE 内部闭源机制。
- **MCP**【官方】：一键安装 + 官方服务器精选 + OAuth；project `.cursor/mcp.json`；MCP Apps（3.0，结构化内容）。
- **沙箱**【官方】：终端沙箱化 + Sandboxed Terminals GA（2.0）；cloud agents 运行在隔离云端 VM。
- **评测基准**：无公开官方基准分数【—】；Composer 模型"4x 速度/frontier 级"等为官方博客营销表述【官方营销口径】，Composer 2.5"基于 Moonshot Kimi K2.5、10x 效率"等为 X/社区转述【传闻】。
- **企业/IDE**【官方】：VS Code fork 深度（原生内嵌而非插件）；SOC 2；团队 admin/审计日志/用量 API；SSO/隐私模式；JetBrains 经 Agent Client Protocol 支持【第三方】。
- **审批流**【官方】：逐动作权限提示 / Yolo auto-approve / 权限记忆；human-in-the-loop 的 diff 审阅为主。
- **成本**【官方】信用点（credits）计量制；Pro $20/月（社区多来源一致）；**并行 agent 3–5x 消耗信用点**为第三方观察【第三方】。
- **限流容错**：后台 agent 可用性/可靠性持续改进（官方 changelog 多条 fix 与"99.9% 可靠性"宣传）【官方】。

**一句话定位**：把"agent 编排"做成 IDE 一等公民；多 agent 并行（worktree/云端）与自研模型是差异化点；但许多机制是 IDE 内闭源的，外部可验证性低于 CLI 型工具。

---

### 3. OpenHands（原 OpenDevin，All Hands AI）—— 开源 agent 平台 + 云服务

**身份与形态**
- 开源平台（MIT 核心，社区称 6.5 万+ stars），ICLR 2025 论文背书【官方/学术】；GUI、CLI、headless、SDK 四形态【官方 docs】。
- OpenHands Cloud / 企业版（SaaS、BYOK、RBAC、audit trails、自托管 Helm/K8s）【官方营销页 + 第三方】。
- "1.0 发布：生产级 Docker 沙箱 + 安全策略 + 资源限制 + 插件系统"——多个独立博客一致报道（时间约 2025 末–2026 初）【第三方】；官方 GitHub release 页未在本次调研直接核实（见盲区）。

**核心能力**
- **Agent 循环**【官方 docs/SDK 架构】：CodeAct 思想（动作统一为代码）；reasoning-action loop 单步执行、事件流（event stream）架构、每步可原子中断/暂停/恢复；Agent SDK（2025 论文）。
- **工具使用**【官方】：（沙箱内）任意 Linux bash、IPython 交互、浏览器；AgentSkills 工具库（可扩展、含视觉/PDF 解析等）。模型无关（Anthropic/OpenAI/Gemini/开源模型，LiteLLM 网关）【官方+第三方】。
- **沙箱**【官方】：每次任务会话拉起隔离 Docker 容器（bash+IPython+browser 运行时）；SecurityAnalyzer 在动作执行前做风险校验；confirmation（人工确认门）机制内建于 loop。
- **多文件编辑**：通过 bash/编辑工具在沙箱内自由操作（平台不限定 IDE 式 diff）；更依赖模型能力的通用编辑。
- **检查点/恢复**：事件流本身可回放，会话步骤原子化；CLI/会话级 resume 支持情况本次未核实【未知】。
- **计划/审批**：Agent 对话中可提问澄清；confirmation 模式（WAITING_FOR_CONFIRMATION）【官方架构】；未见产品级"plan mode"宣传【—】。
- **后台/并行**：multi-agent 协调（ManagerAgent 拆分任务给微 agent）【官方 README/社区】；云上异步任务执行【官方营销页】。并行度深度不如 Cursor/Claude Code 显性化。
- **记忆/上下文**：loop 内 condenser（历史压缩，token 临近上限时）【官方 SDK 架构】；AgentSkills/上下文组装；无强跨会话记忆体系（组织级另有云产品）。
- **MCP**：文档存在 MCP 配置支持【官方 docs 体系，未逐页核实】。
- **评测基准**：SWE-bench Verified 公开跑分是它的招牌——不同模型/配置 60.6%（Claude 3.7 单次）→66.4%（5 路并行+critic）→约 68%（Qwen3-Coder-480B）→72%（Sonnet 4.5+thinking）→77.6%（2026 初 leaderboard 快照，官方榜单自报）【第三方，区间矛盾需谨慎】。因为开源可复现性最强，其分数在"open-source agent 代表"层面参考价值高；但 harness 差异可导致 ±15–20 分（byteiota 警告）。
- **企业/IDE**：Jira/GitHub/GitLab/Bitbucket/Slack 集成；云产品带 RBAC/audit/BYOK；IDE 形态弱（不是编辑器产品）。
- **成本**：开源自跑（token 成本 ~$0.3–3/任务，社区估）；云服务订阅制【第三方】。
- **限流容错**：模型提供商侧由 LiteLLM 层代理切换；平台级重试/容错细节未见系统化公开。

**一句话定位**：最可信的开源"平台型"agent（可自托管+可评测+模型无关）；但产品化打磨（检查点 UX、IDE、企业完整度）弱于商业闭源产品。

---

### 4. Devin（Cognition）—— 云端自主软件工程师

**身份与形态**
- 2024 年 GA 的首个"AI 软件工程师"品类开创者；形态 = Web app 内云端工作区（VM + 编辑器 + 浏览器 + shell），会话异步在云上执行。
- 2025-09-29【官方博客】：为 Claude Sonnet 4.5 重写新 Devin（"New Devin agent"，2x 快），旧 agent 保留可选；后升级覆盖全部企业客户【官方 release notes】。
- 2025-12【官方（多家媒体一致）+ 官方 docs 迁移佐证】：收购 Windsurf（$250M 为媒体报道数字，官方未披露价格，见传闻区）；2026 品牌整合为 Devin 系（Devin Desktop）。

**核心能力**
- **Agent 循环**【官方】：plans→executes→iterates 自主循环，计划显式可见（plan 展示/分步回放）；多动作乐观并行执行（multi-action：看浏览器+跑命令+读多文件同时进行）；batch edits（"fan out"并行改任意数量文件，专为重复性重构）。
- **工具/多文件**【官方】：shell、编辑器、浏览器（多 tab、自动开 tab 处理 auth 流）、computer use（全部 agent 版本可用，release notes 去掉 beta 限制）；跨文件重构上下文能力多次改进。
- **沙箱**【官方】：每会话独立云端工作区（machine snapshot）；repo setup 验证（lint/install/test 命令预校验）；git 权限/网络受企业策略管控。
- **检查点/恢复**：会话中可用方向键沿工作区时间步回放（workspace progress 回放）【官方】；工作区快照/环境缓存存在（clone via API + snapshot 管理）【官方】；但"代码级自动 checkpoint/回滚"不是其显式公开卖点【—】。
- **计划/审批**：/plan、/review、/test、/think-hard 等 slash commands（官方 release notes，企业可自定义 slash commands）；人类在会话中可提问/打断/跟进；PR 评论驱动的修改闭环（读 review 意见并逐条处理）【官方】。
- **后台/并行**：会话天然异步云端后台执行（Slack/Teams 内 @Devin 触发）；automations、batch/子会话（sub-Devin sessions、会话层级）【官方】。
- **记忆/上下文**【官方】：Knowledge（知识条目/文件夹，agent 会话中可自动沉淀）；Playbooks（可复用任务模板，团队/企业级共享）；Enterprise Knowledge（org 级共享上下文）；DeepWiki 自动仓库文档；Ask Devin 助手。模型对长会话有自身 compacting/summarization 系统（官方博客坦承模型自摘要不如系统压缩可靠——**官方诚实性样本**）。
- **MCP**【官方】：MCP marketplace 连接数据源；企业级 MCP 用量追踪与可观测性；Redshift MCP 等生产化。
- **评测基准**：官方自报内部 "Junior Developer Evals"（Sonnet 4.5 版 +12%）、planning evals（+18%）、multi-hour 会话可靠性提升【官方，但内部集不公开】；SWE-bench Verified 绝对分数（45.8% Devin 2.0、77.8% SWE-1.7 等）均为第三方转述【第三方/传闻，矛盾】。
- **企业/IDE**【官方】：GitHub/GitLab/Bitbucket/Azure DevOps、Slack（含 Enterprise Grid）、Teams、Jira；VS Code 内使用；Enterprise API v1/v2/v3、service users、RBAC、audit logs、消费分析仪表盘、git 权限管理、SSO。企业功能是商业 agent 中最深的之一。
- **成本**【官方】：订阅 + ACU（Agent Compute Units）计量消耗；企业可设额外用量预算；官方最佳实践提示"长会话性能下降，建议 <10 ACU/会话"（**官方承认长任务质量衰减**）。
- **限流容错**：官方 best practices + release notes 大量稳定性修复；公开细节少于 Claude Code。

**一句话定位**：把"委托给一个远程工程师"做到极致（企业治理/审计/集成最完整），但它是闭源黑盒：agent 内部机制、评测集、模型组合公开度低。

---

### 5. Google Jules —— 异步云上编码 agent（GitHub 仓库）

**身份与形态**
- 2025-05-19 发布【官方 changelog】；2025-08-06 出 public beta，对所有人开放【官方 blog】；运行在 Google Cloud VM（安全隔离、私有默认、不拿私有代码训练）。
- 2026 首页已标 Gemini 3 Pro（Pro/Ultra 档）与 Gemini 2.5 Pro（基础档）【官方首页】。

**核心能力**
- **Agent 循环**【官方】：克隆仓库→读上下文→出计划→（人类批准后）改代码→跑测试→开 PR；plan/reasoning/diff 全程可见；2025-06 升级：读 AGENTS.md、更少"放弃"(punting)、环境 setup 脚本稳定执行、更主动写/跑测试。
- **多文件/测试**【官方】：多文件变更、依赖升级/迁移、测试补写、GitHub issues 集成（issue 打 `jules` label 直接派活）。
- **沙箱/执行环境**【官方】：Google Cloud VM 隔离执行；environment setup 复用（"reusing previous setups so new tasks run faster"）。
- **并行/后台**【官方定价页】：异步并发有硬性层级——免费 15 任务/天 & 3 并发；Pro 100/天 & 15 并发；Ultra 300/天 & 60 并发（"massively parallel"）。是官方明示并发能力的少数产品。
- **检查点/恢复**：任务失败可重跑环境设置？未见代码级检查点；"setup reuse"是环境缓存而非检查点【—】。
- **计划/审批**【官方】：执行前计划审批流（"approve Jules' plan"）；执行中可给反馈。
- **上下文/记忆**：AGENTS.md 支持【官方】；无跨任务持久记忆公开。
- **MCP**：未见于公开文档（本次调研未见官方 MCP 条目）【信息不足】。
- **评测**：无公开基准【—】。
- **企业/IDE**：GitHub 生态为主；CLI 与 API 存在【官方首页】；无企业 SSO/RBAC 宣传；面向个人/团队级 Google AI Pro/Ultra 订阅捆绑。
- **成本/限流**：任务/天 + 并发的**硬性限流即产品分层**【官方】；无超预算机制。

**一句话定位**：最"干净"的异步单任务 agent（VM 隔离+PR 闭环+显式并发配额），能力清单最短、扩展面最窄（无 MCP/无记忆/无沙箱策略自定义），是"保守可预测"路线的代表。

---

### 6. GitHub Copilot coding agent（含 Copilot CLI）

说明：GitHub 侧实际是三层——(a) GitHub.com 上的后台 coding agent（issue→draft PR）；(b) Copilot CLI（终端 agent，2026-02 GA）；(c) IDE 内 agent mode。此处合述但逐层标注。

**身份与形态**
- (a) 2025-05-19 发布 preview（Pro+/Enterprise）【官方 blog】→ 2025-06-24 开放 Business【官方 changelog】→ 2025-09-25 GA 全量付费用户【官方 changelog】。跑在 **GitHub Actions** 环境里。
- (b) Copilot CLI：2025-09 public preview → 2026-02-25 GA【官方 github.blog changelog】。
- (c) IDE agent mode：VS Code 起，扩至 Xcode/Eclipse/JetBrains/Visual Studio【官方 blog】。

**核心能力（coding agent，GitHub.com）**
- **循环**【官方】：指派 issue 或 Chat 里 `@github` → 起 draft PR → Actions VM 里克隆/装环境/RAG（GitHub code search）分析 → 推 commit + 更新 PR 描述 → 完成后 tag 你 review；PR 评论可继续驱动修改。
- **多文件/测试**：声明支持新功能/bugfix/重构/测试补齐/文档【官方】；agent session logs 可见推理与验证步骤【官方】。
- **沙箱**【官方】：安全、可定制的 Actions 开发环境；分支保护等既有策略照常生效。
- **审批流**：PR 评审为门（人类 review 后 agent 迭代）【官方】；无 IDE 式逐动作权限。
- **MCP**【官方】：仓库设置里可配 MCP servers 给 coding agent 外部数据/工具。
- **成本**【官方】：消耗 GitHub Actions 分钟 + premium requests（2025-06-04 起 1 模型请求 = 1 premium request）。
- **记忆**：无公开跨会话记忆（repo 内 AGENTS.md 语境）。并行：可同时对多个 issue 派活（数量受策略约束）。
- **评测**：无官方公开基准【—】。

**核心能力（Copilot CLI，2026-02 GA）**
- **循环/模式**【官方】：Ask（默认）/ **Plan**（Shift+Tab，先提问澄清+结构化计划，批准后执行）/ **Autopilot**（全自主无审批，`--plan --mode autopilot` 先计划后执行）；内置专门 agent（Explore 快速代码分析 / Task 跑构建测试 / Code Review / Plan），**多个 agent 可并行**【官方 GA 文】。
- **后台委派**【官方】：`&` 前缀或 `/delegate` → 推给云端 Copilot coding agent（起分支、draft PR、后台跑），`/resume` 无缝切本地/远端会话；`/fleet` 把计划拆给多个子 agent 并行【第三方，与官方"多 agent 并行"一致】。
- **工具/沙箱**【官方 changelog】：终端沙箱化（macOS/Linux/Windows 网络与文件策略、sandboxed commands）；权限分级（按 tool 的 allow/deny，`--allow-tool`/`--deny-tool`）【第三方指南 + 官方 flags 语义一致】；文件编辑、跑测试、MCP 工具、/review 预提交评审。
- **检查点/恢复**【官方】：Esc-Esc rewind 文件到会话内任意快照；会话可长跑；`/worktree new` 开 worktree 会话。
- **上下文/记忆**【官方】：**auto-compaction（~95% 上下文自动后台压缩，会话无限长）**；**repository memory（跨会话记住代码库约定/模式/偏好）**——这是官方明示的跨会话记忆少数案例。
- **MCP/插件**【官方】：内置 GitHub MCP server + 自定义 MCP；plugins（GitHub 仓库安装，可捆绑 MCP servers/agents/skills/hooks）；skills。
- **模型/成本**【官方】：Anthropic/OpenAI/Google 多模型选择（Claude Opus 4.6、Sonnet 4.6、GPT-5.3-Codex、Gemini 3 Pro、Haiku 4.5），/model 会话中切换；premium request 计费，模型有倍率（Opus 3x / Sonnet·Codex 1x / Haiku 0.33x）【第三方指南；官方文档有此模型权重的等价表述，未逐字核实】。
- **企业**：随 Copilot 订阅（Business/Enterprise 可用）；管理员策略（managed settings/MDM）【官方 changelog 提及】。

**一句话定位**：GitHub 系 = "**PR 优先**的委托式 agent + 终端内自主 agent"双形态；官方明示 auto-compaction、repository memory、MCP 内建；但没有自研模型（接各家前沿模型），评测也不公开。

---

### 7. Cline / Roo Code —— 开源 BYOK VS Code 扩展（同源异流）

**Cline**
- 身份【官方站点 cline.bot】：Apache-2.0 开源 agent runtime（IDE 扩展 + 桌面/终端/SDK 形态），自称 8M+ 开发者（营销口径），BYOK/BYOM 全模型（Anthropic/OpenAI/Gemini/本地 Ollama/LM Studio/任意 OpenAI 兼容端点），无订阅费。
- **循环**【官方】：Plan / Act 两态循环——Plan 态推理不改文件，Act 态执行；默认逐步审批，可开 auto-approve 全自动。
- **工具/多文件**【官方】：读改写工作区文件、终端命令、浏览器自动化（调试/测试）；coordinated multi-file changes with linter-aware fixes；每步 diff 预览。
- **检查点**【官方】：checkpoints + 一键 undo（每次 agent 编辑前快照工作区）。
- **MCP**【官方】：MCP marketplace 一键装、SDK 注册自定义工具/lifecycle hooks、插件。
- **上下文**：基本上下文窗口管理；第三方评测称长会话会按时间截断【第三方】。无云端/后台并行（本地单会话为主）【官方形态即如此】。
- **评测/企业**：无基准；无托管企业治理（这正是它的卖点——数据主权本地化）。

**Roo Code**
- 身份【第三方多来源一致】：2025 年中从 Cline fork 出的独立产品（Apache-2.0），主打"可配置性"；22K stars、SOC 2 Type 2（云组件，第三方报道）。
- **循环/模式**【第三方】：内置 Code/Debug/Architect/Ask/Orchestrator 等多模式 + **自定义模式**（YAML 定义系统提示/工具白名单/文件访问 glob/独立模型路由）——"每个模式一个人格+护栏"。
- **工具/多文件**：diff-based editing（省 token）【第三方】；浏览器自动化（可调视口/截图质量）【第三方】。
- **检查点**【第三方】：每次 agent 编辑前快照工作区、单步回滚（不碰 git）。
- **上下文**【第三方】：激进 compaction 策略（总结旧步骤、超阈值工具输出归档、仅保留活跃文件集合），长会话（200+ turn）表现优于 Cline（第三方实测）。
- **成本优化**【第三方】：prompt caching 适配器（Anthropic/OpenAI）、per-mode 模型路由（Architect 用贵模型、样板活用便宜模型）、OpenRouter compression。
- **MCP**【第三方】：支持但需手动配置（无 marketplace 一类的一站式 UI；Cline 有 marketplace）。
- **Cloud Tasks**【第三方】：可选远程 agent 运行（需 Roo 账号）。
- 官方文档（roocode.com）存在但本次未逐页抓取 → 大部分细节标注【第三方】。

**一句话定位**：开源/自托管路线的"左右两极"——Cline 保守可预测（Plan→Act），Roo 强调模式化治理与成本工程；两者均无官方评测、无托管并发编排，能力上限取决于所选模型。

---

### 8. Windsurf（Codeium → Cognition；2026-06 起 = Devin Desktop）

**身份与形态**
- 原 Codeium 的 AI-native IDE（VS Code fork），核心是 Cascade agent【官方 docs（现已重定向到 docs.devin.ai）】。
- 2025-12-04 前后 Cognition 宣布收购 Windsurf【官方宣布（X/新闻稿）+ 多家媒体一致】；价格 "~$250M" 系媒体口径（官方未披露）【第三方，数字勿当真】。
- 2026-06-02 Windsurf 品牌退役，更名 **Devin Desktop**（官方 docs 已整体切到 docs.devin.ai、页面标题即 "Devin Desktop's Cascade"【官方证据】）；社区称 Cascade 2026-07-01 EOL、Devin Local（Rust）接棒【第三方，日期待核实】。
- Google 2025-07 以 ~$24 亿"反向收购式"挖走 Windsurf 创始人团队（CNBC 报道）【第三方，与本差距分析相关性低】。

**核心能力（以官方 Cascade 文档为准）**
- **循环/模式**【官方】：Code / Chat 两模式；ReAct 式 tool calling；**每 prompt 最多 20 次 tool call** + Auto-Continue 设置；tool budget 用完可续。
- **计划**【官方】：内建 planning——后台专职 planning agent 持续精化长期计划，前台模型按计划执行短期动作；复杂任务在会话内建 Todo list（人机可共同编辑）。
- **工具/多文件**【官方】：Search / Analyze / Web Search / MCP / terminal；自动识别缺包缺工具并安装；**linter 集成（自动修复生成的代码，默认开）**；多文件编辑 + 逐文件 accept/reject。
- **检查点**【官方】：**命名快照/检查点**（会话内创建、任意导航/回退）+ 按步骤 revert 全部代码变更；revert 不可逆有警告。
- **上下文/记忆**：real-time awareness（感知用户实时动作，无需补上下文）【官方】；社区/文档另有三层配置：.windsurfrules / Memories（长期代码库约定记忆）/ AGENTS.md【第三方+官方文档体系】。
- **并行**：Wave 13（2025-12）git worktrees 并行多 agent【第三方，多来源一致】。
- **MCP**【官方】：原生 MCP（stdio / Streamable HTTP / SSE / OAuth）；100-tool 上限；第三方称是主流 IDE 中最完整的 MCP 面（marketplace、OAuth、per-tool toggles）【第三方】。
- **模型**【第三方】：自研 SWE-1.5/1.6（Codeium 训练，"13x faster"为营销）；BYOK 可选 Claude/GPT/Gemini/DeepSeek/Grok/本地 Ollama（本地模型下 Cascade 工具使用受限）；adaptive model router（按任务路由模型）。SWE-bench 分数（35.5%/自报 77.8% 之类）为第三方且互相矛盾【传闻】。
- **成本**【第三方】：免费档/Pro $15–20/月/Teams/企业；ACU（Agent Compute Units）计量；免费额度 2026 初收紧（500→200 actions/月）；定价细节多变。
- **企业**【第三方】：SSO、audit logs、FedRAMP/HIPAA/ITAR 合规（收购前 Codeium 既有认证）；on-prem/VPC。
- **盲区提示**：Windsurf 是本清单中"官方 vs 第三方信息断层最大"的产品（品牌刚完成迁移，文档/页面/定价剧烈变动中）。

**一句话定位**：被 Cognition 整合进 Devin 产品族的 IDE（Cascade agent + 计划 agent + 命名检查点 + 深 MCP）；2026 年品牌与功能处于迁移动荡期，作差距分析时建议按 "Devin Desktop + Devin Local + Devin Cloud" 的新产品结构重新核实。

---

## 二、综合提炼：『成熟上线 Agent 能力维度清单』

> 用途：作为自研 C# agent 框架的差距分析基准表。每个维度给出**成熟产品普遍具备**的水平（"基线"），可逐条对照自家实现。共 14 个维度。

1. **Agent 核心循环（计划-执行-验证）**
   基线：成熟的 plan→execute→(test/lint/verify)→iterate 自主循环；agent 能跨多轮保持任务状态与目标；不满足即自我修复（跑测试失败→读错误→改→重跑）；长任务（数百 tool call）不跑飞不丢目标。代表：Claude Code、Devin、Copilot CLI。

2. **工具调用与文件编辑（多文件）**
   基线：结构化文件编辑（非整文件重写）、一次任务内协调修改多个文件、diff 级应用、linter/编译器错误反馈回路、支持并行/乐观执行多个工具动作；对代码库的检索（grep/语义/符号级）是标配。代表：Claude Code Edit、Cursor、Copilot CLI、Cascade。

3. **执行沙箱与安全隔离**
   基线：默认隔离执行（本地进程沙箱 或 Docker/VM），文件系统与网络权限可配置、命令/路径级 allow/deny、危险操作（rm 等）额外拦截、可禁用沙箱或提升权限但有提示。代表：Claude Code（最深）、Cursor sandboxed terminals、OpenHands（容器沙箱）、Copilot CLI、Devin（云端工作区）。

4. **检查点与回滚**
   基线：自动在修改前建立代码状态快照，支持一键回退到任意先前状态（代码/会话可分开回退），建议与 VCS 配合；回滚在超长任务中可信。代表：Claude Code checkpoints、Copilot CLI Esc-Esc rewind、Cascade named snapshots、Cline/Roo checkpoints。

5. **会话恢复与续跑**
   基线：会话可中断/断电后恢复（resume/continue），长任务可脱离交互跑并在之后 attach；恢复后上下文（文件读取记录、任务状态）不丢失。代表：Claude Code `-p --resume`/`claude attach`、Copilot `/resume`、Cloud agents 异步续跑。

6. **计划模式与审批流（human-in-the-loop）**
   基线：显式 Plan/Act 分离（或权限模式分级：默认询问 / 自动接受编辑 / 计划先行 / 全自动），用户可评审计划与 diff 后批准；也支持全自动模式 + 事后审查（PR）；审批粒度可配置（逐动作/按工具/按文件）。代表：Claude Code permission modes、Cursor Plan Mode/Yolo、Copilot CLI Plan/Autopilot、Cline Plan-Act、Jules 计划审批。

7. **并行与后台任务**
   基线：可并行多个 agent/子任务（subagent fan-out、后台任务不阻塞主循环、git worktree 或多环境隔离避免文件冲突）；云端/远端后台执行 + 通知。成熟上限：数十–数百并行（Claude Code dynamic workflows、Cursor 8 路）。代表：Claude Code、Cursor、Devin（多会话/automations）、Copilot（多 agent 并行）、Jules（并发配额 3/15/60）。

8. **上下文与记忆管理**
   基线：长上下文自动管理（接近上限时压缩/摘要、压缩可配置或可阻断）；会话内上下文可见性工具（占用量、成本）；项目级指令文件（CLAUDE.md / AGENTS.md / .cursorrules）成为事实标准；跨会话持久记忆（约定/偏好/知识库）在头部产品已出现但形态各异。代表：Claude Code auto-compact+CLAUDE.md、Copilot CLI auto-compaction+repository memory、Devin Knowledge、Windsurf Memories。

9. **MCP 与扩展生态**
   基线：作为 MCP client 接入外部工具/数据源是标配；扩展机制除 MCP 外还有插件/技能/skills/hooks/SDK（生命周期钩子可拦截工具执行）；服务器市场/一键安装普及。代表：全部主要产品均声明 MCP；Claude Code hooks、Cursor MCP Apps、Copilot plugins、Cline marketplace。

10. **评测与基准**
    基线：**注意——成熟度并不等于有公开分数**。行业事实：只有开源平台（OpenHands SWE-bench Verified 跑分）与少数厂商内部集有可查数字；闭源头部产品官方不发布可比分数或只发内部集相对提升；第三方 SWE-bench 数字互相矛盾（差 15–20 分常见），vendor 自报有污染风险。差距分析不应以"分数"作主要维度，应以能力机制对照为准。

11. **企业/团队集成与治理**
    基线：IDE/终端/聊天工具多处入口（VS Code、Slack、Teams、GitHub PR/issue）；企业版具备 SSO、RBAC、审计日志、策略下发（managed settings）、用量/花费 API、私有化或 VPC/on-prem 选项、数据不训练承诺。代表：Devin（最完整）、Cursor、Claude Code、Copilot（GitHub 原生治理）、OpenHands Cloud。

12. **成本控制**
    基线：用量可见性（会话级成本/上下文成本）；配额与预算上限（usage credits、spend limit、额外预算开关）；模型路由/分层（贵模型干重活、便宜模型跑批量）与 effort 控制；提示缓存优化降本；按用量（token/credit/任务/ACU）分层定价是普遍商业模式。代表：Claude Code /cost+/usage、Copilot premium request 倍率、Devin ACU、Jules 任务配额、Roo per-mode 路由。

13. **限流与容错**
    基线：API 429/超时的指数退避重试、长时间卡死检测（stalled/timeout 告警）、后台会话崩溃可恢复、网络抖动下 MCP/工具调用超时隔离；厂商对"长跑可靠性"有持续投入证据（changelog 级）。代表：Claude Code（文档最细）、Cursor 99.9% 云端宣称、Devin 长会话专项优化。*注意：长任务质量衰减是公开承认的现实（Devin 官方建议 <10 ACU/会话）。*

14. **多环境与远程编排**
    基线：本地/远端/云端多执行目标；云端会话可从终端/桌面/浏览器/手机接管（remote control）；worktree 隔离并行；会话可在多机器间迁移。代表：Claude Code Remote Control + cloud sessions、Cursor Agents Window 四类环境、Devin 纯云端、OpenHands 本地/云/自托管三形态。

---

## 三、调研盲区与无法验证项（诚实声明）

**产品级盲区**
1. **Cursor 2026 年 3.5+ 功能细节**：官方 changelog 只核实到 3.0（2026-04-02）。社区所称 3.5（2026-05-20）Cloud Agents 获得完整桌面/浏览器/computer-use 能力、视频演示产出等【第三方】未在官方页面核实；Cursor 2.0 官方 changelog 确实有"Cloud Agents 99.9% 可靠性、云端运行"表述，可作为部分佐证，但 computer-use 级能力状态存疑。
2. **Cursor 自研模型**：Composer 2.5 的架构/性能/定价（"Moonshot Kimi K2.5 基座""10x 效率"）来自 X 帖与社区博客【传闻】；Cursor 内部 ARR 数字（$500M–$2B）互相矛盾【传闻】。官方 Composer 博客存在但未深挖。
3. **Windsurf/Devin Desktop**：官方文档已切至 docs.devin.ai（证明品牌合并属实），但 Cascade EOL 日期（2026-07-01）、Devin Local（Rust）能力、SWE-1.6 细节、定价结构全部为第三方描述，且多来源数字冲突（免费额度 200 vs 500、价格 $15 vs $20）。收购价 ~$250M 为媒体口径，官方未披露。
4. **OpenHands 1.0**：多个独立博客一致报道（生产级沙箱/安全策略/资源限制/插件系统，SWE-bench ~68%+），但本次未直接核实 GitHub release 页与其发布日期；"77.6% #1 leaderboard"系特定快照/配置（tekai 评估为 vendor 口径），且用 Claude 打底时分数并不代表框架本身。OpenHands 的 CLI 会话 resume、MCP 细节未逐页核实。
5. **Devin**：底层模型组合（多模型路由细节）、内部评测集（Junior Developer Evals）不公开；"New Devin"的完整功能边界（release notes 注明 beta 期不支持 knowledge 建议/cloud IDE/macros）随时间变化。
6. **Cline/Roo Code**：能力细节主要来自官方营销页（Cline）+ 第三方深度评测（Roo）；Roo 官方文档（roocode.com）未逐页抓取；SOC 2 声明、22K stars、Cloud Tasks 为第三方报道。两者活跃版本能力以 GitHub 仓库为准会更准。
7. **Jules**：无任何公开基准分；执行环境细节（VM 规格、依赖缓存机制）透明度低；MCP 支持情况信息不足（官方页面未见，不能断言"无"，只能说"未证实有"）。
8. **GitHub Copilot**：IDE agent mode 与 CLI/后台 coding agent 三者边界与功能差异大，本文合述但每一层能力以对应官方 changelog 条目为准；premium request 模型倍率的具体数值来自第三方指南（官方只确认计费单位）。
9. **Claude Code 具体 SWE-bench 分数**（~80.9% 等）未找到官方第一手页面，仅第三方转述；Anthropic 官方只发内部集相对提升。不要引用具体第三方分数做结论。

**方法论盲区（适用于全部）**
- 所有"官方"信息 = 厂商自述，未独立复现；swift 迭代意味着 2026-09 之后的 changelog 会立即让本文过期（Claude Code changelog 本次已看到 2.1.261 / 2026-09-04）。
- 社区传闻（X、个人博客、聚合站）密度极高且互相抄袭，本文已尽力用"官方 URL 是否在手"作为分界线，但【第三方】与【传闻】之间仍有灰区。
- 未覆盖但相关的邻近产品（值得后续补充）：OpenAI Codex（CLI/云，2025-2026 扩张极快）、Aider、GitHub Copilot Workspace、Factory、Augment Code、Kiro、Amazon Kiro、Cursor 之外的中国系（通义/豆包/CodeBuddy）等——不在本次任务范围内。

---

*报告结束。生成工具：Hermes 调研（web_search/web_extract，官方文档优先）；信息可信度分三级：官方 / 第三方 / 传闻。*
