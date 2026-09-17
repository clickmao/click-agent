namespace agent.userinteraction;


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
