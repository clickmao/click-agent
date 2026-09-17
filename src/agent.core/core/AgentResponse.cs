using System.Text.Json.Serialization;

namespace agent.core;


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
