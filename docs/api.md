# AgentFramework API 文档

## 目录

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
13. [Agent 注册与下轮预估](#13-agent-注册与下轮预估)
14. [本地强制指令](#14-本地强制指令)
15. [返回后处理区段标记](#15-返回后处理区段标记)
16. [任务计划执行器](#16-任务计划执行器)
17. [本地推理](#17-本地推理)
18. [问询数据类型与校验](#18-问询数据类型与校验)
19. [批量问询](#19-批量问询)
20. [子任务置信度与证据门槛](#20-子任务置信度与证据门槛)
21. [问询偏好库](#21-问询偏好库)
22. [双模式输出](#22-双模式输出)
23. [Vulkan 模式加载](#23-vulkan-模式加载)
24. [agent 间问询静默](#24-agent-间问询静默)
25. [Skill 开放规范包](#25-skill-开放规范包)
26. [统一输出接口](#26-统一输出接口)
27. [agent.io 输入输出协议库](#27-agentio-输入输出协议库)
28. [模型队列与 Token 统计](#28-模型队列与-token-统计)
29. [Skill 调度器与触发匹配](#29-skill-调度器与触发匹配)
30. [ConfigWriter 公开配置读写](#30-configwriter-公开配置读写)

> 附: [依赖注入扩展](#依赖注入扩展) · [示例](#示例) · 指令用法见 [CLI指令说明.md](CLI指令说明.md)

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

## 13. Agent 注册与下轮预估

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

## 14. 本地强制指令

```csharp
// 非 LLM 指令: 进入意图识别前拦截, 零 token
LocalCommandResult r = LocalCommandRouter.TryRoute("/stop");
// r.Handled=true, r.Command=LocalCommand.Stop (支持 /stop /continue /pause /status /reset)
```

## 15. 返回后处理区段标记

```csharp
// 快速标记: fenced 区段识别 (```html → UI, 代码块 → 审查服务等), 路由插件化
var router = new ResponseSegmentRouter(provider.GetServices<IResponseSegmentPlugin>());
string processed = await router.ProcessAsync(llmOutput, ct);

// 纯切分 (不路由): 
List<ResponseSegment> segs = ResponseSegmenter.Segment(llmOutput);
// Segment: Kind (PlainText/Code/Json/Fenced), Language, StartLine/EndLine
```

## 16. 任务计划执行器

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

## 17. 本地推理

```csharp
using agent.llamalocal;

// LLamaSharp 0.27.0 + Backend.CPU; 模型文件缺失时诚实报错
var llama = new LocalLlamaCaller(logger, modelPath: "./models/qwen2.5-0.5b-q4.gguf");
LLMResponse resp = await llama.CallAsync(prompt, ct);
```

---

## 18. 问询数据类型与校验

```csharp
using agent.userinteraction;

// 18 类问询数据类型 (枚举固定)
public enum PromptDataType
{
    String, Integer, Number, Date, Time, DateTime,
    Choice, MultiChoice, Boolean,
    Path, Url, Email, CodeExpression, Multiline,
    IpAddress, Port, KeyValue,
}

// 纯规则校验 + 规范化 (微秒级)
var (ok, normalized, error) = PromptDataValidator.Validate(
    PromptDataType.Date, "2026年9月6日");
// ok=true, normalized="2026-09-06"

// Choice 必须给全选项
var (ok2, val, err) = PromptDataValidator.Validate(
    PromptDataType.Choice, "写文档",
    new[] { "搜索资料", "写文档", "执行命令" });
```

## 19. 批量问询

```csharp
using agent.registry;

// 分组: 按 GroupId (空则按 NodeId) — 同组一次问完, 不一条一条问
List<List<ClarificationItem>> groups = ClarificationBatch.Group(clarificationItems);

// 执行一批 (内部: 偏好复用 → 打包问询 → DataType 校验 → 失败重问 → 审计)
BatchResult result = await ClarificationBatch.AskAsync(
    prompts, "task-plan", groups[0],
    maxRetries: 2,
    preferences: preferenceStore);   // 传偏好库自动复用+回写

// 结果: Answered/Value/Error — 不伪造答案
foreach (var ans in result.Answers)
    Console.WriteLine($"{ans.Item.ParameterName}: {ans.Value ?? ans.Error}");
```

## 20. 子任务置信度与证据门槛

```csharp
using agent.intent;
using agent.registry;

// 拆解即评估 (纯规则, 零 LLM 调用): SubTask 带 Confidence + Flags
List<IntentDecomposer.SubTask> tasks = IntentDecomposer.Decompose("处理一下这个文件，然后写总结");
foreach (var t in tasks)
    Console.WriteLine($"{t.Text} conf={t.Confidence} flags={t.Flags}");

// 证据门槛: 低置信 → 向发起者索要证据; 最大疑问数限制 (默认 3)
var gate = new EvidenceGate(maxQuestions: 3, confidenceThreshold: 0.60);
EvidenceGate.GateResult verdict = gate.Evaluate(tasks);

foreach (var req in verdict.ToAsk)          // 上限内, 按优先级排好
    Console.WriteLine($"问: {req.SubTask.Text} ({req.Questions.Count} 问)");
foreach (var dropped in verdict.DroppedForLimit) // 超限 → 走兜底不静默
    Console.WriteLine($"兜底: {dropped.Text}");
```

## 21. 问询偏好库

```csharp
using agent.registry;

// 偏好 = 模式特征, 不是凭据/不是本次输入值
var store = new ClarificationPreferenceStore("data");   // 落盘 data/clarification_preferences.json

// 记录: 合法答案 → 规范化模式 (path→"absolute"; choice→选项序); ApiKey 类拒收
store.RecordAnswer(clarificationItem, normalizedAnswer);

// 复用: 同类新问题 (同指纹) → SuggestedValues 注入偏好 / 选项序重排
store.ApplyTo(newItem);

// 指纹: 意图类别 + 数据类型 (剔除具体值)
string fp = ClarificationFingerprint.Build("保存到哪个路径?", "output", PromptDataType.Path);
```

## 22. 双模式输出

```csharp
using agent.output;

// 底层结构化格式: 一切返回内容统一此格式
var message = AgentOutputMessage.FromLlmAnswer(markdownContent, source, segments);

// 双模式
message.Mode = OutputMode.Markdown;   // 全人性化格式 (文件日志/富界面)
message.Mode = OutputMode.PlainText;  // 纯文本平铺 (控制台/管道)

// 纯规则双向转换
string plain = OutputFormatter.ToPlainText(markdown);

// Spectre.Console 渲染 (第三方库美化, 按消息种类着色; 非 TTY 自动降级)
var renderer = new SpectreOutputRenderer();
renderer.Render(message);
```

CLI: `agenthost --output-mode text "..."` (默认 markdown)。

## 23. Vulkan 模式加载

```csharp
using agent.llamalocal;

// 后端模式: Auto (探测 loader) / Cpu / Vulkan
// Vulkan 模式复用系统 libvulkan.so.1 (与 Silk.NET.Vulkan P/Invoke 同一动态库)
var caller = new LocalLlamaCaller(logger, modelPath,
    contextSize: 4096,
    backendMode: LlamaBackendMode.Auto,   // 有 vulkan loader + 产物 → vulkan, 否则 CPU
    gpuLayers: 16);                        // vulkan 模式 GPU offload 层数

// 底层: NativeLibraryConfig.LLama.WithVulkan(true) 在 LoadFromFile 前配置 (VulkanSupport.Configure)
// 强制 Vulkan 而 loader 缺失 → InvalidOperationException (不静默滑回 CPU)
```

## 24. agent 间问询静默

```csharp
// IUserPromptService 新增开关
prompts.SilentInterAgent = true;

// 之后 MainAgentAllowed 问询: 不打印控制台, 主 agent 空值占位代答 (不编造) + 审计
// 凭据/敏感项 (Kind=ApiKey 或 Sensitive) 不受开关影响 — 永远问真人
```

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

更多示例请参考 [readme.md](../readme.md) 与 [架构文档](architecture.md)。


---

## 28. 模型队列与 Token 统计

### ModelQueueRouter (agent.modelqueue)

```csharp
// 三通道调度: 本地 (LocalLlamaCaller 实跑) > 官方 > 远端; 余额检查在主链
QueuePrompt prompt = new()
{
    SystemPrompt = "...",
    History = new List<QueueHistoryMessage> { new() { Role = "user", Content = "..." } },
    UserMessage = "...",
    EstimatedTokens = 500,
};
QueueResponse resp = await router.CallAsync(prompt, TaskKindHint.General, intent: "coding");

resp.Success;        // bool
resp.Content;        // 回复文本
resp.Model;          // 实际执行模型
resp.PromptTokens;   // 用量 (本地累计进 TokenUsageService)
router.SetManualOverride("deepseek-chat");  // manual 模式 (≡ /model <id|序号>)
router.SetManualOverride(null);             // ≡ /model auto
router.Catalog;      // ModelCatalog (6 模型: 价格/推理分/编码分/上下文窗)
```

### TokenUsageService (余额三段式 + 切模)

```csharp
await tokenUsage.InitializeAsync(ct);       // ① 初始化: 真实 API 余额同步一次
tokenUsage.RecordUsage(model, provider, promptTk, completionTk);  // ② 每次调用本地累计
tokenUsage.NeedsResync(provider);           // ③ 超阈值 (默认 10 万 token) → TryResyncAsync
var (remaining, sufficient) = tokenUsage.EstimateBalance(provider, estimatedTokens);
UsageStatsSnapshot stats = tokenUsage.GetStats();   // ≡ /token stats (全 JSON)
```

余额不足 → Router 主链自动 `SelectAlternativeByBalance` 切换其他模型, `LastBalanceFlag`
携带 `model:xxx flags:余额不足` 协议行 (前端展示)。

### 配套配置 (config/base/models.yaml)

- `balance_schemes`: 按 provider 的余额查询端点/解析路径 (openai/deepseek 已配)
- `proxy`: 官方端点 HTTP 代理 (留空直连; ConfigurePrimaryHttpMessageHandler 实现)
- `local`: 本地 gguf 路径; 缺失时 LocalLlamaCaller.IsAvailable=false 诚实降级

## 29. Skill 开放规范包

### SkillPackageLoader (agent.skills)

```csharp
// SKILL.md 目录包 (Anthropic Agent-Skills Open Standard):
//   skill-name/SKILL.md  — front-matter (name 必填, =目录名) + Markdown 正文
//   scripts/ references/ assets/  — 可选目录
List<SkillDefinition> pkgs = SkillPackageLoader.LoadPackages("skills/");

// SkillRegistry.LoadFromDirectory 同时加载: 开放规范包 + legacy *.yaml (并存, 同名包优先)
SkillRegistry registry = SkillRegistry.LoadFromDirectory("skills/");
```

front-matter 字段映射: `name`→SkillId (目录名必须相等, 不符拒绝); `description`→Domain (语义匹配文本);
扩展字段 keywords/regex_patterns/domain_words/priority/exclusive/force_template/forbidden_words 双向兼容
(外部生态包缺省时走纯语义/关键词调度)。

### TriggerMatcher 语义层

```csharp
// 词面 (关键词/正则/领域词) 全未命中 → bge 嵌入余弦 cos≥0.45 疑似命中 (level 1)
// ITextEmbedder 可选注入; 不可用/失败静默回退词面 (行为兼容)
var matcher = new TriggerMatcher(definition, embedder: bgeEmbedder);
TriggerResult r = matcher.Match(userInput);   // r.Level / r.Precision
```

## 30. 统一输出接口 (v0.10.0)

### IOutputSink (agent.host)

```csharp
public interface IOutputSink
{
    void Write(string text);
    void WriteMarkdown(string text);
    void Step(int no, string what, string detail = "");
}
// 实现: ConsoleOutputSink (默认终端) / FileOutputSink (--log)
// 扩展点: WebSocket/IPC 前端实现此接口即复用整个 CliSession 逻辑
```

库内纪律: agent 库零 Console 直写 (审计: 仅 userinteraction 的 ConsoleUserInteraction 保留 —
其本身即控制台交互实现); 日志/审批/前端指令/步骤状态全部经 IOutputSink / ILogger / IChatboxSink。

### IChatboxSink (agent.logging)

```csharp
sink.Push(new FrontendDirective { Type = "thinking_page_switch", ... });  // @chatbox:{json} 协议行
// 前端 Console.ReadLine() 逐行解析; 协议详见 CLI指令说明.md
```

---

## 27. agent.io 输入输出协议库

独立项目 `src/agent.io` — **netstandard2.1**、零依赖, 供任意前端/宿主引用。

### 统一命令协议 (v0.11.0 — @cmd 行协议)

agent → 前端方向一致命令接口: 余额不足/思考切页/输出追加/模型切换/Skill 进度全部收敛为
`AgentCommand` 信封, 经 `AgentCommandWriter` (组合任意 WriterBase 传输) 写出,
前端用 `AgentCommandReader` (组合任意 ReaderBase 传输) 读取。

```csharp
// 写侧 (agent): 余额不足 → 前端
var commands = new AgentCommandWriter(new AgentRequestWriter(Console.Out));
commands.Send(AgentCommandNames.BalanceInsufficient,
    ("model", "deepseek-chat"), ("from", "gpt-4o"), ("remaining", "$1.24"));
// 线上: @cmd balance_insufficient model=deepseek-chat from=gpt-4o remaining=%241.24

// 读侧 (前端): 逐事件解析
var reader = new AgentCommandReader(new TextReportReader(Console.In));
AgentCommand? cmd;
while ((cmd = reader.ReadCommand(ev => HandleOther(ev))) != null)
{
    if (cmd.Name == AgentCommandNames.BalanceInsufficient)
        ShowBanner($"模型 {cmd.Get("from")} 余额不足 → 已切换 {cmd.Get("model")}");
}
```

已知命令名 (`AgentCommandNames`): `balance_insufficient` / `thinking_page_switch` /
`thinking_end` / `output_append` / `model_switch` / `skill_progress` / `skill_done`。
未知命令名前向兼容 (前端自行忽略或处理)。值转义: 空格 %20、= %3D、% %25、换行 %0A。

### AgentReportReaderBase (输出读取基类)

行协议状态机: 单行事件 (Text / ChatboxDirective / Json) + 多行流式块 (StreamBegin/Chunk/End)。

三种传输实现 (命令层无感切换 — 同一 AgentCommandWriter/Reader 组合任意一对):
- **Console.IO**: `AgentRequestWriter(TextWriter)` + `TextReportReader(TextReader)` — stdin/stdout/文件
- **共享内存**: `SharedMemoryRequestWriter/ReportReader` (文件-backed mmap 环形区; Linux 建议 /dev/shm — 同机进程零拷贝)
- **Socket (TCP)**: `SocketChannelServer` (agent 侧监听) + `SocketChannel.Connect` (前端侧) — 跨机/容器

```csharp
AgentReportReaderBase reader = new TextReportReader(Console.In);
ReportEvent? e = reader.ReadEvent();          // 聚合一个完整语义事件
List<string>? block = reader.ReadStreamBlock(); // 聚合下一个流式块
List<ReportEvent> all = reader.ReadAll();      // 读到流结束
```

| ReportEventKind | 触发 |
|---|---|
| Text | 普通行 |
| ChatboxDirective | `@chatbox:{json}` |
| StreamBegin / StreamChunk / StreamEnd | `@stream begin` … `@stream end` 块 |
| Json | `{…}` 单行 fast-path |
| Eof | 流结束 |

### AgentRequestWriterBase / AgentRequestWriter (请求写入)

```csharp
AgentRequestWriterBase w = new AgentRequestWriter(Console.Out);
w.WriteRequest("/status");       // 单行
w.WriteRequest("多行\n内容");    // 自动流式块
w.WriteStreamBlock("行1", "行2");// 显式块
```

协议常量: `ChatboxPrefix`=`@chatbox:`、`StreamBeginMarker`=`@stream begin`、`StreamEndMarker`=`@stream end`。
指令清单与输出契约见 [CLI指令说明.md](CLI指令说明.md)。


### ConfigWriter (v7.15 需求4: 公开配置读写)

`agent.config` 内新增 — 与 `ConfigSnapshot` 配对的写入口 (外部 C# 项目可直接引用 agent.config):

```csharp
var snapshot = new ConfigSnapshot("./config");
// 快速读取 (dot-path): 模块 → 嵌套路径
int max = ConfigWriter.GetValue(snapshot, "model_queue", "router.max_failures", 3);

var writer = new ConfigWriter("./config");
writer.SetRuntime("model_queue", "router.max_failures", 5);   // L4 runtime/dynamic.yaml (@dynamic)
writer.UpdateModule("model_queue", new Dictionary<string, object?>
{
    ["router"] = new Dictionary<string, object?> { ["sticky"] = false },  // L3 深合并
});
writer.ResetModule("model_queue");                             // 清 L3 覆盖, 回落 L1
```

- 写只落 L3 (`modules/{module}.yaml` 同名覆盖) / L4 (`runtime/dynamic.yaml`) — L1 base 永不直改
- 文件内容顶层 key = 模块名 (分层契约); 深合并语义; null 覆盖项 = 删除回落
- 全部走 MiniYaml (零反射 AOT 安全)
