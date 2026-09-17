using Microsoft.Extensions.Logging;
using System.Text.Json.Serialization;

namespace agent.session;

/// <summary>
/// 会话模型
/// </summary>
public class Session
{
    /// <summary>
    /// 会话ID
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();

    /// <summary>
    /// 用户ID
    /// </summary>
    public string UserId { get; set; } = string.Empty;

    /// <summary>
    /// 会话状态
    /// </summary>
    public core.SessionState State { get; set; } = core.SessionState.Initial;

    /// <summary>
    /// 创建时间
    /// </summary>
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    /// <summary>
    /// 最后活动时间
    /// </summary>
    public DateTime LastActivityAt { get; set; } = DateTime.UtcNow;

    /// <summary>
    /// 轮次计数
    /// </summary>
    public int TurnCount { get; set; }

    /// <summary>
    /// Token使用量
    /// </summary>
    public long TokenUsage { get; set; }

    /// <summary>
    /// 消息列表
    /// </summary>
    public List<core.Message> Messages { get; set; } = new();

    /// <summary>
    /// 元数据
    /// </summary>
    public Dictionary<string, object> Metadata { get; set; } = new();

    /// <summary>会话长期记忆 + 任务目标画像 (v7.14, 懒创建; 上限由 MemoryMaxChars 控制)</summary>
    [JsonIgnore]
    public SessionMemory Memory
    {
        get
        {
            if (_memory == null)
            {
                var cap = Metadata.TryGetValue("memoryMaxChars", out var v) && v is int i ? i : SessionMemory.DefaultMaxChars;
                _memory = new SessionMemory(cap);
            }
            return _memory;
        }
    }

    [JsonIgnore]
    private SessionMemory? _memory;

    /// <summary>
    /// ✅ 添加用户消息
    /// </summary>
    public void AddUserMessage(string content)
    {
        Messages.Add(new core.Message
        {
            Id = Guid.NewGuid().ToString(),
            SessionId = Id,
            SenderId = UserId,
            Role = core.MessageRole.User,
            Content = content,
            Type = core.MessageType.Text,
            Timestamp = DateTime.UtcNow
        });
        TurnCount++;
        LastActivityAt = DateTime.UtcNow;
        TrimHistory();
    }

    /// <summary>
    /// ✅ 添加助手消息
    /// </summary>
    public void AddAssistantMessage(string content, string? senderId = null)
    {
        Messages.Add(new core.Message
        {
            Id = Guid.NewGuid().ToString(),
            SessionId = Id,
            SenderId = senderId ?? "assistant",
            Role = core.MessageRole.Assistant,
            Content = content,
            Type = core.MessageType.Text,
            Timestamp = DateTime.UtcNow
        });
        LastActivityAt = DateTime.UtcNow;
        TrimHistory();
    }

    /// <summary>
    /// 消息历史上限保护 (v7.8): 长会话内存无界增长防线。
    /// 超限裁剪最旧消息; 完整归档属持久化层职责, 不由内存会话承担。
    /// </summary>
    private void TrimHistory()
    {
        if (Messages.Count <= MaxHistoryMessages)
            return;
        
        var excess = Messages.Count - MaxHistoryMessages;
        Messages.RemoveRange(0, excess);
    }

    /// <summary>单会话消息历史上限</summary>
    public const int MaxHistoryMessages = 200;

    /// <summary>
    /// ✅ 获取最近的对话
    /// </summary>
    public List<core.Message> GetRecentMessages(int count = 10)
    {
        // v7.8: Messages 追加序 = 时间序, 直接倒序取尾部 (O(k)) 替代全表排序 (O(N log N))
        var result = new List<core.Message>(Math.Min(count, Messages.Count));
        for (var i = Messages.Count - 1; i >= 0 && result.Count < count; i--)
            result.Add(Messages[i]);
        result.Reverse();
        return result;
    }

    /// <summary>
    /// ✅ 获取相关消息（基于关键词）
    /// </summary>
    public List<core.Message> GetRelevantMessages(string query, int count = 5)
    {
        var keywords = query.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        // v7.8: 命中过滤在前 (O(N*M)), 排序只作用于命中子集 — 原实现对全表排序
        var matches = new List<core.Message>();
        foreach (var m in Messages)
        {
            if (m.Role == core.MessageRole.System)
                continue;
            foreach (var k in keywords)
            {
                if (m.Content.Contains(k, StringComparison.OrdinalIgnoreCase))
                {
                    matches.Add(m);
                    break;
                }
            }
        }
        
        matches.Sort(static (a, b) => b.Timestamp.CompareTo(a.Timestamp));
        if (matches.Count > count)
            matches.RemoveRange(count, matches.Count - count);
        return matches;
    }
    
    /// <summary>
    /// ✅ 添加用户消息（异步版本）
    /// </summary>
    public async Task AddUserMessageAsync(string content)
    {
        AddUserMessage(content);
        LastActivityAt = DateTime.UtcNow;
        await Task.CompletedTask;
    }
    
    /// <summary>
    /// ✅ 添加助手消息（异步版本）
    /// </summary>
    public async Task AddAssistantMessageAsync(string content, string? senderId = null)
    {
        AddAssistantMessage(content, senderId);
        LastActivityAt = DateTime.UtcNow;
        await Task.CompletedTask;
    }
    
    /// <summary>
    /// ✅ 获取对话摘要
    /// </summary>
    public string GetConversationSummary(int maxLength = 200)
    {
        var recent = GetRecentMessages(5);
        var summary = string.Join("\n", recent.Select(m => 
            $"[{m.Role}] {m.Content}"));
        
        if (summary.Length > maxLength)
            return summary[..maxLength] + "...";
        
        return summary;
    }
}
