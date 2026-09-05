namespace agent.templates;

/// <summary>
/// 模板存储接口
/// </summary>
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
    /// 获取所有分类
    /// </summary>
    Task<IEnumerable<string>> GetCategoriesAsync();
    
    /// <summary>
    /// 应用模板生成内容
    /// </summary>
    Task<string> ApplyTemplateAsync(Template template, ApplyContext context);
    
    /// <summary>
    /// 添加正确示例
    /// </summary>
    Task AddCorrectExampleAsync(string templateId, CorrectExample example);
    
    /// <summary>
    /// 添加错误示例
    /// </summary>
    Task AddIncorrectExampleAsync(string templateId, IncorrectExample example);
    
    /// <summary>
    /// 记录模板使用
    /// </summary>
    Task RecordUsageAsync(string templateId, bool success);
    
    /// <summary>
    /// 获取热门模板
    /// </summary>
    Task<IEnumerable<Template>> GetPopularAsync(int count);
    
    /// <summary>
    /// 获取推荐模板
    /// </summary>
    Task<IEnumerable<Template>> GetRecommendedAsync(string? category, int count = 5);
}

/// <summary>
/// 模板匹配器接口
/// </summary>
public interface ITemplateMatcher
{
    /// <summary>
    /// 匹配模板
    /// </summary>
    Task<TemplateMatchResult?> MatchAsync(string input);
    
    /// <summary>
    /// 获取候选模板
    /// </summary>
    Task<IEnumerable<Template>> GetCandidatesAsync(string input, int topN = 5);
    
    /// <summary>
    /// 计算相似度
    /// </summary>
    Task<double> CalculateSimilarityAsync(string input, string templatePattern);
    
    /// <summary>
    /// 批量匹配
    /// </summary>
    Task<IEnumerable<TemplateMatchResult>> BatchMatchAsync(IEnumerable<string> inputs);
}
