# AgentFramework

基于微软MAF (Microsoft Agent Framework) 和 WebReaper 的企业级智能Agent框架。

## 项目概述

AgentFramework 是一个模块化的、可扩展的智能Agent框架，集成了：
- **微软MAF框架**: 作为核心Agent宿主，提供标准化的Agent生命周期管理
- **WebReaper**: 作为内置网络搜索服务，提供实时信息检索能力

## 核心特性

### 🎯 智能任务处理
- **任务拆分**: 自动将复杂任务拆分为可管理的子任务
- **SubAgent池**: 支持多Agent并行处理，提高效率
- **任务边界评估**: 精确控制子任务的输入、输出和资源限制

### 🧠 记忆系统
- **长期记忆**: 持久化存储模板、示例、模式
- **短期记忆**: 会话级临时数据
- **智能摘要**: 自动压缩上下文，减少Token消耗
- **多数据源上下文注入**: Memory + Session + Web + UserTendency 自动组装

### 📋 模板系统
- **模板存储**: 正确用例、错误用例、模式定义
- **数据召回**: 基于关键词和时间的数据检索
- **趋势分析**: 分析用户偏好，个性化响应

### 🔍 搜索集成
- **WebReaper集成**: 实时网络搜索
- **内容提取**: 智能解析搜索结果
- **缓存管理**: 避免重复搜索

### 🔄 会话循环
- **状态管理**: 完整的会话生命周期
- **用户确认**: 关键操作需要用户参与
- **权限控制**: 细粒度的权限管理

## 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/your-org/AgentFramework.git
cd AgentFramework

# 恢复依赖
dotnet restore

# 构建
dotnet build
```

### 基本使用

```csharp
using AgentFramework;
using AgentFramework.Core;
using AgentFramework.Memory;
using AgentFramework.Search;

// 创建服务容器
var services = new ServiceCollection();
services.AddAgentFramework();
var provider = services.BuildServiceProvider();

// 获取Agent实例
var agent = provider.GetRequiredService<IAgent>();

// 初始化Agent
await agent.InitializeAsync(new AgentContext
{
    SessionId = Guid.NewGuid().ToString(),
    UserId = "user_001",
    TokenBudget = 100000
});

// 发送消息
var response = await agent.ProcessAsync(new Message
{
    Content = "帮我创建一个简单的计算器类",
    Role = MessageRole.User
});

Console.WriteLine(response.Content);
```

### Web搜索示例

```csharp
var searchService = provider.GetRequiredService<ISearchService>();

var results = await searchService.SearchAsync(
    "C# async best practices",
    new SearchOptions { MaxResults = 5 }
);

foreach (var result in results)
{
    Console.WriteLine($"{result.Title}: {result.Snippet}");
}
```

### 使用模板

```csharp
var templateStore = provider.GetRequiredService<ITemplateStore>();

// 查询模板
var templates = await templateStore.QueryAsync(new TemplateQuery
{
    Category = "DSL",
    Pattern = "parser"
});

// 使用模板生成代码
var template = templates.First();
var generated = await templateStore.ApplyTemplateAsync(template, context);
```

### 上下文注入示例

```csharp
// 创建带上下文注入的 Agent
var agent = provider.GetRequiredService<IndustrialAgentV2>();

// 用户提问 - Agent 自动从多数据源召回上下文
var response = await agent.ProcessAsync(new Message
{
    Content = "帮我修改上次写的代码",
    SessionId = sessionId
});

// Agent 会自动：
// 1. 识别意图 (code_modification)
// 2. 召回 Memory/Session 中的相关代码
// 3. 组装 Prompt 并调用 LLM
// 4. 返回上下文感知的回答
```

## 项目结构

```
AgentFramework/
├── src/
│   └── AgentFramework/
│       ├── Core/           # 核心接口和基类
│       ├── Memory/         # 记忆系统
│       ├── Templates/      # 模板系统
│       ├── Search/         # 搜索服务
│       ├── SubAgent/       # 子Agent管理
│       ├── Session/        # 会话管理
│       ├── UserInteraction/# 用户交互
│       ├── Pipeline/       # 任务管道
│       ├── TokenCompression/  # Token压缩
│       ├── DataStore/      # 数据存储
│       ├── KeywordAnnotation/  # 关键词标注
│       ├── Tendency/       # 趋势分析
│       └── MAF/            # MAF集成
├── tests/
│   └── AgentFramework.Tests/
├── examples/
│   ├── basic/
│   ├── advanced/
│   └── web-search/
└── docs/
```

## 配置

### appsettings.json

```json
{
  "Agent": {
    "Name": "MainAgent",
    "MaxSubAgents": 4,
    "EnableMAF": false,
    "EnableSearchCache": true,
    "SummarizeAfterTurns": 10
  },
  "OpenAI": {
    "ApiKey": "${OPENAI_API_KEY}",
    "Model": "gpt-4"
  },
  "Storage": {
    "Path": "./data"
  }
}
```

## 文档

- [架构文档](docs/ARCHITECTURE.md) - 详细系统架构
- [API文档](docs/API.md) - 接口和类参考
- [故障排除](docs/TROUBLESHOOTING.md) - 常见问题

## 开发

### 构建

```bash
# Debug构建
./scripts/build.ps1 -Configuration Debug

# Release构建
./scripts/build.ps1 -Configuration Release
```

### 测试

```bash
# 运行所有测试
./scripts/test.ps1

# 运行特定测试
dotnet test --filter "FullyQualifiedName~MemoryTests"
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

- GitHub Issues: [链接]
- 邮箱: support@agentframework.dev
