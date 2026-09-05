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

### 🗺 开发计划 (v7.15 — 全部节点已落地)
每个开发计划独立成文（单个模块一个文档，无需加载全上下文）；无法在计划期确定的事项已在各文档内标注**待确认**留给下次开发核实。

0. ✅ **TaskPlan 体系归拢**（`d46e735`）：代码库存在两套并行任务计划体系（遗留 `agent.planner` vs 现役 `TaskPlan*`），且现役主链一条都不跑执行器（`TaskPlanExecutor` 生产零构造、仅测试调用；`TaskPlanBuilder.Build` 生产零调用；`WaitingClarification` 死状态零赋值）。本项**定案：删除遗留 `agent.planner` 项目与 V1 残留（不再评估保留）**，再把 V2 主链接入计划执行（影子模式→主路）。详见 [plan_taskplan_consolidation.md](docs/plan_taskplan_consolidation.md)。
1. ✅ **执行器同层并发化**（`45f762e`）：`TaskPlanExecutor.ExecuteAsync` 现为逐节点串行 await（源码注释自认"同层并行留给并发化迭代"）；`Level/ParallelGroup` 算法**已存在**（`ComputeLevelsAndParallelGroups`），本项只补执行端：同层并发（`Task.WhenAll` + `MaxParallelism` 上限分片）、跨层等待上游、保留全部现有失败/暂停/问询语义。详见 [plan_executor_parallel.md](docs/plan_executor_parallel.md)。
2. ✅ **节点级重试策略**（`2e6cd5d`）：单节点失败现直接 FailFast 放弃全计划（源码注释自认"重试策略后续迭代"）；补 `MaxRetries` + 指数退避 + 瞬态/永久失败分类 + 重试审计进 `TaskPlanRun`，取消永不重试。详见 [plan_node_retry.md](docs/plan_node_retry.md)。
3. ✅ **隔离任务**（`e5bbb9c`）：主 agent 任务循环中收到**与当前目标无关的新提问**（如计算器开发中突然要求"查天气"）→ 纯规则打分判定（实体重叠/指代词/意图类别，锚=`SessionMemory.GoalProfile.KeyEntities`）→ 额外开**隔离边界的子 agent** 执行（独立会话/不写主记忆/不污染主画像/静默问询），完成即销毁。详见 [plan_isolated_task.md](docs/plan_isolated_task.md)。
4. ✅ **模型队列 + Token 余额查询**（`4645c89`）：独立模块 `src/agent/modelqueue/`；本地 JSON config（`data/config/model_queue.json`）存主/次模型（key 只存环境变量名）；手动 `/model` 指定 + 自动模式（主模型连续 N 败切副模型，取消永不触发切换）+ 计价策略路由（上下文压缩等性能不敏感功能自动走便宜模型）；新增本地指令 `/balance` 查询 token 账户余额（双通道 JSON 输出，不支持的端点诚实报错）。详见 [plan_model_queue.md](docs/plan_model_queue.md)。
5. ✅ **全模块 YAML 分层配置体系**（P1, `e1f8078`）：新模块 `src/agent.config/`——`config/base|env|modules|runtime` 四级分层，**模块只调 `ConfigSnapshot.Get<T>()`，base 配置被同名 module 配置增量覆盖**（用户钦定核心契约：深合并、未定义字段继承低层）；启动强校验失败即失败、缺失兜底默认值、`@dynamic immediate/next-turn` 热更新标注；现有硬编码（EvidenceGate 疑问数、搜索熔断、源配额、模型队列参数等）收编为 6 个 base yaml；配置类 JSON 废弃转 YAML（运行时**数据**落盘仍 JSON 不动）；AOT 风险项：YamlDotNet 反射 vs NativeAOT，开发第一步先 POC，失败则启用零反射 YAML 子集解析器备选。详见 [plan_yaml_config.md](docs/plan_yaml_config.md)。
6. ✅ **Skill 调度模块**（P1, `036da83`）：新模块 `src/agent.skills/`（依据《Skill 模块技术设计文档 v1.0》）——领域级能力封装与口径管控：注册中心（skills/ 目录 yaml 定义）+ 三级触发匹配（前缀树预匹配→意图/正则/语义精匹配→上下文匹配，**疑似命中即激活**，插在 V2 推理前）+ 生命周期状态机（会话缓存/连续两轮脱域自动卸载/挂起恢复）+ 上下文隔离沙箱（白名单读/写回卷/中间数据不入历史）+ 执行调度（超时/幂等重试/熔断）+ 标准化输出（`force_use` 强制口径禁模型篡改）；失败自动降级普通推理不阻塞主链；全部阈值走第 5 项 YAML 分层配置；多 Skill 编排映射 TaskPlan 不新建执行引擎。详见 [plan_skill_dispatch.md](docs/plan_skill_dispatch.md)。
7. ✅ **日志细分通道与前端思考流协议**（`d286471`）：LogFlags 四位独立开关 {显示到控制台/显示到chatbox思考/显示到chatbox输出/记录到日志}；CLI 日志缓存 `/log dump` 存档；`thinking_page_switch` / `thinking_end` 前端 JSON 指令（思考分片推送防前端全量加载）。详见 [plan_log_channels.md](docs/plan_log_channels.md)。
8. ✅ **模型目录与意图选模**（`4645c89`）：推理/编码能力 1-10 标准值；`config/base/models.yaml` 知名模型目录（除 API-KEY 外全参数 + 余额查询方案）；"自动"按意图×token 预估×费用综合选模（重推理→全量版，轻意图→flash）；新增模型强制真实 http 校验（假 key 期望 401 = 地址合法）。详见 [plan_model_queue.md](docs/plan_model_queue.md) C.6。
9. ✅ **上下文梯度压缩与防漂移**（P1 规则版, `6efe75f`）：新模块 `src/agent.context/`（依据《上下文梯度压缩与防漂移子系统技术设计文档 v1.0》）——L0 原文/L1 轻摘/L2 结构化索引/L3 归档四层梯度（近详远略）+ P0-P3 分级锚点（P0 永不压缩，召回率强制 100%）+ 主题域增量聚类（语义×0.7+实体×0.3，每 10 轮巡检合并/拆分）+ 三重漂移校验（锚点召回/语义相似度 0.92/事实三元组）不过即回滚（版本链 10 版，连续失败降级）+ **重复确认驱动弹性校正**（四类信号→仅目标主题域提层，3/5/8 轮阶梯冷却回落）+ **跨进程持久化复用**（fragments/topics/versions/essence 落盘 `data/context/`，重启重建索引，essence 注入新会话初始锚——用户点名）；P1 规则版先行（实体 Jaccard 聚类），P3 接 bge 真向量（`/home/agentuser/models/bge-small-*.gguf`，当前 EmbeddingConfig 是空壳）；全部阈值走第 5 项 YAML 配置（规范文档 5.3 节参数表）。详见 [plan_context_compression.md](docs/plan_context_compression.md)。

> 计划总图：`docs/plans/v715_dev_plan.taskplan.json`（TaskPlan 结构 + 每节点 DocRef 标注文档，防漂移测试 `DevPlanDocRefTests` 固化）
>
> **v7.15 基线**：276/276 测试全绿 · Release 全量编译 0 警 0 错 · NativeAOT publish 0 IL 警 · 冒烟通过。
> 遗留迭代点（各计划文档 ⚠ 待确认节）：Skill P2 生命周期/执行调度、Skill P3 语义匹配、压缩 P3 向量化、chatbox 推送传输通道。

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

## 许可证

MIT License
