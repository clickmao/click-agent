# click-agent

基于微软 MAF (Microsoft Agent Framework) 与 WebReaper 的工业级 C# 智能体框架。net10.0 / NativeAOT 零警告 / 202 项测试全绿。

## 核心特性

### 💬 智能问询 (v7.13)
- 18 类问询数据类型枚举 + 纯规则校验 (数字/日期/选单/路径…)
- 批量问询: 按组一次问全, 不一条一条打断
- 子任务置信度 + 证据补充 + 最大疑问数限制
- 问询偏好库: 记录**偏好模式** (非凭据/非原值) 跨会话复用

### 🎨 双模式输出 (v7.13)
- Markdown / 纯文本双模式, Spectre.Console 控制台着色美化
- 一切返回内容 (回答/问询/日志/审批) 统一底层结构化格式
- agent 间问询静默模式 (用户界面零打扰)

### 🎯 意图分析与子任务拆解
- **IntentDecomposer**: 复合句按连接词切分为子任务序列，四级关系标注——`Sequential`（然后/接着，保执行序）、`Parallel`（同时/以及，同层并行）、`DependsOnOutput`（基于/根据，数据依赖）；依赖词本身就是切分点，句中误切由边界保护拦截
- **19 个中英连接词**，英文按词边界匹配（`and` 不切 `android`），单字连接词前后贴非汉字才切（"再次检查"不误切）

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
│   ├── agent.host/          # CLI 宿主 (NativeAOT 发布)
│   ├── agent.planner/       # 任务执行引擎
│   ├── agent.codegen/       # 代码生成
│   ├── agent.recovery/      # 故障恢复
│   ├── agent.rag/           # RAG 召回
│   ├── agent.vectormemory/  # 向量记忆
│   ├── agent.workspace/     # 工作区
│   └── agent.tests/         # 173 项测试
└── docs/                    # 架构/API/改进记录
```

## 验证基线

| 项 | 结果 |
|---|---|
| 编译 (--no-incremental) | 0 错误 0 警告 |
| 测试 | 173/173 Passed |
| NativeAOT (linux-x64) | 0 IL/TR 警告，2.9MB 单文件 |
| 端到端冒烟 | DI 全图 11/11 解析 + 多轮会话断言 |

## 文档

- [架构文档](docs/architecture.md)
- [API 文档](docs/api.md)
- [改进记录](docs/improvements.md) — v7.4 → v7.12 每轮真实执行证据
- [任务循环](docs/task_loop.md)
- [开发计划: 依赖拓扑任务图 × 隔离任务](docs/plan_taskgraph_and_isolated_task.md) — 待开发子模块，独立成文无需加载全上下文

### 🗺 下一步开发计划 (v7.15 候选)
1. **依赖拓扑任务图**：`TaskPlanBuilder` 按 `SubTask.Dependencies` 将子任务拆解为 Level 分层 + ParallelGroup 并行组 → 执行器按层执行，同层并发、跨层等待上游（Kahn 分层，环检测报错）。详见计划文档模块 A。
2. **隔离任务**：主 agent 任务循环中收到**与当前目标无关的新提问**（如计算器开发中突然要求"查天气"）→ 纯规则判定无关（实体重叠/指代词/意图类别，锚=`SessionMemory.GoalProfile.KeyEntities`）→ 额外开**隔离边界的子 agent** 执行（独立会话/不写主记忆/不污染主画像/静默问询），完成即销毁。详见计划文档模块 B。

## 配置

```json
{
  "Agent": {
    "AgentName": "MainAgent",
    "MaxSubAgents": 4,
    "EnableSearchCache": true,
    "SummarizeAfterTurns": 10
  },
  "OpenAI": {
    "ApiKey": "${OPENAI_API_KEY}",
    "Model": "gpt-4"
  }
}
```

API Key 优先走环境变量 `AGENT_OPENAI_KEY`；未配置时走 `NullLLMCaller` 明确报错路径，不静默伪造。

## 许可证

MIT License
