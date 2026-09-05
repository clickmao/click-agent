namespace agent.rag;

/// <summary>
/// 用户反馈记录 (自旧任务规划体系迁入 — 反馈域归属 RAG)
/// </summary>
public class UserFeedback
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string SessionId { get; set; } = string.Empty;
    public string TaskId { get; set; } = string.Empty;
    public string InteractionId { get; set; } = string.Empty;
    public string SelectedOptionId { get; set; } = string.Empty;
    public string? SelectedOptionLabel { get; set; }
    public string? UserComment { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public List<string> Keywords { get; set; } = new();
    public string Context { get; set; } = string.Empty;
    public string TaskDescription { get; set; } = string.Empty;
    public string? Outcome { get; set; }
    public double? Satisfaction { get; set; }
    public Dictionary<string, object> Metadata { get; set; } = new();
}
