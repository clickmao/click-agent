using System.Text.Json.Serialization;

namespace agent.core;

/// <summary>
/// 消息模型
/// </summary>
public class Message
{
    /// <summary>
    /// 消息ID
    /// </summary>
    [JsonPropertyName("id")]
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>
    /// 会话ID
    /// </summary>
    [JsonPropertyName("session_id")]
    public string SessionId { get; set; } = string.Empty;
    
    /// <summary>
    /// 发送者ID
    /// </summary>
    [JsonPropertyName("sender_id")]
    public string SenderId { get; set; } = string.Empty;
    
    /// <summary>
    /// 消息角色
    /// </summary>
    [JsonPropertyName("role")]
    public MessageRole Role { get; set; } = MessageRole.User;
    
    /// <summary>
    /// 消息内容
    /// </summary>
    [JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;
    
    /// <summary>
    /// 消息类型
    /// </summary>
    [JsonPropertyName("type")]
    public MessageType Type { get; set; } = MessageType.Text;
    
    /// <summary>
    /// 时间戳
    /// </summary>
    [JsonPropertyName("timestamp")]
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    
    /// <summary>
    /// 元数据
    /// </summary>
    [JsonPropertyName("metadata")]
    public Dictionary<string, object> Metadata { get; set; } = new();
    
    /// <summary>
    /// 提取的关键词
    /// </summary>
    [JsonPropertyName("keywords")]
    public List<string> Keywords { get; set; } = new();
    
    /// <summary>
    /// 识别的意图
    /// </summary>
    [JsonPropertyName("intent")]
    public string? Intent { get; set; }
    
    /// <summary>
    /// 置信度
    /// </summary>
    [JsonPropertyName("confidence")]
    public double Confidence { get; set; } = 1.0;
    
    /// <summary>
    /// 回复的消息ID（如果这是回复）
    /// </summary>
    [JsonPropertyName("reply_to")]
    public string? ReplyTo { get; set; }
    
    /// <summary>
    /// Token数估算
    /// </summary>
    [JsonPropertyName("token_count")]
    public int TokenCount { get; set; }
}

/// <summary>
/// Agent响应模型
/// </summary>
public class AgentResponse
{
    /// <summary>
    /// 响应ID
    /// </summary>
    [JsonPropertyName("id")]
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>
    /// 请求ID
    /// </summary>
    [JsonPropertyName("request_id")]
    public string? RequestId { get; set; }
    
    /// <summary>
    /// 响应内容
    /// </summary>
    [JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;
    
    /// <summary>
    /// 响应类型
    /// </summary>
    [JsonPropertyName("type")]
    public MessageType Type { get; set; } = MessageType.Text;
    
    /// <summary>
    /// 是否成功
    /// </summary>
    [JsonPropertyName("success")]
    public bool Success { get; set; } = true;
    
    /// <summary>
    /// 错误消息
    /// </summary>
    [JsonPropertyName("error")]
    public string? Error { get; set; }
    
    /// <summary>
    /// Agent状态
    /// </summary>
    [JsonPropertyName("agent_state")]
    public AgentState AgentState { get; set; } = AgentState.Ready;
    
    /// <summary>
    /// 生成的Token数
    /// </summary>
    [JsonPropertyName("tokens_generated")]
    public int TokensGenerated { get; set; }
    
    /// <summary>
    /// 执行时间（毫秒）
    /// </summary>
    [JsonPropertyName("execution_time_ms")]
    public long ExecutionTimeMs { get; set; }
    
    /// <summary>
    /// 相关记忆条目
    /// </summary>
    [JsonPropertyName("related_memories")]
    public List<string> RelatedMemories { get; set; } = new();
    
    /// <summary>
    /// 使用的工具
    /// </summary>
    [JsonPropertyName("tools_used")]
    public List<string> ToolsUsed { get; set; } = new();
    
    /// <summary>
    /// 额外数据
    /// </summary>
    [JsonPropertyName("data")]
    public Dictionary<string, object> Data { get; set; } = new();
    
    /// <summary>
    /// 时间戳
    /// </summary>
    [JsonPropertyName("timestamp")]
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    
    /// <summary>
    /// 创建成功响应
    /// </summary>
    public static AgentResponse SuccessResponse(string content, MessageType type = MessageType.Text)
    {
        return new AgentResponse
        {
            Content = content,
            Type = type,
            Success = true
        };
    }
    
    /// <summary>
    /// 创建错误响应
    /// </summary>
    public static AgentResponse ErrorResponse(string error)
    {
        return new AgentResponse
        {
            Content = string.Empty,
            Error = error,
            Success = false,
            AgentState = AgentState.Error
        };
    }
}
