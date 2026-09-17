using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 代码生成器接口
/// </summary>
public interface ICodeGenerator
{
    /// <summary>
    /// 生成代码
    /// </summary>
    Task<CodeGenResult> GenerateAsync(CodeGenRequest request, CancellationToken ct = default);
    
    /// <summary>
    /// 从模板生成
    /// </summary>
    Task<CodeGenResult> GenerateFromTemplateAsync(string templateId, Dictionary<string, object> parameters, CancellationToken ct = default);
    
    /// <summary>
    /// 获取支持的模板
    /// </summary>
    Task<List<CodeTemplate>> GetTemplatesAsync(CodeGenType? type = null, string? language = null);
    
    /// <summary>
    /// 添加模板
    /// </summary>
    Task AddTemplateAsync(CodeTemplate template);
    
    /// <summary>
    /// 格式化代码
    /// </summary>
    Task<string> FormatAsync(string code, string language);
    
    /// <summary>
    /// 补全代码
    /// </summary>
    Task<List<CodeCompletion>> CompleteAsync(string code, int position, string language);
    
    /// <summary>
    /// 分析代码
    /// </summary>
    Task<CodeAnalysis> AnalyzeAsync(string code, string language);
}
