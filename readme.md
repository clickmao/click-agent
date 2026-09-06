# click-agent (v0.10.0)

基于微软 MAF (Microsoft Agent Framework) 与 WebReaper 的 C# 智能体框架 — 全场景覆盖, 100% 托管代码。net10.0 / NativeAOT 零警告 / 351 项测试全绿。
版本口径: v0.10.x — 本轮: Yamlify YAML 解析 / Token 统计与余额联动切模 / Skill 语义匹配 (bge) / 统一输出收口。

## 语言切换 | Language Switch

[🇨🇳 中文](#中文版本) | [🇺🇸 English](#english-version)

---

## 中文版本 | Chinese Version

### 🆕 v0.10.0 新增能力
- **Yamlify YAML 解析**: 换用 SourceGenerator 级库 (零反射, NativeAOT 实测零警告), YAML 1.2 全规范; `MiniYaml.Parse` API 兼容不变
- **Token 使用统计 + 余额联动**: 初始化真实 API 同步 → 本地累计 → 阈值再同步; 余额不足自动切换其他模型 + `model:xxx flags:余额不足` 前端提示; `/token stats` 全 JSON 统计
- **Skill 语义匹配 (bge)**: 词面未命中 → 384 维语义余弦疑似判定, 嵌入器不可用自动回退
- **官方端点可配置代理**: `models.yaml proxy` 段, 留空直连
- **统一输出收口**: 全部输出 (日志/审批/前端指令/步骤状态) 走 IOutputSink 统一底层接口, 库内零 Console 直写
- **/forecast 指令**: 下轮预估机制前端可见化
- **/model list 序号选择**: 序号 1-N, `/model 3` ≡ `/model <id>`; auto/manual 双模式指令切换

### 🧭 系统能力全景 (v0.10.0)

**推理与任务**
- 意图分析与子任务拆解: 19 个中英连接词切分, Sequential/Parallel/DependsOnOutput 关系标注
- TaskPlan 依赖拓扑执行: 分层并发 (Task.WhenAll + MaxParallelism)、节点级重试 (指数退避+瞬态分类)、敏感意图 (文件/git) PausedForApproval 审批暂停
- 隔离任务: 无关提问 → 独立子 agent 执行 (独立会话/不污染主记忆), 完成即销毁
- 敏感意图审批: 文件操作/git 操作默认 PausedForApproval, 全计划暂停等审批

**模型调度 (agent.modelqueue)**
- 三通道混合调度: 本地 (LocalLlamaCaller 实跑) > 官方 (硬编码+内存态 key) > 远端 API
- 模型目录: 18 模型 (OpenAI/Anthropic/Google/xAI/DeepSeek/智谱/Qwen/Moonshot), 意图×token 预估×费用综合选模
- auto/manual 双模式: `/model list` 序号 1-N 选择; 连续失败自动切换
- Token 统计+余额联动: 初始化 API 同步→本地累计→阈值再同步; 不足切模+`flags:余额不足`
- 官方端点可配置代理 (models.yaml proxy 段)

**Skill 调度 (agent.skills)**
- SKILL.md 目录包 (Anthropic Agent-Skills Open Standard) + legacy yaml 双格式
- 四级触发: 关键词→正则→领域词→bge 语义 (cos≥0.45), 疑似即激活
- 生命周期状态机 (LRU/脱域卸载/熔断) + 沙箱上下文 + 超时/幂等重试

**上下文与记忆 (agent.contextgradient)**
- 梯度压缩: L0 原文/L1 轻摘/L2 索引/L3 归档; P0-P3 锚点 (P0 永不压缩)
- 主题域聚类 + 三重漂移校验 (不过即回滚, 版本链 10 版) + 跨进程持久化
- 会话记忆滚动 + GoalProfile + AgentProfile 动态学习 + 下轮预估落盘

**配置与输出**
- 四层 YAML 分层配置 (base/env/modules/runtime): 深合并、@dynamic 热更新、启动强校验
- YAML 解析: Yamlify (SourceGenerator 级, 零反射, AOT 零警告)
- 统一输出: IOutputSink 全出口收口 (日志/审批/前端指令/步骤状态), 库内零 Console 直写
- 日志四通道开关 + thinking 分片流 (`@chatbox:` JSON 协议行)

**工程化**
- agent.io 协议库 (netstandard2.1 零依赖): 单行事件 + @stream 流式块读写
- 会话中断恢复: ExecutionCheckpoint 原子落盘, 重启复原执行进度
- NativeAOT: 全链路 0 IL 警告, 12MB 单文件 ELF
- 能力插件接口: ICapabilityPlugin (工作区/测试/审查由开发者实现)

### 🚀 v0.9.0 能力总览 (需求1-6)
- **三通道模型调度**: 本地模型 > 官方通道 > 远端 API, 优先级恒定; 通道并发数托管; 子任务按 并发余量×推理能力×推理速度×价格 综合选模; 官方模型硬编码 (不进 yaml), key 仅 CLI `--official-key` / `/official-key` 注入 (内存态)
- **agent.io 协议库**: netstandard2.1 零依赖; 单行事件 (文本/chatbox 指令/JSON) + `@stream` 多行流式块双态读写, 前端 `Console.ReadLine()` 逐行即可解析
- **会话中断恢复**: 任务步骤检查点 (原子落盘) — 意外中断后启动直接复原执行进度
- **公开配置读写**: ConfigWriter (dot-path / L3 深合并 / L4 runtime), 与 ConfigSnapshot 读写分离
- **能力插件接口**: ICapabilityPlugin — 工作区管理/测试集成/代码审查由开发者实现注册 (框架定契约, 参考 [能力增强计划](docs/industrial_enhancements.md))

### 💬 智能问询
- 18 类问询数据类型枚举 + 纯规则校验 (数字/日期/选单/路径…)
- 批量问询: 按组一次问全, 不一条一条打断
- 子任务置信度 + 证据补充 + 最大疑问数限制
- 问询偏好库: 记录**偏好模式** (非凭据/非原值) 跨会话复用

### 🎨 双模式输出
- Markdown / 纯文本双模式, Spectre.Console 控制台着色美化
- 一切返回内容 (回答/问询/日志/审批) 统一底层结构化格式
- agent 间问询静默模式 (用户界面零打扰)

### 🎯 意图分析与子任务拆解
- **IntentDecomposer**: 复合句按连接词切分为子任务序列，四级关系标注——`Sequential`（然后/接着，保执行序）、`Parallel`（同时/以及，同层并行）、`DependsOnOutput`（基于/根据，数据依赖）；依赖词本身就是切分点，句中误切由边界保护拦截
- **19 个中英连接词**，英文按词边界匹配（`and` 不切 `android`），单字连接词前后贴非汉字才切（\"再次检查\"不误切）

### 📋 任务计划图 (TaskPlan)
- `TaskPlanBuilder` 将子任务拆解为依赖拓扑图（Level 分层 + ParallelGroup 并行组）
- **UI JSON 契约**：节点含 `Text/Intent/DependsOn/Level/ParallelGroup/Parameters/Clarifications/IsExecutable`，source-gen 序列化（AOT 安全），可直接供外部 UI 绘制
- 敏感意图（文件操作/git 操作）默认 `PausedForApproval`，全计划暂停等审批
- 参数缺失生成 `Clarification` 问询节点，**参数无关节点不联动阻塞**

### 🔌 问询协议
- `IUserPromptService` 统一问询：凭据请求（`CredentialRequestKind`）、审批请求、参数澄清
- `AnswerAuthority` 权威分级：普通参数主 Agent 可代答，敏感操作必须真实用户（`RealUserOnly`）
- 非交互环境（管道/CI）自动降级，诚实跳过不伪造

### 🛠 本地强制指令 (非 LLM)
- `LocalCommandRouter` 在意图识别前拦截：`/stop` `/continue` `/pause` `/status` `/reset`，零 token 消耗

### 📦 持久化身份与下轮预估
- `AgentRegistry`：主/子 Agent 持久化 UID + 从属关系，跨进程复用
- `NextTurnForecast`：任务循环完成后生成下轮预估落盘，关闭程序后下次对话读回，指示 LLM 用户输入倾向；按 Agent UID 隔离存储

### 🧩 返回后处理区段标记 (插件化)
- `ResponseSegmenter` 快速标记 LLM 返回内容中的 fenced 区段（```html → UI 消费，代码块 → 审查服务等）
- 路由规则插件化，`IResponseSegmentPlugin` 注册即用，不写死

### 🧠 记忆与上下文
- 多数据源上下文注入：Memory + Session + Web + UserTendency 自动组装
- 关键词召回算法经性能治理：10k 消息下 `GetRecentMessages` **5424µs → 256µs (21.2x)**，语义等价逐条验证
- 会话历史 Trim 上限治理，无界增长清剿

### 🔍 搜索集成 (主备槽)
- 内置多搜索源插件 + 主备故障转移（3 败熔断 2 分钟，槽序持久化 `search_slots.json` 复用）
- WebReaper 11.3.1 库直引，搜索结果全文增强

### 🦙 本地推理
- LLamaSharp 0.27.0 + Backend.CPU 内置，`LocalLlamaCaller : ILLMCaller` 云端失败兜底；Vulkan loader 与 Silk.NET 统一
- 模型文件缺失时诚实报错，不伪造回复

## 快速开始

```bash
git clone https://github.com/clickmao/click-agent.git
cd click-agent
dotnet restore
dotnet build
```

### CLI 使用

```bash
cd src/agent.host

# 交互 REPL（步骤明细 + /status 状态查询 + markdown 渲染）
dotnet run

# 单条模式
dotnet run -- -q "先搜索AOT资料，然后写总结文档"

# 输出日志保存为 markdown 文件
dotnet run -- --log run.md -q "你的任务"
```

CLI 内置命令：`/status`（当前状态/步骤明细/下轮预估）、`/reset`、`/exit`；每轮执行显示 `[01] 意图分析 → [02] 子任务 → [03] 管线 → [04] 区段标记` 步骤链。

### 代码使用

```csharp
using Microsoft.Extensions.DependencyInjection;
using agent;            // IndustrialAgentV2 / AgentContext
using agent.core;       // Message / MessageRole

var services = new ServiceCollection();
services.AddAgentFramework(o =>
{
    o.DataStoragePath = "./data";
    o.MaxSubAgents = 4;
});
await using var provider = services.BuildServiceProvider();

var agent = provider.GetRequiredService<IAgent>();
var ctx = new AgentContext(provider) { SessionId = "s1", UserId = "u1" };
await agent.InitializeAsync(ctx);

var reply = await agent.ProcessAsync(new Message
{
    Role = MessageRole.User,
    Content = "先搜索 .NET 10 新特性，然后基于结果写总结",
    SessionId = "s1"
}, CancellationToken.None);
Console.WriteLine(reply.Content);
```

### 模板查询

```csharp
using agent.templates;

var templates = provider.GetRequiredService<ITemplateStore>();
var found = await templates.QueryAsync(new TemplateQuery { Category = "DSL" });
```

## 项目结构

```
click-agent/
├── agent.sln
├── src/
│   ├── agent/               # 核心：意图拆解/任务计划/注册表/区段路由/本地推理
│   ├── agent.core/          # 基础契约：Message/AgentContext/IAgent
│   ├── agent.config/        # 四层 YAML 分层配置：ConfigSnapshot/ConfigWriter/MiniYaml (Yamlify 门面)
│   ├── agent.modelqueue/    # 模型队列：Router/Catalog/ChannelScheduler/BalanceQuery/TokenUsage
│   ├── agent.skills/        # Skill 调度：Registry/TriggerMatcher (bge)/PackageLoader (SKILL.md 规范)
│   ├── agent.contextgradient/ # 梯度压缩：分层/锚点/聚类/漂移校验 + BgeEmbedder
│   ├── agent.logging/       # 日志四通道 + IChatboxSink (@chatbox: 协议行)
│   ├── agent.io/            # 协议库 (netstandard2.1)：行协议/流式块读写
│   ├── agent.output/        # 输出管道：Formatter/Spectre 渲染
│   ├── agent.host/          # CLI 宿主 (NativeAOT, IOutputSink)
│   ├── agent.codegen/       # 代码生成
│   ├── agent.recovery/      # 会话中断恢复：ExecutionCheckpoint
│   ├── agent.rag/           # RAG 召回
│   ├── agent.vectormemory/  # 向量记忆
│   ├── agent.workspace/     # 工作区
│   └── agent.tests/         # 351 项测试
└── docs/                    # 架构/API/改进记录/计划文档
```

## 验证基线

| 项 | 结果 |
|---|---|
| 编译 (--no-incremental) | 0 错误 0 警告 |
| 测试 | 351/351 Passed |
| NativeAOT (linux-x64) | 0 IL/TR 警告，12MB 单文件 |
| 端到端冒烟 | DI 全图解析 + 多轮会话断言 + `/model list` 6 模型 + `/token stats` + `/forecast` |

## 文档

- [架构文档](docs/architecture.md)
- [API 文档](docs/api.md)
- [CLI 指令说明](docs/CLI指令说明.md) — 全部指令+agent.io 行协议 (需求2)
- [改进记录](docs/improvements.md) — v7.4 → v0.10.0 每轮真实执行证据与历史计划归档
- [任务循环](docs/task_loop.md)

### 🗺 下一步开发计划 (v0.11.0)

> 历史计划 (v7.15 十节点 — 全部已落地) 已归档至 [improvements.md](docs/improvements.md); 各模块设计细节见 docs/plan_*.md。

1. **Chatbox WebSocket 宿主**: IChatboxSink 协议行已就绪 (`@chatbox:` JSON), 补真实 WebSocket 传输实现与前端面板对接 (当前仅 Console 落地)
2. **余额阈值切模 E2E**: TokenUsageService 余额联动逻辑已测试覆盖, 需真实 API key 环境跑通端到端切模与 `flags:余额不足` 前端提示
3. **Skill 执行型脚本调度**: SKILL.md 包 `scripts/` 目录执行体接入 SkillExecutor (解析/沙箱/超时已有, 缺脚本进程调度)
4. **上下文压缩 P3 向量化**: L1 轻摘/聚类接 BgeEmbedder 真向量 (P1 规则版已落地, bge 已接入 Skill 语义匹配)
5. **模型目录 verify 补全**: 全目录 6 模型真机校验 (api.openai.com 本网络 RST, 需代理环境复测)
6. **开源发布收尾** (代码已推送 @ 387bfb1): LICENSE 文件/CI 工作流/徽章/英文 README 精简版

> **v0.11.0 基线**：351/351 测试全绿 · Release 编译 0 警 0 错 · NativeAOT 0 IL 警 · agenthost 12MB ELF 真机冒烟通过。

## 配置

配置类文件**统一 YAML**（`config/` 四级分层，依据《全模块 YAML 配置开发规范》），`appsettings.json` 已弃用（迁移期兼容读取并告警）：

```
config/
├── base/            # L1 基础默认 (随版本发布, 禁止本地修改): core.yaml
├── env/             # L2 环境覆盖: development.yaml / production.yaml (AGENTFRAMEWORK_ENV 选择)
├── modules/         # L3 模块定制: 同名文件覆盖 base 同名节 (增量覆盖, 未写字段继承)
└── runtime/         # L4 动态配置: dynamic.yaml (热更新, 仅 @dynamic 项生效)
```

```yaml
# config/base/core.yaml (节选, 完整见文件)
agent:
  agent_name: MainAgent
  max_sub_agents: 4
  enable_search_cache: true
  summarize_after_turns: 10

openai:
  api_key_env: AGENT_OPENAI_KEY   # 只存环境变量名, Key 本身不落配置
  model: gpt-4
```

**覆盖优先级**：`runtime/dynamic.yaml` > `modules/{module}.yaml`（同名覆盖 base，用户钦定契约）> `env/{env}.yaml` > `base/{module}.yaml`；深合并、未定义字段自动继承低层。API Key 优先走环境变量 `AGENT_OPENAI_KEY`；未配置时走 `NullLLMCaller` 明确报错路径，不静默伪造。模块代码只调 `agent.config.ConfigSnapshot`，禁止自行读 yaml 文件。

## 依赖库 | Dependencies

### 核心依赖 | Core Dependencies
| 库名称 | 版本 | 用途 | 链接 |
|--------|------|------|------|
| **Microsoft.Extensions.*** | 10.0.8 | .NET 生态系统核心依赖 | [Microsoft.Extensions](https://docs.microsoft.com/dotnet/api/microsoft.extensions) |
| **WebReaper** | 11.3.1 | 搜索结果全文增强引擎 | [WebReaper](https://github.com/WebReaper/WebReaper) |
| **LLamaSharp** | 0.27.0 | 本地大语言模型推理 (含 bge 嵌入语义匹配) | [LLamaSharp](https://github.com/SciSharp/LLamaSharp) |
| **Silk.NET.Vulkan** | 2.23.0 | Vulkan 图形API绑定 | [Silk.NET](https://github.com/dotnet/Silk.NET) |
| **Spectre.Console** | 0.57.2 | 控制台美化与渲染 | [Spectre.Console](https://spectreconsole.net/) |
| **Yamlify** | 1.8.0 | YAML 1.2 解析/序列化 (SourceGenerator 级, 零反射, AOT 兼容) | [Yamlify](https://github.com/SwissLife-OSS/Yamlify) |

### 开发工具 | Development Tools
| 工具类型 | 工具名称 | 用途 |
|----------|----------|------|
| **构建工具** | .NET 10.0 | 主要开发与运行时环境 |
| **包管理器** | NuGet | .NET 包管理 |
| **测试框架** | xUnit | 单元测试与集成测试 |
| **代码分析** | SonarCloud | 代码质量分析 |

### 许可证 | License
MIT License - 详见 [LICENSE](LICENSE) 文件

---

## English Version

### 🆕 v0.10.0 New Capabilities
- **Yamlify YAML parsing**: SourceGenerator-level library (zero reflection, AOT verified zero warnings), full YAML 1.2; `MiniYaml.Parse` API unchanged
- **Token usage stats + balance linkage**: real-API sync -> local accumulation -> threshold re-sync; auto model switching + `model:xxx flags:balance-insufficient` hint; `/token stats`
- **Skill semantic matching (bge)**: lexical miss -> 384-dim cosine suspected match (cos>=0.45), silent fallback
- **Configurable proxy**: `models.yaml proxy` section (ConfigurePrimaryHttpMessageHandler)
- **Unified output**: IOutputSink all exits; zero direct Console writes in libraries; agent/Program.cs dead code removed
- **/forecast**: next-turn forecast surfaced to frontend
- **SKILL.md packages**: Anthropic Agent-Skills Open Standard loader (dir name = front-matter name) + 2 example packages

### 🧭 Full Capability Panorama (v0.10.0)

**Reasoning & Tasks**
- Intent analysis & sub-task decomposition: 19 CN/EN connectives, Sequential/Parallel/DependsOnOutput relations
- TaskPlan topological execution: level concurrency (Task.WhenAll + MaxParallelism), node retry (exponential backoff + transient classification), sensitive intents (file/git) PausedForApproval
- Isolated tasks: unrelated questions spawn boundary-isolated sub-agents (independent session, no main-memory pollution), destroyed on completion

**Model Scheduling (agent.modelqueue)**
- Three-channel hybrid: Local (LocalLlamaCaller real runs) > Official (hardcoded + in-memory keys) > Remote API
- Model catalog: 18 models (OpenAI/Anthropic/Google/xAI/DeepSeek/Zhipu/Qwen/Moonshot), intent x token-estimate x cost ranking
- auto/manual dual-mode: `/model list` index 1-N; auto-switch on consecutive failures
- Token stats + balance linkage: initial API sync -> local accumulation -> threshold re-sync; insufficient balance switches model + `flags:balance-insufficient`
- Configurable proxy for official endpoints (models.yaml proxy section)

**Skill Dispatch (agent.skills)**
- SKILL.md directory packages (Anthropic Agent-Skills Open Standard) + legacy yaml coexistence
- Four-level triggering: keywords -> regex -> domain words -> bge semantic (cos >= 0.45), suspected-hit activates
- Lifecycle state machine (LRU/off-domain unload/circuit breaker) + sandboxed context + timeout/idempotent retry

**Context & Memory (agent.contextgradient)**
- Gradient compression: L0 raw/L1 digest/L2 index/L3 archive; P0-P3 anchors (P0 never compressed)
- Topic clustering + triple drift verification (rollback on failure, 10-version chain) + cross-process persistence
- Rolling session memory + GoalProfile + AgentProfile dynamic learning + next-turn forecast persistence

**Config & Output**
- Four-layer YAML config (base/env/modules/runtime): deep merge, @dynamic hot-reload, startup strict validation
- YAML parsing: Yamlify (SourceGenerator-level, zero reflection, AOT zero warnings)
- Unified output: IOutputSink all exits (logs/approvals/frontend directives/step status), zero direct Console writes in libraries
- Log 4-channel switches + thinking stream chunks (`@chatbox:` JSON protocol lines)

**Engineering**
- agent.io protocol library (netstandard2.1, zero deps): single-line events + @stream blocks
- Session interruption recovery: ExecutionCheckpoint atomic persistence, restart restores progress
- NativeAOT: 0 IL warnings end-to-end, 12MB single-file ELF
- Capability plugin interface: ICapabilityPlugin (workspace/tests/review by developers)

### 🚀 v0.9.0 Capability Overview (Requirements 1-6)
- **Three-channel Model Scheduling**: Local model > Official channel > Remote API, fixed priority; Channel concurrency management; Sub-tasks selected by concurrency margin × inference capability × inference speed × price; Official models hardcoded (not in yaml), keys only injected via CLI `--official-key` / `/official-key` (in-memory)
- **agent.io Protocol Library**: netstandard2.1 zero dependency; Single-line events (text/chatbox directives/JSON) + `@stream` multi-line stream block dual-mode read/write, frontend `Console.ReadLine()` line-by-line parsing
- **Session Interruption Recovery**: Task step checkpoints (atomic disk persistence) — Direct execution progress restoration after unexpected interruption
- **Public Configuration Read/Write**: ConfigWriter (dot-path / L3 deep merge / L4 runtime), separated from ConfigSnapshot read/write
- **Capability Plugin Interface**: ICapabilityPlugin — Workspace management/test integration/code review implemented by developers (framework defines contract, see [Capability Enhancement Plan](docs/industrial_enhancements.md))

### 💬 Intelligent Inquiry
- 18 inquiry data type enumerations + pure rule validation (numbers/dates/selections/paths...)
- Batch inquiry: Ask all at once by group, not one by one
- Sub-task confidence + evidence supplementation + maximum question limit
- Inquiry preference library: Record **preference patterns** (not credentials/original values) cross-session reuse

### 🎨 Dual-mode Output
- Markdown / Plain text dual modes, Spectre.Console console color beautification
- All return content (answers/inquiries/logs/approvals) unified underlying structured format
- Inter-agent inquiry silent mode (zero user interface disturbance)

### 🎯 Intent Analysis and Sub-task Decomposition
- **IntentDecomposer**: Complex sentences split into sub-task sequences by connectors, four-level relationship annotation — `Sequential` (then/next, preserve execution order), `Parallel` (simultaneously/and, same-level parallel), `DependsOnOutput` (based on, data dependency); Connectors themselves are splitting points, sentence mis-splitting intercepted by boundary protection
- **19 Chinese-English connectors**, English word boundary matching (`and` doesn't split `android`), single-character connectors must attach to non-Chinese characters on both sides to split ("再次检查" not mis-split)

### 📋 Task Plan Diagram (TaskPlan)
- `TaskPlanBuilder` decomposes sub-tasks into dependency topology graph (Level分层 + ParallelGroup parallel groups)
- **UI JSON Contract**: Nodes contain `Text/Intent/DependsOn/Level/ParallelGroup/Parameters/Clarifications/IsExecutable`, source-gen serialized (AOT safe), directly available for external UI rendering
- Sensitive intents (file operations/git operations) default to `PausedForApproval`, full plan pause pending approval
- Parameter missing generates `Clarification` inquiry nodes, **parameter-independent nodes don't block联动**

### 🔌 Inquiry Protocol
- `IUserPromptService` unified inquiry: Credential requests (`CredentialRequestKind`), approval requests, parameter clarification
- `AnswerAuthority` authority hierarchy: Normal parameters MainAgent can answer, sensitive operations must real user (`RealUserOnly`)
- Non-interactive environments (pipe/CI) automatically degrade, honestly skip without fabrication

### 🛠 Local Mandatory Commands (non-LLM)
- `LocalCommandRouter` intercepts before intent recognition: `/stop` `/continue` `/pause` `/status` `/reset`, zero token consumption

### 📦 Persistent Identity and Next-turn Forecast
- `AgentRegistry`: Main/sub-agent persistent UID + subordination relationship, cross-process reuse
- `NextTurnForecast`: Generate next-turn forecast after task cycle completion, read back on next conversation after shutdown, indicates LLM user input tendency; isolated by Agent UID

### 🧩 Post-processing Segment Marking (pluginized)
- `ResponseSegmenter` quickly marks fenced segments in LLM return content (```html → UI consumption, code blocks → review services, etc.)
- Routing rules pluginized, `IResponseSegmentPlugin` register-to-use, not hardcoded

### 🧠 Memory and Context
- Multi-data source context injection: Memory + Session + Web + UserTendency automatic assembly
- Keyword recall algorithm performance governance: 10k messages `GetRecentMessages` **5424µs → 256µs (21.2x)**, semantic equivalent逐条验证
- Session history Trim upper limit governance, unbounded growth eradication

### 🔍 Search Integration (main backup slots)
- Built-in multi-search source plugins + main backup failover (3 failures熔断 2 minutes, slot sequence persistent `search_slots.json` reuse)
- WebReaper 11.3.1 library direct引用, search results full-text enhancement

### 🦙 Local Inference
- LLamaSharp 0.27.0 + Backend.CPU built-in, `LocalLlamaCaller : ILLMCaller` cloud failure fallback; Vulkan loader unified with Silk.NET
- Honest error reporting when model files missing, no fabricated replies

## Quick Start

```bash
git clone https://github.com/clickmao/click-agent.git
cd click-agent
dotnet restore
dotnet build
```

### CLI Usage

```bash
cd src/agent.host

# Interactive REPL (step details + /status status query + markdown rendering)
dotnet run

# Single mode
dotnet run -- -q "First search AOT materials, then write summary document"

# Output log save as markdown file
dotnet run -- --log run.md -q "your task"
```

CLI built-in commands: `/status` (current status/step details/next-turn forecast), `/reset`, `/exit`; each execution shows `[01] Intent Analysis → [02] Sub-tasks → [03] Pipeline → [04] Segment Marking` step chain.

### Code Usage

```csharp
using Microsoft.Extensions.DependencyInjection;
using agent;            // IndustrialAgentV2 / AgentContext
using agent.core;       // Message / MessageRole

var services = new ServiceCollection();
services.AddAgentFramework(o =>
{
    o.DataStoragePath = "./data";
    o.MaxSubAgents = 4;
});
await using var provider = services.BuildServiceProvider();

var agent = provider.GetRequiredService<IAgent>();
var ctx = new AgentContext(provider) { SessionId = "s1", UserId = "u1" };
await agent.InitializeAsync(ctx);

var reply = await agent.ProcessAsync(new Message
{
    Role = MessageRole.User,
    Content = "First search .NET 10 new features, then write summary based on results",
    SessionId = "s1"
}, CancellationToken.None);
Console.WriteLine(reply.Content);
```

### Template Query

```csharp
using agent.templates;

var templates = provider.GetRequiredService<ITemplateStore>();
var found = await templates.QueryAsync(new TemplateQuery { Category = "DSL" });
```

## Project Structure

```
click-agent/
├── agent.sln
├── src/
│   ├── agent/               # Core: Intent decomposition/Task planning/Registry/Segment routing/Local inference
│   ├── agent.core/          # Base contracts: Message/AgentContext/IAgent
│   ├── agent.config/        # 4-layer YAML config: ConfigSnapshot/ConfigWriter/MiniYaml (Yamlify facade)
│   ├── agent.modelqueue/    # Model queue: Router/Catalog/ChannelScheduler/BalanceQuery/TokenUsage
│   ├── agent.skills/        # Skill dispatch: Registry/TriggerMatcher (bge)/PackageLoader (SKILL.md spec)
│   ├── agent.contextgradient/ # Gradient compression: layers/anchors/clustering/drift check + BgeEmbedder
│   ├── agent.logging/       # Log 4-channels + IChatboxSink (@chatbox: protocol lines)
│   ├── agent.io/            # Protocol library (netstandard2.1): line protocol/stream blocks
│   ├── agent.output/        # Output pipeline: Formatter/Spectre rendering
│   ├── agent.host/          # CLI host (NativeAOT, IOutputSink)
│   ├── agent.codegen/       # Code generation
│   ├── agent.recovery/      # Session recovery: ExecutionCheckpoint
│   ├── agent.rag/           # RAG recall
│   ├── agent.vectormemory/  # Vector memory
│   ├── agent.workspace/     # Workspace
│   └── agent.tests/         # 351 tests
└── docs/                    # Architecture/API/improvement records/plans
```

## Validation Baseline

| Item | Result |
|---|---|
| Compilation (--no-incremental) | 0 errors 0 warnings |
| Tests | 351/351 Passed |
| NativeAOT (linux-x64) | 0 IL/TR warnings, 12MB single file |
| End-to-end smoke test | DI full graph 11/11 parsing + multi-session assertions |

## Documentation

- [Architecture Document](docs/architecture.md)
- [API Document](docs/api.md)
- [CLI Command Instructions](docs/CLI指令说明.md) — All commands + agent.io line protocol (requirement 2)
- [Improvement Records](docs/improvements.md) — v7.4 → v0.10.0 real execution evidence & plan archive
- [Task Loop](docs/task_loop.md)

### 🗺 Next Development Plan (v0.11.0)

> Historical plan (v7.15 ten nodes - all landed) archived in [improvements.md](docs/improvements.md); per-module design details in docs/plan_*.md.

1. **Chatbox panel extension (optional)**: io protocol output (`@chatbox:` lines) already covers CLI/script integration; WebSocket host only if a browser panel is needed (IChatboxSink unchanged)
2. **Balance-threshold switching E2E**: TokenUsageService balance linkage unit-tested; needs real API key end-to-end switching + `flags:balance-insufficient` frontend hint
3. **Skill executive script dispatch**: SKILL.md package `scripts/` directory execution wiring into SkillExecutor (parsing/sandbox/timeout done, script process scheduling missing)
4. **Context compression P3 vectorization**: L1 summaries/clustering onto BgeEmbedder real vectors (P1 rule version landed; bge already wired into Skill semantic matching)
5. **Model catalog verify completion**: full 6-model real-device verification (api.openai.com RST on this network, retest via proxy)
6. **Open-source release polish** (code pushed @ 387bfb1): LICENSE file/CI workflows/badges/condensed English README

> **v0.10.0 baseline**: 351/351 tests green / Release build 0 warnings 0 errors / NativeAOT 0 IL warnings / agenthost 12MB ELF device smoke passed.

## Configuration

Configuration files **unified YAML** (`config/` four-level分层, based on "Full Module YAML Configuration Development Specification"), `appsettings.json` deprecated (migration period compatible reading and warning):

```
config/
├── base/            # L1基础默认 (随版本发布,禁止本地修改): core.yaml
├── env/             # L2环境覆盖: development.yaml / production.yaml (AGENTFRAMEWORK_ENV选择)
├── modules/         # L3模块定制: 同名文件覆盖base同名节 (增量覆盖,未写字段继承)
└── runtime/         # L4动态配置: dynamic.yaml (热更新,仅 @dynamic项生效)
```

```yaml
# config/base/core.yaml (节选,完整见文件)
agent:
  agent_name: MainAgent
  max_sub_agents: 4
  enable_search_cache: true
  summarize_after_turns: 10

openai:
  api_key_env: AGENT_OPENAI_KEY   # 只存环境变量名, Key本身不落配置
  model: gpt-4
```

**Override priority**: `runtime/dynamic.yaml` > `modules/{module}.yaml` (同名覆盖base,用户钦定契约) > `env/{env}.yaml` > `base/{module}.yaml`; deep merge, undefined fields automatically inherit lower层. API Key优先走环境变量 `AGENT_OPENAI_KEY`;未配置时走 `NullLLMCaller`明确报错路径,不静默伪造.模块代码只调 `agent.config.ConfigSnapshot`,禁止自行读 yaml文件.

## License

MIT License