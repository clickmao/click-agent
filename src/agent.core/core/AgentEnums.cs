namespace agent.core;

/// <summary>
/// Agent状态枚举
/// </summary>
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

/// <summary>
/// 消息角色
/// </summary>
public enum MessageRole
{
    /// <summary>系统消息</summary>
    System,
    
    /// <summary>用户消息</summary>
    User,
    
    /// <summary>助手消息</summary>
    Assistant,
    
    /// <summary>工具消息</summary>
    Tool,
    
    /// <summary>子Agent消息</summary>
    SubAgent
}

/// <summary>
/// 消息类型
/// </summary>
public enum MessageType
{
    /// <summary>文本消息</summary>
    Text,
    
    /// <summary>代码消息</summary>
    Code,
    
    /// <summary>命令消息</summary>
    Command,
    
    /// <summary>确认请求</summary>
    ConfirmationRequest,
    
    /// <summary>确认响应</summary>
    ConfirmationResponse,
    
    /// <summary>错误消息</summary>
    Error,
    
    /// <summary>状态消息</summary>
    Status,
    
    /// <summary>搜索结果</summary>
    SearchResult,
    
    /// <summary>文件内容</summary>
    File
}

/// <summary>
/// 任务类型
/// </summary>
public enum TaskType
{
    /// <summary>代码生成</summary>
    CodeGeneration,
    
    /// <summary>代码审查</summary>
    CodeReview,
    
    /// <summary>文档生成</summary>
    Documentation,
    
    /// <summary>搜索</summary>
    Search,
    
    /// <summary>分析</summary>
    Analysis,
    
    /// <summary>测试</summary>
    Testing,
    
    /// <summary>重构</summary>
    Refactoring,
    
    /// <summary>通用任务</summary>
    General
}

/// <summary>
/// 任务状态
/// </summary>
public enum TaskStatus
{
    /// <summary>待处理</summary>
    Pending,
    
    /// <summary>运行中</summary>
    Running,
    
    /// <summary>等待依赖</summary>
    WaitingForDependencies,
    
    /// <summary>完成</summary>
    Completed,
    
    /// <summary>失败</summary>
    Failed,
    
    /// <summary>已取消</summary>
    Cancelled,
    
    /// <summary>超时</summary>
    Timeout
}

/// <summary>
/// 会话状态
/// </summary>
public enum SessionState
{
    /// <summary>初始</summary>
    Initial,
    
    /// <summary>活跃</summary>
    Active,
    
    /// <summary>暂停</summary>
    Paused,
    
    /// <summary>等待确认</summary>
    WaitingForConfirmation,
    
    /// <summary>已完成</summary>
    Completed,
    
    /// <summary>已终止</summary>
    Terminated
}

/// <summary>
/// 会话循环状态
/// </summary>
public enum SessionLoopState
{
    /// <summary>已停止</summary>
    Stopped,
    
    /// <summary>运行中</summary>
    Running,
    
    /// <summary>暂停</summary>
    Paused,
    
    /// <summary>等待输入</summary>
    WaitingForInput,
    
    /// <summary>处理中</summary>
    Processing
}

/// <summary>
/// 确认类型
/// </summary>
public enum ConfirmationType
{
    /// <summary>保存模板</summary>
    SaveTemplate,
    
    /// <summary>保存示例</summary>
    SaveExample,
    
    /// <summary>确认操作</summary>
    ConfirmAction,
    
    /// <summary>选择选项</summary>
    SelectOption,
    
    /// <summary>批准变更</summary>
    ApproveChange,
    
    /// <summary>拒绝变更</summary>
    RejectChange,
    
    /// <summary>自定义</summary>
    Custom
}

/// <summary>
/// 记忆类型
/// </summary>
public enum ContentCategory
{
    /// <summary>会话</summary>
    Conversation,
    
    /// <summary>模板</summary>
    Template,
    
    /// <summary>示例</summary>
    Example,
    
    /// <summary>模式</summary>
    Pattern,
    
    /// <summary>决策</summary>
    Decision,
    
    /// <summary>偏好</summary>
    Preference,
    
    /// <summary>摘要</summary>
    Summary
}


