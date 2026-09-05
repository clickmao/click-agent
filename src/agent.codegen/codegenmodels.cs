using Microsoft.Extensions.Logging;

namespace agent.codegen;

/// <summary>
/// 代码生成选项
/// </summary>
public class CodeGenOptions
{
    public string Language { get; set; } = "csharp";
    public bool AddComments { get; set; } = true;
    public bool FormatCode { get; set; } = true;
    public string NamingConvention { get; set; } = "PascalCase";
    public bool GenerateTests { get; set; } = false;
    public int MaxLineLength { get; set; } = 120;
}

/// <summary>
/// 代码生成请求
/// </summary>
public class CodeGenRequest
{
    public string Description { get; set; } = string.Empty;
    public CodeGenType Type { get; set; } = CodeGenType.Class;
    public string? TemplateName { get; set; }
    public Dictionary<string, object> Parameters { get; set; } = new();
    public CodeGenOptions Options { get; set; } = new();
    public List<string>? Imports { get; set; }
    public string? BaseClass { get; set; }
    public List<string>? Interfaces { get; set; }
    public List<string>? Attributes { get; set; }
}

/// <summary>
/// 代码生成类型
/// </summary>
public enum CodeGenType
{
    Class,
    Interface,
    Struct,
    Enum,
    Record,
    Method,
    Property,
    Field,
    Constructor,
    File
}

/// <summary>
/// 代码风格（用于上下文感知生成）
/// </summary>
public class CodeStyle
{
    public NamingConvention NamingConvention { get; set; } = NamingConvention.PascalCase;
    public bool UseRegions { get; set; } = false;
    public CommentStyle CommentStyle { get; set; } = CommentStyle.SingleLine;
    public bool UseNullable { get; set; } = true;
}

/// <summary>
/// 命名风格
/// </summary>
public enum NamingConvention
{
    PascalCase,
    CamelCase,
    SnakeCase,
    Hungarian
}

/// <summary>
/// 注释风格
/// </summary>
public enum CommentStyle
{
    SingleLine,
    XmlDoc,
    Block
}

/// <summary>
/// 代码生成结果
/// </summary>
public class CodeGenResult
{
    public bool Success { get; set; }
    public string? Code { get; set; }
    public string? Error { get; set; }
    public string? FilePath { get; set; }
    public List<CodeChange> Changes { get; set; } = new();
    public Dictionary<string, object> Metadata { get; set; } = new();
}

/// <summary>
/// 代码变更
/// </summary>
public class CodeChange
{
    public string FilePath { get; set; } = string.Empty;
    public ChangeType Type { get; set; }
    public string? OldContent { get; set; }
    public string? NewContent { get; set; }
    public int OldLineStart { get; set; }
    public int OldLineEnd { get; set; }
    public int NewLineStart { get; set; }
    public int NewLineEnd { get; set; }
    public string? Description { get; set; }
}

/// <summary>
/// 变更类型
/// </summary>
public enum ChangeType
{
    Created,
    Modified,
    Deleted,
    Renamed
}

/// <summary>
/// 代码模板
/// </summary>
public class CodeTemplate
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Name { get; set; } = string.Empty;
    public string Language { get; set; } = string.Empty;
    public CodeGenType Type { get; set; }
    public string Pattern { get; set; } = string.Empty;
    public string Template { get; set; } = string.Empty;
    public List<string> RequiredParameters { get; set; } = new();
    public List<string> OptionalParameters { get; set; } = new();
    public string? Description { get; set; }
    public int UsageCount { get; set; }
}

/// <summary>
/// 代码片段
/// </summary>
public class CodeSnippet
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Code { get; set; } = string.Empty;
    public string Language { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public List<string> Tags { get; set; } = new();
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public string? FilePath { get; set; }
    public int? StartLine { get; set; }
    public int? EndLine { get; set; }
}

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

/// <summary>
/// 代码补全
/// </summary>
public class CodeCompletion
{
    public string Text { get; set; } = string.Empty;
    public string DisplayText { get; set; } = string.Empty;
    public CompletionKind Kind { get; set; }
    public string? Documentation { get; set; }
    public int Priority { get; set; }
    public string? InsertText { get; set; }
    public string? Snippet { get; set; }
}

/// <summary>
/// 补全类型
/// </summary>
public enum CompletionKind
{
    Keyword,
    Class,
    Interface,
    Method,
    Property,
    Field,
    Variable,
    Function,
    Snippet,
    Module,
    Constant,
    Type
}

/// <summary>
/// 代码分析结果
/// </summary>
public class CodeAnalysis
{
    public List<SyntaxError> Errors { get; set; } = new();
    public List<SyntaxWarning> Warnings { get; set; } = new();
    public List<CodeIssue> Issues { get; set; } = new();
    public CodeStructure? Structure { get; set; }
    public List<Symbol> Symbols { get; set; } = new();
    public Dictionary<string, object> Metrics { get; set; } = new();
}

/// <summary>
/// 语法错误
/// </summary>
public class SyntaxError
{
    public int Line { get; set; }
    public int Column { get; set; }
    public string Message { get; set; } = string.Empty;
    public string Severity { get; set; } = "error";
    public string? Code { get; set; }
}

/// <summary>
/// 语法警告
/// </summary>
public class SyntaxWarning
{
    public int Line { get; set; }
    public int Column { get; set; }
    public string Message { get; set; } = string.Empty;
    public string Severity { get; set; } = "warning";
    public string? Code { get; set; }
}

/// <summary>
/// 代码问题
/// </summary>
public class CodeIssue
{
    public string RuleId { get; set; } = string.Empty;
    public int Line { get; set; }
    public int Column { get; set; }
    public string Message { get; set; } = string.Empty;
    public IssueSeverity Severity { get; set; }
    public string? Suggestion { get; set; }
}

/// <summary>
/// 问题严重性
/// </summary>
public enum IssueSeverity
{
    Hint,
    Info,
    Warning,
    Error
}

/// <summary>
/// 代码结构
/// </summary>
public class CodeStructure
{
    public List<CodeMember> Members { get; set; } = new();
    public List<string> Usings { get; set; } = new();
    public string? Namespace { get; set; }
    public string? ClassName { get; set; }
    public List<string> BaseTypes { get; set; } = new();
}

/// <summary>
/// 代码成员
/// </summary>
public class CodeMember
{
    public string Name { get; set; } = string.Empty;
    public MemberKind Kind { get; set; }
    public int Line { get; set; }
    public int EndLine { get; set; }
    public string? AccessModifier { get; set; }
    public string? ReturnType { get; set; }
    public List<CodeMember> Children { get; set; } = new();
}

/// <summary>
/// 成员类型
/// </summary>
public enum MemberKind
{
    Class,
    Interface,
    Struct,
    Enum,
    Method,
    Property,
    Field,
    Constructor,
    Destructor,
    Event,
    Indexer
}

/// <summary>
/// 符号
/// </summary>
public class Symbol
{
    public string Name { get; set; } = string.Empty;
    public SymbolKind Kind { get; set; }
    public string? Type { get; set; }
    public int Line { get; set; }
    public string? Definition { get; set; }
}

/// <summary>
/// 符号类型
/// </summary>
public enum SymbolKind
{
    Namespace,
    Class,
    Interface,
    Struct,
    Enum,
    Method,
    Property,
    Field,
    Variable,
    Parameter,
    TypeParameter
}
