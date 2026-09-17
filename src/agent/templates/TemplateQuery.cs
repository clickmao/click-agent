namespace agent.templates;


/// <summary>
/// 模板查询
/// </summary>
public class TemplateQuery
{
    /// <summary>
    /// 名称（模糊匹配）
    /// </summary>
    public string? Name { get; set; }
    
    /// <summary>
    /// 分类
    /// </summary>
    public string? Category { get; set; }
    
    /// <summary>
    /// 模式（模糊匹配）
    /// </summary>
    public string? Pattern { get; set; }
    
    /// <summary>
    /// 标签
    /// </summary>
    public List<string>? Tags { get; set; }
    
    /// <summary>
    /// 是否启用
    /// </summary>
    public bool? IsEnabled { get; set; }
    
    /// <summary>
    /// 最小成功率
    /// </summary>
    public double? MinSuccessRate { get; set; }
    
    /// <summary>
    /// 跳过数量
    /// </summary>
    public int Skip { get; set; }
    
    /// <summary>
    /// 获取数量
    /// </summary>
    public int Take { get; set; } = 20;
    
    /// <summary>
    /// 排序字段
    /// </summary>
    public string SortBy { get; set; } = "UsageCount";
    
    /// <summary>
    /// 是否降序
    /// </summary>
    public bool Descending { get; set; } = true;
}
