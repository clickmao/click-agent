using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;


/// <summary>
/// 上下文验证器
/// </summary>
public interface IContextValidator
{
    /// <summary>
    /// 验证片段
    /// </summary>
    ValidationResult ValidateSnippet(ContextSnippet snippet);
    
    /// <summary>
    /// 验证组装请求
    /// </summary>
    ValidationResult ValidateRequest(ContextAssemblyRequest request);
    
    /// <summary>
    /// 验证组装结果
    /// </summary>
    ValidationResult ValidateResult(ContextAssemblyResult result);
}
