# click-agent (v0.11.0)

[![ci](https://github.com/clickmao/click-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/clickmao/click-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![.NET](https://img.shields.io/badge/.NET-10.0-512BD4)
![Tests](https://img.shields.io/badge/tests-355%2F355-brightgreen)
![NativeAOT](https://img.shields.io/badge/NativeAOT-zero%20warnings-blueviolet)

> CI 工作流文件已就绪 (`.github/workflows/ci.yml`), 待具有 `workflow` 权限的 token 推送后徽章生效。

基于微软 MAF (Microsoft Agent Framework) 与 WebReaper 的 C# 智能体框架 — 全场景覆盖, 100% 托管代码。net10.0 / NativeAOT 零警告 / 355 项测试全绿。
版本口径: v0.11.0 — 本轮: 统一命令协议 (@cmd) + 三传输 / Skill 执行型脚本 / 相关性向量化混合打分 / 19 模型目录。

[🇺🇸 English → README_EN.md](README_EN.md)

---

### 🆕 v0.11.0 新增能力
- **统一命令协议 (`@cmd`)**: 全部前端指令 (余额不足/思考切页/模型切换/Skill 进度) 收敛 `AgentCommand` 信封; 三种传输: Console.IO / 共享内存 (mmap 环形) / TCP Socket — 读写工具类组合任意 WriterBase/ReaderBase
- **Skill 执行型脚本**: SKILL.md `scripts/` 真进程调度 (python/bash/node), 包目录沙箱, 环境变量白名单, 超时杀树, 脚本 `@cmd` 行转发面板 (附 skill 参数)
- **相关性向量化混合打分 (P3)**: 消息相关性 = 0.6×词面 + 0.4×bge 余弦, 强语义 (≥0.8) 抬底; 嵌入器缺失纯词面回退 (P1 兼容)
- **19 模型目录**: `modules:` 数组 (name/description/request_address/api_key 环境变量名/费用与能力预估); `/model list` 逐模型展示描述
- **Yamlify YAML 解析**: 换用 SourceGenerator 级库 (零反射, NativeAOT 实测零警告), YAML 1.2 全规范; `MiniYaml.Parse` API 兼容不变
- **Token 使用统计 + 余额联动**: 初始化真实 API 同步 → 本地累计 → 阈值再同步; 余额不足自动切换其他模型 + `model:xxx flags:余额不足` 前端提示; `/token stats` 全 JSON 统计
- **Skill 语义匹配 (bge)**: 词面未命中 → 384 维语义余弦疑似判定, 嵌入器不可用自动回退
- **官方端点可配置代理**: `models.yaml proxy` 段, 留空直连
- **统一输出收口**: 全部输出 (日志/审批/前端指令/步骤状态) 走 IOutputSink 统一底层接口, 库内零 Console 直写
- **/forecast 指令**: 下轮预估机制前端可见化
- **/model list 序号选择**: 序号 1-N, `/model 3` ≡ `/model <id>`; auto/manual 双模式指令切换

### 🧭 系统能力全景 (v0.11.0)

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
| 测试 | 355/355 Passed |
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

> **v0.11.0 基线**：355/355 测试全绿 · Release 编译 0 警 0 错 · NativeAOT 0 IL 警 · agenthost 12MB ELF 真机冒烟通过。

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

模型目录 `config/base/models.yaml` — 顶层 `modules:` 数组, 每条目一个远端模型 (v0.11.0 格式):

```yaml
modules:
  - name: deepseek-chat              # 模型名 (/model <name> 引用)
    description: DeepSeek V3 对话版, 编码性价比高
    provider: deepseek
    request_address: https://api.deepseek.com/v1/chat/completions
    api_key: DEEPSEEK_KEY            # 只存环境变量名, Key 本身不落配置
    price_in_per_m: 0.27             # 费用预估: 输入 USD/每百万 token (公开牌价)
    price_out_per_m: 1.10            # 费用预估: 输出
    reasoning_score: 7               # 推理能力预估 1-10 (公开评测归一化)
    coding_score: 8                  # 编码能力预估 1-10
    context_window: 64000
    suited_for: [general, coding, summary]
```

目录内置 19 模型 (OpenAI/Anthropic/Google/xAI/DeepSeek/智谱/Qwen/Moonshot), `/model list` 全量展示, `/model verify <name>` 真机校验端点。

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
