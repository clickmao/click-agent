using Microsoft.Extensions.Logging;

namespace agent.memory;

/// <summary>
/// 记忆查询模型
/// </summary>
public class MemoryQuery
{
    /// <summary>
    /// 查询文本
    /// </summary>
    public string? Text { get; set; }
    
    /// <summary>
    /// 关键词
    /// </summary>
    public List<string>? Keywords { get; set; }
    
    /// <summary>
    /// 记忆类型
    /// </summary>
    public MemoryType? Type { get; set; }
    
    /// <summary>
    /// 会话ID
    /// </summary>
    public string? SessionId { get; set; }
    
    /// <summary>
    /// 用户ID
    /// </summary>
    public string? UserId { get; set; }
    
    /// <summary>
    /// 开始时间
    /// </summary>
    public DateTime? FromDate { get; set; }
    
    /// <summary>
    /// 结束时间
    /// </summary>
    public DateTime? ToDate { get; set; }
    
    /// <summary>
    /// 最小相关性分数
    /// </summary>
    public double? MinRelevance { get; set; }
    
    /// <summary>
    /// 跳过数量
    /// </summary>
    public int Skip { get; set; }
    
    /// <summary>
    /// 获取数量
    /// </summary>
    public int Take { get; set; } = 50;
    
    /// <summary>
    /// 排序字段
    /// </summary>
    public string SortBy { get; set; } = "CreatedAt";
    
    /// <summary>
    /// 是否降序
    /// </summary>
    public bool Descending { get; set; } = true;
}
