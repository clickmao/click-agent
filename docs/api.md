# AgentFramework API 文档

## 目录

> v7.11-v7.12 新增章节: 13 Agent 注册与下轮预估 / 14 本地强制指令 / 15 区段标记 / 16 任务计划执行器 / 17 本地推理

1. [核心接口](#1-核心接口)
2. [记忆系统](#2-记忆系统)
3. [模板系统](#3-模板系统)
4. [搜索服务](#4-搜索服务)
5. [SubAgent系统](#5-subagent系统)
6. [会话管理](#6-会话管理)
7. [用户交互](#7-用户交互)
8. [任务管道](#8-任务管道)
9. [Token压缩](#9-token压缩)
10. [数据存储](#10-数据存储)
11. [趋势分析](#11-趋势分析)
12. [MAF集成](#12-maf集成)

---

## 1. 核心接口

### IAgent

Agent核心接口，定义Agent的基本行为。

```csharp
public interface IAgent
{
    /// <summary>
    /// Agent唯一标识符
    /// </summary>
    string Id { get; }
    
    /// <summary>
    /// Agent名称
    /// </summary>
    string Name { get; }
    
    /// <summary>
    /// 当前状态
    /// </summary>
    AgentState State { get; }
    
    /// <summary>
    /// 初始化Agent
    /// </summary>
    Task InitializeAsync(IAgentContext context, CancellationToken ct = default);
    
    /// <summary>
    /// 处理消息
    /// </summary>
    Task<AgentResponse> ProcessAsync(Message message, CancellationToken ct = default);
    
    /// <summary>
    /// 执行子任务
    /// </summary>
    Task<AgentResponse> ExecuteTaskAsync(SubAgentTask task, CancellationToken ct = default);
    
    /// <summary>
    /// 路由消息到合适的处理器
    /// </summary>
    Task<AgentResponse> RouteAsync(Message message, CancellationToken ct = default);
    
    /// <summary>
    /// 关闭Agent
    /// </summary>
    Task ShutdownAsync(CancellationToken ct = default);
}
```

### IAgentContext

Agent执行上下文，提供访问各种服务的能力。

```csharp
public interface IAgentContext
{
    /// <summary>
    /// 会话ID
    /// </summary>
    string SessionId { get; }
    
    /// <summary>
    /// 用户ID
    /// </summary>
    string UserId { get; }
    
    /// <summary>
    /// 父上下文（用于SubAgent）
    /// </summary>
    IAgentContext? Parent { get; }
    
    /// <summary>
    /// 自定义属性
    /// </summary>
    IDictionary<string, object> Properties { get; }
    
    /// <summary>
    /// Token预算
    /// </summary>
    long TokenBudget { get; set; }
    
    /// <summary>
    /// 已使用的Token数
    /// </summary>
    long TokensUsed { get; }
    
    /// <summary>
    /// 获取记忆存储
    /// </summary>
    Task<IMemoryStore> GetMemoryAsync(string name = "default");
    
    /// <summary>
    /// 获取模板存储
    /// </summary>
    Task<ITemplateStore> GetTemplateStoreAsync();
    
    /// <summary>
    /// 获取搜索服务
    /// </summary>
    Task<ISearchService> GetSearchServiceAsync();
    
    /// <summary>
    /// 获取数据存储
    /// </summary>
    Task<IDataStore> GetDataStoreAsync();
}
```

### AgentState

```csharp
public enum AgentState
{
    /// <summary>初始状态</summary>
    Initial,
    
    /// <summary>初始化中</summary>
    Initializing,
    
    /// <summary>就绪</summary>
    Ready,
    
    /// <summary>处理中</summary>
    Processing,
    
    /// <summary>等待用户输入</summary>
    WaitingForInput,
    
    /// <summary>暂停</summary>
    Paused,
    
    /// <summary>错误</summary>
    Error,
    
    /// <summary>已关闭</summary>
    Shutdown
}
```

### Message

```csharp
public class Message
{
    /// <summary>消息ID</summary>
    public string Id { get; set; }
    
    /// <summary>会话ID</summary>
    public string SessionId { get; set; }
    
    /// <summary>发送者ID</summary>
    public string SenderId { get; set; }
    
    /// <summary>消息角色</summary>
    public MessageRole Role { get; set; }
    
    /// <summary>消息内容</summary>
    public string Content { get; set; }
    
    /// <summary>消息类型</summary>
    public MessageType Type { get; set; }
    
    /// <summary>时间戳</summary>
    public DateTime Timestamp { get; set; }
    
    /// <summary>元数据</summary>
    public Dictionary<string, object> Metadata { get; set; }
    
    /// <summary>提取的关键词</summary>
    public List<string> Keywords { get; set; }
    
    /// <summary>识别的意图</summary>
    public string? Intent { get; set; }
    
    /// <summary>置信度</summary>
    public double Confidence { get; set; }
}
```

---

## 2. 记忆系统

### IMemoryStore

```csharp
public interface IMemoryStore
{
    /// <summary>
    /// 添加记忆条目
    /// </summary>
    Task<MemoryEntry> AddAsync(MemoryEntry entry);
    
    /// <summary>
    /// 查询记忆
    /// </summary>
    Task<IEnumerable<MemoryEntry>> QueryAsync(MemoryQuery query);
    
    /// <summary>
    /// 获取单个记忆
    /// </summary>
    Task<MemoryEntry?> GetAsync(string id);
    
    /// <summary>
    /// 更新记忆
    /// </summary>
    Task UpdateAsync(MemoryEntry entry);
    
    /// <summary>
    /// 删除记忆
    /// </summary>
    Task DeleteAsync(string id);
    
    /// <summary>
    /// 获取最近的记忆
    /// </summary>
    Task<IEnumerable<MemoryEntry>> GetRecentAsync(int count);
    
    /// <summary>
    /// 通过关键词获取记忆
    /// </summary>
    Task<IEnumerable<MemoryEntry>> GetByKeywordsAsync(IEnumerable<string> keywords);
}
```

### MemoryEntry

```csharp
public class MemoryEntry
{
    public string Id { get; set; }
    public string Content { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime LastAccessedAt { get; set; }
    public int AccessCount { get; set; }
    public List<string> Keywords { get; set; }
    public MemoryType Type { get; set; }
    public double RelevanceScore { get; set; }
    public Dictionary<string, object> Metadata { get; set; }
}

public enum MemoryType
{
    Conversation,
    Template,
    Example,
    Pattern,
    Decision,
    Preference
}
```

### ISummarizer

```csharp
public interface ISummarizer
{
    /// <summary>
    /// 生成摘要
    /// </summary>
    Task<string> SummarizeAsync(string content, SummarizeOptions? options = null);
    
    /// <summary>
    /// 提取关键事实
    /// </summary>
    Task<IEnumerable<string>> ExtractKeyFactsAsync(string content);
    
    /// <summary>
    /// 提取决策点
    /// </summary>
    Task<IEnumerable<string>> ExtractDecisionsAsync(string content);
}
```

---

## 3. 模板系统

### ITemplateStore

```csharp
public interface ITemplateStore
{
    /// <summary>
    /// 添加模板
    /// </summary>
    Task<Template> AddAsync(Template template);
    
    /// <summary>
    /// 查询模板
    /// </summary>
    Task<IEnumerable<Template>> QueryAsync(TemplateQuery query);
    
    /// <summary>
    /// 通过ID获取模板
    /// </summary>
    Task<Template?> GetByIdAsync(string id);
    
    /// <summary>
    /// 通过名称和分类获取
    /// </summary>
    Task<Template?> GetByNameAsync(string name, string category);
    
    /// <summary>
    /// 更新模板
    /// </summary>
    Task UpdateAsync(Template template);
    
    /// <summary>
    /// 删除模板
    /// </summary>
    Task DeleteAsync(string id);
    
    /// <summary>
    /// 获取分类下的所有模板
    /// </summary>
    Task<IEnumerable<Template>> GetByCategoryAsync(string category);
    
    /// <summary>
    /// 应用模板生成内容
    /// </summary>
    Task<string> ApplyTemplateAsync(Template template, ApplyContext context);
}
```

### Template

```csharp
public class Template
{
    public string Id { get; set; }
    public string Name { get; set; }
    public string Category { get; set; }
    public string Version { get; set; }
    public string Description { get; set; }
    public string Pattern { get; set; }
    public string Schema { get; set; }
    public List<CorrectExample> CorrectExamples { get; set; }
    public List<IncorrectExample> IncorrectExamples { get; set; }
    public Dictionary<string, object> Metadata { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
    public int UsageCount { get; set; }
    public double SuccessRate { get; set; }
}
```

### CorrectExample & IncorrectExample

```csharp
public class CorrectExample
{
    public string Id { get; set; }
    public string Input { get; set; }
    public string Output { get; set; }
    public string Description { get; set; }
    public List<string> Tags { get; set; }
}

public class IncorrectExample
{
    public string Id { get; set; }
    public string Input { get; set; }
    public string IncorrectOutput { get; set; }
    public string Explanation { get; set; }
    public string CorrectApproach { get; set; }
    public List<string> Tags { get; set; }
}
```

---

## 4. 搜索服务

### ISearchService

```csharp
public interface ISearchService
{
    /// <summary>
    /// 搜索
    /// </summary>
    Task<SearchResult> SearchAsync(string query, SearchOptions? options = null);
    
    /// <summary>
    /// 批量搜索
    /// </summary>
    Task<IEnumerable<SearchResult>> BatchSearchAsync(
        IEnumerable<string> queries, 
        BatchSearchOptions? options = null);
    
    /// <summary>
    /// 提取页面内容
    /// </summary>
    Task<string> ExtractContentAsync(string url, ExtractOptions? options = null);
}
```

### SearchResult

```csharp
public class SearchResult
{
    public string Id { get; set; }
    public string Query { get; set; }
    public string Title { get; set; }
    public string Url { get; set; }
    public string Snippet { get; set; }
    public string Content { get; set; }
    public double RelevanceScore { get; set; }
    public DateTime CrawledAt { get; set; }
    public List<string> Keywords { get; set; }
    public SearchResultSource Source { get; set; }
}

public enum SearchResultSource
{
    WebReaper,
    Cache,
    Memory
}
```

---

## 5. SubAgent系统

### ISubAgentPool

```csharp
public interface ISubAgentPool
{
    /// <summary>
    /// 最大Agent数
    /// </summary>
    int MaxAgents { get; set; }
    
    /// <summary>
    /// 当前活跃Agent数
    /// </summary>
    int ActiveAgentCount { get; }
    
    /// <summary>
    /// 获取可用Agent
    /// </summary>
    Task<ISubAgent> AcquireAsync(CancellationToken ct = default);
    
    /// <summary>
    /// 释放Agent
    /// </summary>
    Task ReleaseAsync(ISubAgent agent);
    
    /// <summary>
    /// 尝试路由消息到Agent
    /// </summary>
    Task<bool> TryRouteAsync(Message message, out ISubAgent agent);
}
```

### ISubAgent

```csharp
public interface ISubAgent
{
    string Id { get; }
    string Name { get; }
    bool IsBusy { get; }
    SubAgentTask? CurrentTask { get; }
    
    Task InitializeAsync(IAgentContext context, CancellationToken ct);
    Task<AgentResponse> ExecuteAsync(SubAgentTask task, CancellationToken ct);
    Task ReportProgressAsync(double progress, string? status = null);
    Task CancelAsync();
}
```

### SubAgentTask

```csharp
public class SubAgentTask
{
    public string Id { get; set; }
    public string Name { get; set; }
    public string Description { get; set; }
    public string Input { get; set; }
    public TaskType Type { get; set; }
    public TaskStatus Status { get; set; }
    public TaskBoundary Boundary { get; set; }
    public List<string> Dependencies { get; set; }
    public string? AssignedAgentId { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? StartedAt { get; set; }
    public DateTime? CompletedAt { get; set; }
    public long TimeoutMs { get; set; }
    public long TokenBudget { get; set; }
    public string? Result { get; set; }
    public string? Error { get; set; }
}
```

### TaskBoundary

```csharp
public class TaskBoundary
{
    public string TaskId { get; set; }
    public List<string> InputRequirements { get; set; }
    public List<string> Dependencies { get; set; }
    public List<string> OutputFiles { get; set; }
    public List<string> OutputPatterns { get; set; }
    public long MaxTokens { get; set; }
    public long TimeoutMs { get; set; }
    public Dictionary<string, object> Constraints { get; set; }
    public Dictionary<string, object> ContextHints { get; set; }
}
```

---

## 6. 会话管理

### ISessionManager

```csharp
public interface ISessionManager
{
    Task<ISession> CreateSessionAsync(string userId, SessionConfig? config = null);
    Task<ISession> GetSessionAsync(string sessionId);
    Task UpdateSessionAsync(ISession session);
    Task EndSessionAsync(string sessionId);
    Task<ISessionLoop> GetSessionLoopAsync(string sessionId);
}
```

### ISession

```csharp
public interface ISession
{
    string Id { get; }
    string UserId { get; }
    SessionState State { get; }
    DateTime CreatedAt { get; }
    DateTime LastActivityAt { get; }
    int TurnCount { get; }
    long TokenUsage { get; }
    
    Task AddMessageAsync(Message message);
    Task<IEnumerable<Message>> GetMessagesAsync(int skip = 0, int take = 50);
    Task<MemoryEntry> SummarizeAsync();
}
```

### ISessionLoop

```csharp
public interface ISessionLoop
{
    string SessionId { get; }
    SessionLoopState State { get; }
    
    Task StartAsync(CancellationToken ct);
    Task PauseAsync();
    Task ResumeAsync();
    Task StopAsync();
    Task<UserConfirmRequest> WaitForConfirmationAsync(string requestId);
}
```

---

## 7. 用户交互

### IUserInteraction

```csharp
public interface IUserInteraction
{
    /// <summary>
    /// 请求用户确认
    /// </summary>
    Task<ConfirmationResult> RequestConfirmationAsync(
        UserConfirmRequest request, 
        CancellationToken ct = default);
    
    /// <summary>
    /// 显示进度
    /// </summary>
    Task ShowProgressAsync(ProgressInfo info);
    
    /// <summary>
    /// 显示消息
    /// </summary>
    Task ShowMessageAsync(MessageInfo info);
    
    /// <summary>
    /// 获取用户输入
    /// </summary>
    Task<string> GetUserInputAsync(InputRequest request, CancellationToken ct = default);
}
```

### UserConfirmRequest

```csharp
public class UserConfirmRequest
{
    public string Id { get; set; }
    public ConfirmationType Type { get; set; }
    public string Message { get; set; }
    public string? Details { get; set; }
    public List<ConfirmOption> Options { get; set; }
    public string? DefaultOption { get; set; }
    public TimeSpan? Timeout { get; set; }
    public Dictionary<string, object> Context { get; set; }
}

public enum ConfirmationType
{
    SaveTemplate,
    SaveExample,
    ConfirmAction,
    SelectOption,
    ApproveChange,
    RejectChange,
    Custom
}
```

---

## 8. 任务管道

### ITaskPipeline

```csharp
public interface ITaskPipeline
{
    /// <summary>
    /// 添加任务到管道
    /// </summary>
    Task EnqueueAsync(PipelineTask task);
    
    /// <summary>
    /// 获取下一个待处理任务
    /// </summary>
    Task<PipelineTask?> DequeueAsync(CancellationToken ct);
    
    /// <summary>
    /// 完成任务
    /// </summary>
    Task CompleteAsync(string taskId, string result);
    
    /// <summary>
    /// 失败任务
    /// </summary>
    Task FailAsync(string taskId, string error);
}
```

### TaskDecomposer

```csharp
public interface ITaskDecomposer
{
    /// <summary>
    /// 分解任务
    /// </summary>
    Task<DecompositionResult> DecomposeAsync(
        string task, 
        DecomposeOptions? options = null);
    
    /// <summary>
    /// 评估任务复杂度
    /// </summary>
    Task<ComplexityAssessment> AssessComplexityAsync(string task);
    
    /// <summary>
    /// 分析任务依赖
    /// </summary>
    Task<DependencyGraph> AnalyzeDependenciesAsync(IEnumerable<string> tasks);
}
```

---

## 9. Token压缩

### ITokenCompressor

```csharp
public interface ITokenCompressor
{
    /// <summary>
    /// 压缩上下文
    /// </summary>
    Task<string> CompressAsync(
        string context, 
        CompressionOptions? options = null);
    
    /// <summary>
    /// 计算Token数
    /// </summary>
    Task<int> CountTokensAsync(string text);
    
    /// <summary>
    /// 截断到指定Token数
    /// </summary>
    Task<string> TruncateAsync(string text, int maxTokens);
}
```

---

## 10. 数据存储

### IDataStore

```csharp
public interface IDataStore
{
    Task<DataEntry> SaveAsync(DataEntry entry);
    Task<DataEntry?> GetAsync(string key);
    Task<IEnumerable<DataEntry>> QueryAsync(DataQuery query);
    Task DeleteAsync(string key);
    Task<bool> ExistsAsync(string key);
}
```

---

## 11. 趋势分析

### ITendencyAnalyzer

```csharp
public interface ITendencyAnalyzer
{
    /// <summary>
    /// 分析用户趋势
    /// </summary>
    Task<TendencyProfile> AnalyzeUserTendencyAsync(string userId);
    
    /// <summary>
    /// 更新趋势数据
    /// </summary>
    Task UpdateTendencyAsync(string userId, TendencyData data);
    
    /// <summary>
    /// 获取上下文偏见
    /// </summary>
    Task<ContextBias> GetContextBiasAsync(string userId, string context);
}
```

---

## 12. MAF集成

### IMAFAgentHost

```csharp
public interface IMAFAgentHost
{
    string HostId { get; }
    bool IsRunning { get; }
    
    Task StartAsync(CancellationToken ct);
    Task StopAsync(CancellationToken ct);
    Task PublishMessageAsync(Message message);
    Task SubscribeAsync(string topic, Func<Message, Task> handler);
}
```

---

## 13. Agent 注册与下轮预估 (v7.11)

```csharp
using agent.registry;

// 持久化身份: 主/子 Agent UID + 从属关系, 落盘 DataStoragePath 下跨进程复用
var registry = new AgentRegistry("./data");
var child = registry.Register("search-worker", parentUid: registry.Main.Uid);
var found = registry.Get(child.Uid);            // 按 UID 查
var kids  = registry.ChildrenOf(registry.Main.Uid);

// 下轮预估: 任务循环完成后 Save; 下次对话 Load 读回 → ToPromptHeader 注入 LLM 提示头
ForecastRecord rec = NextTurnForecast.Save("./data", agentUid, taskText, intent);
ForecastRecord? prev = NextTurnForecast.Load("./data", agentUid);
string header = NextTurnForecast.ToPromptHeader(prev);
```

## 14. 本地强制指令 (v7.11)

```csharp
// 非 LLM 指令: 进入意图识别前拦截, 零 token
LocalCommandResult r = LocalCommandRouter.TryRoute("/stop");
// r.Handled=true, r.Command=LocalCommand.Stop (支持 /stop /continue /pause /status /reset)
```

## 15. 返回后处理区段标记 (v7.11)

```csharp
// 快速标记: fenced 区段识别 (```html → UI, 代码块 → 审查服务等), 路由插件化
var router = new ResponseSegmentRouter(provider.GetServices<IResponseSegmentPlugin>());
string processed = await router.ProcessAsync(llmOutput, ct);

// 纯切分 (不路由): 
List<ResponseSegment> segs = ResponseSegmenter.Segment(llmOutput);
// Segment: Kind (PlainText/Code/Json/Fenced), Language, StartLine/EndLine
```

## 16. 任务计划执行器 (v7.11)

```csharp
// 逐子任务顺序调度: 依赖拓扑 + 敏感暂停 (PausedForApproval) + 注入指令合并
var executor = new TaskPlanExecutor(async (node, ct) =>
{
    // 每个 PlanNode 的真实执行体
    return new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed };
});
TaskPlanRun run = await executor.ExecuteAsync(plan);
// run.State: Running / PausedForApproval / Cancelled / Finished
// run.NodeStates / run.PendingSensitiveNodeId / run.PauseReason
```

## 17. 本地推理 (v7.12)

```csharp
using agent.llamalocal;

// LLamaSharp 0.27.0 + Backend.CPU; 模型文件缺失时诚实报错
var llama = new LocalLlamaCaller(logger, modelPath: "./models/qwen2.5-0.5b-q4.gguf");
LLMResponse resp = await llama.CallAsync(prompt, ct);
```

---

## 依赖注入扩展

```csharp
// 在 Startup.cs 或 Program.cs 中
services.AddAgentFramework();

// 自定义配置
services.AddAgentFramework(options =>
{
    options.MaxSubAgents = 8;
    options.MaxTokenBudget = 150000;
    options.EnableMAF = true;
    options.EnableSearchCache = true;
    options.DataStoragePath = "./data";
});
```

## 示例

更多示例请参考 `examples/` 目录。
