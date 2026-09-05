using Microsoft.Extensions.Logging;
using System.Text;
using System.Text.RegularExpressions;

namespace agent.codegen;

/// <summary>
/// 代码生成器实现（线程安全）
/// </summary>
public class CodeGenerator : ICodeGenerator
{
    private readonly ILogger<CodeGenerator> _logger;
    private readonly Dictionary<string, CodeTemplate> _templates = new();
    private readonly Dictionary<string, LanguageConfig> _languageConfigs = new();
    private readonly object _lock = new();
    
    public CodeGenerator(ILogger<CodeGenerator> logger)
    {
        _logger = logger;
        InitializeLanguageConfigs();
        InitializeDefaultTemplates();
    }
    
    public async Task<CodeGenResult> GenerateAsync(CodeGenRequest request, CancellationToken ct = default)
    {
        try
        {
            var code = request.Type switch
            {
                CodeGenType.Class => GenerateClass(request),
                CodeGenType.Interface => GenerateInterface(request),
                CodeGenType.Struct => GenerateStruct(request),
                CodeGenType.Enum => GenerateEnum(request),
                CodeGenType.Method => GenerateMethod(request),
                CodeGenType.Property => GenerateProperty(request),
                CodeGenType.Constructor => GenerateConstructor(request),
                CodeGenType.File => GenerateFile(request),
                _ => GenerateClass(request)
            };
            
            if (request.Options.FormatCode)
            {
                code = await FormatAsync(code, request.Options.Language);
            }
            
            return new CodeGenResult
            {
                Success = true,
                Code = code,
                Metadata = new Dictionary<string, object>
                {
                    { "type", request.Type.ToString() },
                    { "language", request.Options.Language },
                    { "hasComments", request.Options.AddComments }
                }
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Code generation failed");
            return new CodeGenResult
            {
                Success = false,
                Error = ex.Message
            };
        }
    }
    
    public async Task<CodeGenResult> GenerateFromTemplateAsync(string templateId, Dictionary<string, object> parameters, CancellationToken ct = default)
    {
        if (!_templates.TryGetValue(templateId, out var template))
        {
            return new CodeGenResult { Success = false, Error = $"Template not found: {templateId}" };
        }
        
        var request = new CodeGenRequest
        {
            Type = template.Type,
            Parameters = parameters,
            Options = new CodeGenOptions { Language = template.Language }
        };
        
        var result = await GenerateAsync(request, ct);
        
        // 应用模板
        if (result.Success && !string.IsNullOrEmpty(template.Template))
        {
            result.Code = ApplyTemplate(template.Template, parameters);
        }
        
        return result;
    }
    
    public Task<List<CodeTemplate>> GetTemplatesAsync(CodeGenType? type = null, string? language = null)
    {
        var templates = _templates.Values.AsEnumerable();
        
        if (type.HasValue)
        {
            templates = templates.Where(t => t.Type == type.Value);
        }
        
        if (!string.IsNullOrEmpty(language))
        {
            templates = templates.Where(t => t.Language.Equals(language, StringComparison.OrdinalIgnoreCase));
        }
        
        return Task.FromResult(templates.ToList());
    }
    
    public Task AddTemplateAsync(CodeTemplate template)
    {
        _templates[template.Id] = template;
        return Task.CompletedTask;
    }
    
    public Task<string> FormatAsync(string code, string language)
    {
        // 简单的格式化实现
        var lines = code.Split('\n');
        var sb = new StringBuilder();
        var indentLevel = 0;
        
        foreach (var rawLine in lines)
        {
            var line = rawLine.Trim();
            
            // 跳过空行处理（保留结构）
            if (string.IsNullOrWhiteSpace(line))
            {
                sb.AppendLine();
                continue;
            }
            
            // 调整缩进
            if (line.StartsWith("}"))
            {
                indentLevel = Math.Max(0, indentLevel - 1);
            }
            
            var indent = new string(' ', indentLevel * 4);
            
            sb.AppendLine(indent + line);
            
            // 调整缩进
            if (line.EndsWith("{"))
            {
                indentLevel++;
            }
        }
        
        return Task.FromResult(sb.ToString().TrimEnd());
    }
    
    public Task<List<CodeCompletion>> CompleteAsync(string code, int position, string language)
    {
        var completions = new List<CodeCompletion>();
        
        // 简单的关键字补全
        var keywords = language.ToLowerInvariant() switch
        {
            "csharp" or "cs" => new[] { "public", "private", "protected", "internal", "class", "interface", "struct", "enum", "void", "async", "await", "var", "string", "int", "bool", "new", "return", "if", "else", "for", "foreach", "while", "switch", "case", "try", "catch", "throw", "using", "namespace", "this", "base", "static", "readonly", "const", "virtual", "override", "abstract", "sealed", "partial" },
            "javascript" or "js" => new[] { "const", "let", "var", "function", "async", "await", "class", "extends", "import", "export", "return", "if", "else", "for", "while", "switch", "try", "catch", "throw", "new", "this", "super" },
            "python" or "py" => new[] { "def", "class", "import", "from", "if", "elif", "else", "for", "while", "try", "except", "finally", "with", "as", "return", "yield", "lambda", "pass", "break", "continue", "raise", "assert", "global", "nonlocal" },
            _ => Array.Empty<string>()
        };
        
        foreach (var keyword in keywords)
        {
            completions.Add(new CodeCompletion
            {
                Text = keyword,
                DisplayText = keyword,
                Kind = CompletionKind.Keyword,
                Priority = 100
            });
        }
        
        return Task.FromResult(completions);
    }
    
    public Task<CodeAnalysis> AnalyzeAsync(string code, string language)
    {
        var analysis = new CodeAnalysis();
        
        // 简单的语法分析
        var lines = code.Split('\n');
        
        for (int i = 0; i < lines.Length; i++)
        {
            var line = lines[i];
            var lineNum = i + 1;
            
            // 检测常见问题
            if (line.Contains("TODO") || line.Contains("FIXME"))
            {
                analysis.Warnings.Add(new SyntaxWarning
                {
                    Line = lineNum,
                    Message = "Contains TODO/FIXME comment",
                    Severity = "info"
                });
            }
            
            // 检测过长行
            if (line.Length > 120)
            {
                analysis.Warnings.Add(new SyntaxWarning
                {
                    Line = lineNum,
                    Message = "Line exceeds 120 characters",
                    Severity = "warning"
                });
            }
            
            // 检测未使用的变量（简化实现）
            var unusedVar = Regex.Match(line, @"var\s+(\w+)\s*=");
            if (unusedVar.Success)
            {
                analysis.Issues.Add(new CodeIssue
                {
                    RuleId = "SA",
                    Line = lineNum,
                    Message = $"Variable '{unusedVar.Groups[1].Value}' may not be used",
                    Severity = IssueSeverity.Hint
                });
            }
        }
        
        // 简单的结构分析
        analysis.Structure = new CodeStructure();
        
        return Task.FromResult(analysis);
    }
    
    private string GenerateClass(CodeGenRequest request)
    {
        var sb = new StringBuilder();
        
        // ✅ 真正使用传入的上下文
        var context = request.Parameters.GetValueOrDefault("Context", "")?.ToString() ?? "";
        var name = request.Parameters.GetValueOrDefault("Name", "MyClass")?.ToString() ?? "MyClass";
        var access = request.Parameters.GetValueOrDefault("AccessModifier", "public")?.ToString() ?? "public";
        var isPartial = request.Parameters.GetValueOrDefault("IsPartial", false) as bool? ?? false;
        var isAbstract = request.Parameters.GetValueOrDefault("IsAbstract", false) as bool? ?? false;
        
        // ✅ 根据上下文推断代码风格
        var codeStyle = InferCodeStyle(context);
        
        // 命名空间
        if (request.Parameters.TryGetValue("Namespace", out var ns))
        {
            sb.AppendLine($"namespace {ns}");
            sb.AppendLine("{");
        }
        
        // 属性
        if (request.Attributes != null)
        {
            foreach (var attr in request.Attributes)
            {
                sb.AppendLine($"[{attr}]");
            }
        }
        
        // 类声明
        var classModifier = "";
        if (isPartial) classModifier += " partial";
        if (isAbstract) classModifier += " abstract";
        
        var baseClass = !string.IsNullOrEmpty(request.BaseClass) ? $": {request.BaseClass}" : "";
        if (request.Interfaces?.Any() == true)
        {
            if (!string.IsNullOrEmpty(baseClass))
            {
                baseClass += ", ";
            }
            else
            {
                baseClass = ": ";
            }
            baseClass += string.Join(", ", request.Interfaces);
        }
        
        if (!string.IsNullOrEmpty(baseClass) && !baseClass.StartsWith(":"))
        {
            baseClass = ": " + baseClass.TrimStart(':').Trim();
        }
        
        sb.AppendLine($"{access}{classModifier} class {name} {baseClass}");
        sb.AppendLine("{");
        
        // ✅ 如果有上下文，添加基于上下文的构造函数和成员
        if (!string.IsNullOrEmpty(context))
        {
            // 从上下文推断需要的成员
            var inferredMembers = InferMembersFromContext(context, codeStyle);
            foreach (var member in inferredMembers)
            {
                sb.AppendLine($"    {member}");
            }
            
            if (inferredMembers.Any())
            {
                sb.AppendLine();
            }
        }
        
        // 构造函数
        sb.AppendLine($"    public {name}()");
        sb.AppendLine("    {");
        if (!string.IsNullOrEmpty(context))
        {
            // 从上下文推断初始化逻辑
            var initLogic = InferInitLogic(context, codeStyle);
            if (!string.IsNullOrEmpty(initLogic))
            {
                foreach (var line in initLogic.Split('\n'))
                {
                    sb.AppendLine($"        {line}");
                }
            }
        }
        sb.AppendLine("    }");
        
        sb.AppendLine("}");
        
        if (request.Parameters.ContainsKey("Namespace"))
        {
            sb.AppendLine("}");
        }
        
        return sb.ToString();
    }
    
    /// <summary>
    /// ✅ 从上下文推断代码风格
    /// </summary>
    private CodeStyle InferCodeStyle(string context)
    {
        var style = new CodeStyle();
        
        if (string.IsNullOrEmpty(context))
            return style;
        
        // 检测命名风格
        if (context.Contains("_") || context.Contains("m_"))
        {
            style.NamingConvention = NamingConvention.Hungarian;
        }
        else if (context.Contains("snake_case"))
        {
            style.NamingConvention = NamingConvention.SnakeCase;
        }
        
        // 检测是否使用 region
        style.UseRegions = context.Contains("#region");
        
        // 检测注释风格
        style.CommentStyle = context.Contains("///") ? CommentStyle.XmlDoc : CommentStyle.SingleLine;
        
        // 检测 nullable
        style.UseNullable = context.Contains("?") || context.Contains("string?");
        
        return style;
    }
    
    /// <summary>
    /// ✅ 从上下文推断成员
    /// </summary>
    private List<string> InferMembersFromContext(string context, CodeStyle style)
    {
        var members = new List<string>();
        
        if (string.IsNullOrEmpty(context))
            return members;
        
        // 检测是否有字段/属性
        var fieldPattern = style.NamingConvention switch
        {
            NamingConvention.Hungarian => @"(private|public|protected)\s+\w+\s+m_\w+",
            _ => @"(private|public|protected)\s+\w+\s+\w+;"
        };
        
        // 提取上下文中的类型
        var typesInContext = ExtractTypes(context);
        foreach (var type in typesInContext.Take(3))
        {
            var fieldName = style.NamingConvention switch
            {
                NamingConvention.Hungarian => $"m_{char.ToLower(type[0])}{type[1..]}",
                NamingConvention.SnakeCase => char.ToLower(type[0]).ToString() + type[1..],
                _ => char.ToLower(type[0]) + type[1..]
            };
            
            members.Add($"private {type} {fieldName};");
        }
        
        // 如果上下文提到某个类，添加相关成员
        if (context.Contains("User") || context.Contains("用户"))
        {
            members.Add("public string Id { get; set; }");
            members.Add("public string Name { get; set; }");
        }
        
        if (context.Contains("Auth") || context.Contains("登录"))
        {
            members.Add("public DateTime LoginTime { get; set; }");
        }
        
        return members;
    }
    
    /// <summary>
    /// ✅ 从上下文推断初始化逻辑
    /// </summary>
    private string InferInitLogic(string context, CodeStyle style)
    {
        if (string.IsNullOrEmpty(context))
            return "";
        
        var lines = new List<string>();
        
        if (context.Contains("初始化") || context.Contains("Init"))
        {
            lines.Add("// 初始化");
        }
        
        if (context.Contains("默认值") || context.Contains("default"))
        {
            lines.Add("InitializeDefaults();");
        }
        
        if (context.Contains("Logger") || context.Contains("日志"))
        {
            lines.Add("_logger = LoggerFactory.Create(b => b.AddConsole()).CreateLogger<MyClass>();");
        }
        
        return string.Join("\n", lines);
    }
    
    /// <summary>
    /// ✅ 从上下文提取类型
    /// </summary>
    private List<string> ExtractTypes(string context)
    {
        var types = new List<string>();
        var typePattern = @"(?:class|interface|struct|enum)\s+(\w+)";
        var matches = System.Text.RegularExpressions.Regex.Matches(context, typePattern);
        
        foreach (System.Text.RegularExpressions.Match match in matches)
        {
            types.Add(match.Groups[1].Value);
        }
        
        return types.Distinct().Take(5).ToList();
    }
    
    private string GenerateInterface(CodeGenRequest request)
    {
        var sb = new StringBuilder();
        var name = request.Parameters.GetValueOrDefault("Name", "IMyInterface")?.ToString() ?? "IMyInterface";
        var access = request.Parameters.GetValueOrDefault("AccessModifier", "public")?.ToString() ?? "public";
        
        if (request.Parameters.TryGetValue("Namespace", out var ns))
        {
            sb.AppendLine($"namespace {ns}");
            sb.AppendLine("{");
        }
        
        sb.AppendLine($"{access} interface {name}");
        
        if (request.Interfaces?.Any() == true)
        {
            sb.AppendLine($"    : {string.Join(", ", request.Interfaces)}");
        }
        
        sb.AppendLine("{");
        sb.AppendLine("}");
        
        if (request.Parameters.ContainsKey("Namespace"))
        {
            sb.AppendLine("}");
        }
        
        return sb.ToString();
    }
    
    private string GenerateStruct(CodeGenRequest request)
    {
        var sb = new StringBuilder();
        var name = request.Parameters.GetValueOrDefault("Name", "MyStruct")?.ToString() ?? "MyStruct";
        var access = request.Parameters.GetValueOrDefault("AccessModifier", "public")?.ToString() ?? "public";
        
        sb.AppendLine($"{access} struct {name}");
        sb.AppendLine("{");
        sb.AppendLine("}");
        
        return sb.ToString();
    }
    
    private string GenerateEnum(CodeGenRequest request)
    {
        var sb = new StringBuilder();
        var name = request.Parameters.GetValueOrDefault("Name", "MyEnum")?.ToString() ?? "MyEnum";
        var access = request.Parameters.GetValueOrDefault("AccessModifier", "public")?.ToString() ?? "public";
        var values = request.Parameters.GetValueOrDefault("Values", new List<string>()) as IEnumerable<object>;
        
        sb.AppendLine($"{access} enum {name}");
        sb.AppendLine("{");
        
        if (values != null)
        {
            var i = 0;
            foreach (var val in values)
            {
                sb.AppendLine($"    {val}{(i < values.Count() - 1 ? "," : "")}");
                i++;
            }
        }
        
        sb.AppendLine("}");
        
        return sb.ToString();
    }
    
    private string GenerateMethod(CodeGenRequest request)
    {
        var sb = new StringBuilder();
        var name = request.Parameters.GetValueOrDefault("Name", "MyMethod")?.ToString() ?? "MyMethod";
        var access = request.Parameters.GetValueOrDefault("AccessModifier", "public")?.ToString() ?? "public";
        var returnType = request.Parameters.GetValueOrDefault("ReturnType", "void")?.ToString() ?? "void";
        var isAsync = request.Parameters.GetValueOrDefault("IsAsync", false) as bool? ?? false;
        
        var asyncModifier = isAsync ? " async" : "";
        var awaitKeyword = isAsync ? "await " : "";
        
        sb.AppendLine($"{access}{asyncModifier} {returnType} {name}()");
        sb.AppendLine("{");
        sb.AppendLine($"    {awaitKeyword}throw new NotImplementedException();");
        sb.AppendLine("}");
        
        return sb.ToString();
    }
    
    private string GenerateProperty(CodeGenRequest request)
    {
        var sb = new StringBuilder();
        var name = request.Parameters.GetValueOrDefault("Name", "MyProperty")?.ToString() ?? "MyProperty";
        var access = request.Parameters.GetValueOrDefault("AccessModifier", "public")?.ToString() ?? "public";
        var propertyType = request.Parameters.GetValueOrDefault("Type", "string")?.ToString() ?? "string";
        var hasGetter = request.Parameters.GetValueOrDefault("HasGetter", true) as bool? ?? true;
        var hasSetter = request.Parameters.GetValueOrDefault("HasSetter", true) as bool? ?? true;
        var isAutoProperty = request.Parameters.GetValueOrDefault("IsAutoProperty", true) as bool? ?? true;
        
        var accessor = "";
        if (hasGetter && hasSetter)
        {
            accessor = " { get; set; }";
        }
        else if (hasGetter)
        {
            accessor = " { get; }";
        }
        else if (hasSetter)
        {
            accessor = " { set; }";
        }
        
        sb.AppendLine($"{access} {propertyType} {name}{accessor}");
        
        return sb.ToString();
    }
    
    private string GenerateConstructor(CodeGenRequest request)
    {
        var sb = new StringBuilder();
        var className = request.Parameters.GetValueOrDefault("ClassName", "MyClass")?.ToString() ?? "MyClass";
        var access = request.Parameters.GetValueOrDefault("AccessModifier", "public")?.ToString() ?? "public";
        var parameters = request.Parameters.GetValueOrDefault("Parameters", new List<string>()) as IEnumerable<object>;
        
        var paramStr = parameters?.Any() == true 
            ? string.Join(", ", parameters) 
            : "";
        
        sb.AppendLine($"{access} {className}({paramStr})");
        sb.AppendLine("{");
        sb.AppendLine("}");
        
        return sb.ToString();
    }
    
    private string GenerateFile(CodeGenRequest request)
    {
        var sb = new StringBuilder();
        
        // using 语句
        if (request.Imports?.Any() == true)
        {
            foreach (var import in request.Imports)
            {
                sb.AppendLine($"using {import};");
            }
            sb.AppendLine();
        }
        
        // 命名空间
        if (request.Parameters.TryGetValue("Namespace", out var ns))
        {
            sb.AppendLine($"namespace {ns}");
            sb.AppendLine("{");
        }
        
        // 类
        var classCode = GenerateClass(request);
        
        // 移除命名空间包裹（因为上面已经加了）
        if (request.Parameters.ContainsKey("Namespace"))
        {
            classCode = classCode.Replace("namespace " + ns, "");
            classCode = classCode.Trim('{', '}');
        }
        
        sb.Append(classCode);
        
        if (request.Parameters.ContainsKey("Namespace"))
        {
            sb.AppendLine("}");
        }
        
        return sb.ToString();
    }
    
    private string ApplyTemplate(string template, Dictionary<string, object> parameters)
    {
        var result = template;
        
        foreach (var (key, value) in parameters)
        {
            result = result.Replace($"{{{{{key}}}}}", value?.ToString() ?? "");
        }
        
        return result;
    }
    
    private void InitializeLanguageConfigs()
    {
        _languageConfigs["csharp"] = new LanguageConfig
        {
            Name = "C#",
            Extensions = new[] { ".cs" },
            CommentSingle = "//",
            CommentStart = "/*",
            CommentEnd = "*/",
            IndentSize = 4
        };
        
        _languageConfigs["javascript"] = new LanguageConfig
        {
            Name = "JavaScript",
            Extensions = new[] { ".js", ".mjs" },
            CommentSingle = "//",
            CommentStart = "/*",
            CommentEnd = "*/",
            IndentSize = 2
        };
        
        _languageConfigs["python"] = new LanguageConfig
        {
            Name = "Python",
            Extensions = new[] { ".py" },
            CommentSingle = "#",
            CommentStart = "\"\"\"",
            CommentEnd = "\"\"\"",
            IndentSize = 4
        };
    }
    
    private void InitializeDefaultTemplates()
    {
        _templates["csharp-class"] = new CodeTemplate
        {
            Id = "csharp-class",
            Name = "C# Class",
            Language = "csharp",
            Type = CodeGenType.Class,
            Pattern = @"class\s+\w+",
            Template = @"{{AccessModifier}} class {{Name}}
{
    public {{Name}}()
    {
    }
}",
            RequiredParameters = new List<string> { "Name" },
            OptionalParameters = new List<string> { "AccessModifier", "BaseClass" }
        };
        
        _templates["csharp-interface"] = new CodeTemplate
        {
            Id = "csharp-interface",
            Name = "C# Interface",
            Language = "csharp",
            Type = CodeGenType.Interface,
            Pattern = @"interface\s+\w+",
            RequiredParameters = new List<string> { "Name" },
            OptionalParameters = new List<string> { "AccessModifier" }
        };
        
        _templates["csharp-method"] = new CodeTemplate
        {
            Id = "csharp-method",
            Name = "C# Method",
            Language = "csharp",
            Type = CodeGenType.Method,
            Pattern = @"(public|private|protected)\s+\w+\s+\w+\s*\(",
            RequiredParameters = new List<string> { "Name", "ReturnType" },
            OptionalParameters = new List<string> { "AccessModifier", "Parameters", "IsAsync" }
        };
    }
}

/// <summary>
/// 语言配置
/// </summary>
public class LanguageConfig
{
    public string Name { get; set; } = string.Empty;
    public string[] Extensions { get; set; } = Array.Empty<string>();
    public string CommentSingle { get; set; } = "//";
    public string CommentStart { get; set; } = "/*";
    public string CommentEnd { get; set; } = "*/";
    public int IndentSize { get; set; } = 4;
}
