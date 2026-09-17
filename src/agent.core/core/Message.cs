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
    /// R379 缓存前缀稳定化: 实际发送给 LLM 的 user 内容 (任务原文 + 本轮内联易变上下文)。
    /// 多轮回放必须逐字节重放"当初真正发出去的字节", 否则 provider 的缓存前缀单元失配
    /// (用户钦定 KPI 红线: 多轮会话第 2 轮起命中率 ≥90%, 目标 98~99%)。为空时回退 Content。
    /// </summary>
    [JsonPropertyName("sent_content")]
    public string? SentContent { get; set; }
    
    /// <summary>
    /// 消息类型
    /// </summary>
    [JsonPropertyName("type")]
    public MessageType Type { get; set; } = MessageType.Text;

    /// <summary>
    /// v0.12.0 A2: 图像附件 (路径或 URL) — 非空时 vision 链 (capabilities.image_input 路由)。
    /// </summary>
    [JsonPropertyName("image_attachments")]
    public List<string> ImageAttachments { get; set; } = new();
    
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
