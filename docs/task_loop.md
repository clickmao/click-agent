# 任务循环与会话系统详解

## 概述

AgentFramework 实现了一套完整的**工业级任务循环系统**，包含：

1. **SubAgent 任务拆分**
2. **用户互动反馈点**
3. **反馈持久化到 RAG**
4. **相似问题召回**

---

## 1. 任务循环流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           任务循环完整流程                                    │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────┐
    │  用户输入  │  "帮我创建一个用户服务类，包含CRUD操作"
    └────┬─────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  阶段1: 任务规划                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  • 意图识别: code_generation                                                │
│  • 任务拆分: 分析需求 → 生成代码 → 生成测试 → 代码审查                      │
│  • 创建任务图                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
    ┌────────────┐
    │ 交互点 #1   │  ⭐ 用户确认
    │ 任务确认    │
    └────┬───────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  阶段2: SubAgent执行                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Layer 1 (并行)          Layer 2 (并行)          Layer 3 (并行)           │
│   ┌─────────┐            ┌─────────┐            ┌─────────┐              │
│   │Coder    │            │Coder    │            │Tester   │              │
│   │Agent    │───────────▶│Agent    │───────────▶│Agent    │              │
│   │生成代码  │            │生成测试 │            │审查代码 │              │
│   └─────────┘            └─────────┘            └─────────┘              │
│                                                                             │
│   @progress (25%)        @progress (50%)        @progress (75%)          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
    ┌────────────┐
    │ 交互点 #2   │  ⭐ 出错时用户确认
    │ 错误确认    │
    └────┬───────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  阶段3: 结果确认                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  • 展示执行结果                                                             │
│  • 请求用户确认                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
    ┌────────────┐
    │ 交互点 #3   │  ⭐ 用户确认结果
    │ 结果确认    │
    └────┬───────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  阶段4: 反馈持久化                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  • 存储用户选择到 FeedbackStore                                             │
│  • 索引到 RAG 向量库                                                        │
│  • 提取关键词                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
    ┌──────────────┐
    │   任务完成   │
    └──────────────┘
```

---

## 2. 交互点详解

### 2.1 交互点类型

| 类型 | 时机 | 用途 |
|------|------|------|
| `TaskConfirmation` | 任务开始前 | 确认用户意图，必要时调整 |
| `ProgressNotification` | 执行中 | 通知进度（可选） |
| `ResultConfirmation` | 任务完成后 | 确认结果或请求修改 |
| `ErrorConfirmation` | 出错时 | 用户选择重试/跳过/终止 |
| `SelectionConfirmation` | 多选项时 | 用户选择方案 |
| `SaveConfirmation` | 保存前 | 确认保存操作 |
| `AbandonConfirmation` | 放弃前 | 确认放弃操作 |

### 2.2 交互选项

```csharp
// 标准交互选项
var options = new List<InteractionOption>
{
    new() { Id = "proceed", Label = "确认开始", IsRecommended = true },
    new() { Id = "modify", Label = "修改需求" },
    new() { Id = "cancel", Label = "取消任务" }
};

// 破坏性操作需要额外确认
new() { Id = "delete", Label = "删除", IsDestructive = true }
```

---

## 3. SubAgent 任务拆分

### 3.1 任务拆分策略

```csharp
// 根据任务类型自动拆分
private List<(string Name, string Details, SubAgentType Type)> DecomposeIntoSubTasks(string task)
{
    if (task.Contains("创建") || task.Contains("生成"))
    {
        return new List<(string, string, SubAgentType)>
        {
            ("分析需求", "理解用户需求，确定代码结构", SubAgentType.Coder),
            ("生成代码", "根据需求生成代码", SubAgentType.Coder),
            ("生成测试", "为生成的代码编写测试", SubAgentType.Tester),
            ("代码审查", "审查生成的代码质量", SubAgentType.Reviewer)
        };
    }
    // ... 其他类型
}
```

### 3.2 SubAgent 类型

| 类型 | 职责 | 任务类型 |
|------|------|----------|
| `Coder` | 代码编写、修改 | CodeGeneration, CodeModification |
| `Tester` | 测试生成、验证 | Testing |
| `Reviewer` | 代码审查、问题发现 | CodeReview |
| `Researcher` | 资料收集、搜索 | Search, Research |
| `Planner` | 任务规划、分解 | Planning |

### 3.3 任务边界评估

```csharp
public class TaskBoundary
{
    // 任务输入边界
    public string Input { get; set; }
    
    // 任务输出边界
    public string ExpectedOutput { get; set; }
    
    // 资源限制
    public int MaxTokens { get; set; } = 4000;
    public TimeSpan Timeout { get; set; } = TimeSpan.FromMinutes(5);
    
    // 依赖关系
    public List<string> DependsOn { get; set; }
    
    // 任务评估
    public TaskComplexity Complexity { get; set; }
}

public enum TaskComplexity
{
    Trivial,    // < 5分钟
    Simple,     // 5-15分钟
    Medium,     // 15-30分钟
    Complex,    // 30-60分钟
    Epic        // > 60分钟
}
```

---

## 4. 反馈持久化到 RAG

### 4.1 反馈数据结构

```csharp
public class UserFeedback
{
    public string Id { get; set; }
    public string SessionId { get; set; }      // 会话ID
    public string TaskId { get; set; }          // 任务ID
    public string InteractionId { get; set; }   // 交互ID
    
    // 用户选择
    public string SelectedOptionId { get; set; }
    public string SelectedOptionLabel { get; set; }
    public string? UserComment { get; set; }    // 用户评论
    
    // 上下文
    public string Context { get; set; }         // 任务上下文
    public string TaskDescription { get; set; } // 任务描述
    
    // 结果
    public string? Outcome { get; set; }        // 最终结果
    public double? Satisfaction { get; set; }   // 满意度
    
    // 关键词（用于召回）
    public List<string> Keywords { get; set; }
}
```

### 4.2 RAG 索引流程

```
用户反馈
    │
    ▼
┌─────────────────┐
│ FeedbackPersistence │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  FeedbackStore  │     │   RAGRecall     │
│  (原始数据)      │     │  (向量索引)      │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  相似问题召回    │
                        └─────────────────┘
```

### 4.3 相似问题召回

```csharp
// 用户问类似问题
var query = "如何创建用户服务类？";

// 召回相似历史
var results = await ragRecall.RecallAsync(new RecallRequest
{
    Query = query,
    DocumentType = "user_feedback",
    TopK = 5
});

// 结果示例:
// 1. "帮我创建一个用户服务类" - 0.95分 - 选择: "确认开始"
// 2. "创建一个订单服务类" - 0.72分 - 选择: "修改需求"
// ...
```

---

## 5. 会话状态管理

### 5.1 会话状态机

```
     ┌─────────────────────────────────────────────────────────────┐
     │                                                             │
     ▼                                                             │
┌─────────┐    start    ┌─────────────┐    ┌──────────────┐      │
│  Idle   │───────────▶│   Active    │───▶│   Waiting    │      │
└─────────┘            └──────┬──────┘    │   (等待用户)   │      │
     ▲                        │            └──────────────┘      │
     │                        │                                  │
     │                        │ completed                       │
     │                        ▼                                  │
     │                 ┌─────────────┐                           │
     │                 │   Done     │                           │
     │                 └─────────────┘                           │
     │                        │                                  │
     │                        │ abort                            │
     │                        ▼                                  │
     │                 ┌─────────────┐                           │
     └─────────────────│  Aborted   │                           │
                       └─────────────┘                           │
                                                             │
     end ◀────────────────────────────────────────────────────┘
```

### 5.2 会话数据流

```csharp
public class Session
{
    public string Id { get; set; }
    public SessionState State { get; set; }
    
    // 当前任务
    public string? CurrentTaskId { get; set; }
    public string? CurrentPlanId { get; set; }
    
    // 任务历史
    public List<string> CompletedTaskIds { get; set; }
    public List<string> PendingInteractionIds { get; set; }
    
    // 上下文
    public Dictionary<string, object> Context { get; set; }
    
    // 统计
    public DateTime CreatedAt { get; set; }
    public DateTime? LastActivityAt { get; set; }
    public int TotalInteractions { get; set; }
}
```

---

## 6. 完整使用示例

```csharp
// 创建执行引擎
var engine = new TaskExecutionEngine(
    logger,
    interactionManager,
    feedbackStore,
    subAgentPool,
    recoverySystem,
    workspace
);

// 定义选项
var options = new ExecutionOptions
{
    RequireConfirmation = true,
    AutoSaveToRAG = true,
    MaxParallelAgents = 4,
    RequiredInteractionPoints = new()
    {
        InteractionPointType.TaskConfirmation,
        InteractionPointType.ResultConfirmation,
        InteractionPointType.ErrorConfirmation
    }
};

// 执行任务（带进度回调）
var result = await engine.ExecuteAsync(
    "帮我创建一个用户服务类，包含CRUD操作",
    options,
    progress => Console.WriteLine($"[{progress.PercentComplete:F0}%] {progress.Status}"),
    cancellationToken
);

// 输出:
// [0%] 正在分析任务...
// [0%] 任务确认: 帮我创建一个用户服务类，包含CRUD操作
//         选项: [确认开始] [修改需求] [取消任务]
// [25%] 执行层级 1/3...
// [50%] 执行层级 2/3...
// [75%] 执行层级 3/3...
// [100%] 任务完成，确认结果
```

---

## 7. 下次相似问题的处理

```csharp
// 当用户再次问类似问题时

public async Task<Response> HandleQueryAsync(string query)
{
    // 1. RAG 召回相似历史
    var similarFeedbacks = await feedbackPersistence.QuerySimilarAsync(query, topK: 3);
    
    // 2. 检查是否有相关反馈
    if (similarFeedbacks.Any())
    {
        // 3. 构建上下文提示
        var context = similarFeedbacks
            .Where(r => r.Score > 0.7)
            .Select(r => $"之前的类似问题: {r.Document.Content}\n用户选择: {r.Document.Metadata["selectedOption"]}")
            .Join("\n\n");
        
        // 4. 可选：主动提示用户
        if (similarFeedbacks.First().Score > 0.9)
        {
            var lastFeedback = similarFeedbacks.First();
            return new Response
            {
                Content = $"我找到之前处理过类似问题。\n\n" +
                         $"当时您选择了「{lastFeedback.Document.Metadata["selectedOption"]}」。\n" +
                         $"是否需要我按照同样的方式处理？",
                Suggestions = new[] { "是，按照之前的处理", "不，我有新的需求" }
            };
        }
    }
    
    // 5. 正常处理
    return await ExecuteAsync(query);
}
```

---

## 8. 关键文件

| 文件 | 作用 |
|------|------|
| `InteractionManager.cs` | 管理用户交互点 |
| `TaskExecutionEngine.cs` | 任务执行引擎 |
| `RAGRecall.cs` | RAG 召回系统 |
| `FeedbackPersistence.cs` | 反馈持久化 |
| `FeedbackStore.cs` | 反馈存储 |
