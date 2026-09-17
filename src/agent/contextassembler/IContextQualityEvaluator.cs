using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;


/// <summary>
/// 上下文质量评估器
/// </summary>
public interface IContextQualityEvaluator
{
    /// <summary>
    /// 评估上下文片段质量
    /// </summary>
    Task<ContextQualityScore> EvaluateAsync(ContextSnippet snippet, CancellationToken ct = default);
    
    /// <summary>
    /// 评估组装结果质量
    /// </summary>
    Task<AssemblyQualityReport> EvaluateAssemblyAsync(ContextAssemblyResult result, CancellationToken ct = default);
}
