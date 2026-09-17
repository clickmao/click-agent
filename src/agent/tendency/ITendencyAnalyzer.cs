namespace agent.tendency;


/// <summary>
/// 倾向分析器接口
/// </summary>
public interface ITendencyAnalyzer
{
    /// <summary>
    /// 分析用户倾向
    /// </summary>
    Task<TendencyProfile> AnalyzeUserTendencyAsync(string userId);
    
    /// <summary>
    /// 更新倾向数据
    /// </summary>
    Task UpdateTendencyAsync(string userId, TendencyData data);
    
    /// <summary>
    /// 获取上下文偏见
    /// </summary>
    Task<ContextBias> GetContextBiasAsync(string userId, string context);
}
