using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;


/// <summary>
/// 上下文组装器接口
/// </summary>
public interface IContextAssembler
{
    /// <summary>
    /// 组装多数据源上下文
    /// </summary>
    /// <param name="request">组装请求</param>
    /// <param name="ct">取消令牌</param>
    /// <returns>组装结果</returns>
    Task<ContextAssemblyResult> AssembleAsync(ContextAssemblyRequest request, CancellationToken ct = default);
    
    /// <summary>
    /// 异步组装（带进度报告）
    /// </summary>
    IAsyncEnumerable<ContextSnippet> AssembleWithProgressAsync(
        ContextAssemblyRequest request, 
        CancellationToken ct = default);
    
    /// <summary>
    /// 快速获取上下文摘要（用于预览）
    /// </summary>
    Task<ContextSummary> GetQuickSummaryAsync(
        string userMessage, 
        string sessionId, 
        int maxSnippets = 5);
    
    /// <summary>
    /// 失效特定上下文
    /// </summary>
    Task InvalidateAsync(string snippetId);
    
    /// <summary>
    /// 获取组装器统计信息
    /// </summary>
    ContextAssemblerStats GetStats();
}
