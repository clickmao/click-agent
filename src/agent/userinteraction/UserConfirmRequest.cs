namespace agent.userinteraction;

/// <summary>
/// 用户确认请求
/// </summary>
public class UserConfirmRequest
{
    /// <summary>
    /// 请求ID
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>
    /// 确认类型
    /// </summary>
    public core.ConfirmationType Type { get; set; }
    
    /// <summary>
    /// 消息
    /// </summary>
    public string Message { get; set; } = string.Empty;
    
    /// <summary>
    /// 详情
    /// </summary>
    public string? Details { get; set; }
    
    /// <summary>
    /// 选项列表
    /// </summary>
    public List<ConfirmOption> Options { get; set; } = new();
    
    /// <summary>
    /// 默认选项
    /// </summary>
    public string? DefaultOption { get; set; }
    
    /// <summary>
    /// 超时时间
    /// </summary>
    public TimeSpan? Timeout { get; set; }
    
    /// <summary>
    /// 上下文
    /// </summary>
    public Dictionary<string, object> Context { get; set; } = new();
}

/// <summary>
/// 确认选项
/// </summary>
public class ConfirmOption
{
    /// <summary>
    /// 选项ID
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>
    /// 标签
    /// </summary>
    public string Label { get; set; } = string.Empty;
    
    /// <summary>
    /// 描述
    /// </summary>
    public string? Description { get; set; }
    
    /// <summary>
    /// 是否推荐
    /// </summary>
    public bool IsRecommended { get; set; }
    
    /// <summary>
    /// 元数据
    /// </summary>
    public Dictionary<string, object> Metadata { get; set; } = new();
}

/// <summary>
/// 确认结果
/// </summary>
public class ConfirmationResult
{
    /// <summary>
    /// 请求ID
    /// </summary>
    public string RequestId { get; set; } = string.Empty;
    
    /// <summary>
    /// 是否批准
    /// </summary>
    public bool Approved { get; set; }
    
    /// <summary>
    /// 选择的选项ID
    /// </summary>
    public string? SelectedOptionId { get; set; }
    
    /// <summary>
    /// 用户输入（如果有）
    /// </summary>
    public string? UserInput { get; set; }
    
    /// <summary>
    /// 时间戳
    /// </summary>
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    
    /// <summary>
    /// 超时
    /// </summary>
    public bool TimedOut { get; set; }
}

/// <summary>
/// 进度信息
/// </summary>
public class ProgressInfo
{
    /// <summary>
    /// 进度百分比
    /// </summary>
    public double Progress { get; set; }
    
    /// <summary>
    /// 状态消息
    /// </summary>
    public string? Status { get; set; }
    
    /// <summary>
    /// 当前步骤
    /// </summary>
    public string? CurrentStep { get; set; }
    
    /// <summary>
    /// 总步骤数
    /// </summary>
    public int TotalSteps { get; set; }
    
    /// <summary>
    /// 预估剩余时间
    /// </summary>
    public TimeSpan? EstimatedRemaining { get; set; }
}

/// <summary>
/// 消息信息
/// </summary>
public class MessageInfo
{
    /// <summary>
    /// 消息类型
    /// </summary>
    public MessageInfoType Type { get; set; } = MessageInfoType.Info;
    
    /// <summary>
    /// 标题
    /// </summary>
    public string? Title { get; set; }
    
    /// <summary>
    /// 内容
    /// </summary>
    public string Content { get; set; } = string.Empty;
    
    /// <summary>
    /// 详情
    /// </summary>
    public string? Details { get; set; }
    
    /// <summary>
    /// 操作列表
    /// </summary>
    public List<MessageAction> Actions { get; set; } = new();
}

/// <summary>
/// 消息类型
/// </summary>
public enum MessageInfoType
{
    Info,
    Warning,
    Error,
    Success,
    Debug
}

/// <summary>
/// 消息操作
/// </summary>
public class MessageAction
{
    /// <summary>
    /// 操作ID
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>
    /// 标签
    /// </summary>
    public string Label { get; set; } = string.Empty;
    
    /// <summary>
    /// 操作类型
    /// </summary>
    public MessageActionType Type { get; set; } = MessageActionType.Button;
}

/// <summary>
/// 操作类型
/// </summary>
public enum MessageActionType
{
    Button,
    Link,
    Copy
}

/// <summary>
/// 输入请求
/// </summary>
public class InputRequest
{
    /// <summary>
    /// 提示
    /// </summary>
    public string Prompt { get; set; } = string.Empty;
    
    /// <summary>
    /// 默认值
    /// </summary>
    public string? DefaultValue { get; set; }
    
    /// <summary>
    /// 是否多行
    /// </summary>
    public bool MultiLine { get; set; }
    
    /// <summary>
    /// 占位符
    /// </summary>
    public string? Placeholder { get; set; }
    
    /// <summary>
    /// 验证器
    /// </summary>
    public Func<string, (bool IsValid, string? ErrorMessage)>? Validator { get; set; }
}

/// <summary>
/// 用户交互接口
/// </summary>
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
    
    /// <summary>
    /// 显示搜索结果
    /// </summary>
    Task ShowSearchResultsAsync(IEnumerable<search.SearchResult> results);
    
    /// <summary>
    /// 显示模板列表
    /// </summary>
    Task ShowTemplateListAsync(IEnumerable<templates.Template> templates);
}
