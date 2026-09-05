using Microsoft.Extensions.Logging;
using agent.core;
using agent.workspace;
using agent.codegen;
using agent.planner;
using agent.recovery;
using agent.vectormemory;
using agent.memory;
using agent.templates;
using agent.search;
using agent.subagent;
using agent.session;
using agent.userinteraction;
using agent.context;
using agent.rag;
using agent.tendency;
using agent.tokencompression;

namespace agent;

/// <summary>
/// 工业级Agent - 集成多数据源上下文注入
/// 
/// 改进点：
/// 1. ContextAssembler 统一管理多数据源召回
/// 2. PromptHeader 自动组装到请求中
/// 3. Token 压缩和配额管理
/// 4. 上下文优先级和相关性过滤
/// </summary>
public class IndustrialAgent : AgentBase
{
    private readonly IWorkspace _workspace;
    private readonly ICodeGenerator _codeGenerator;
    private readonly ITaskPlanner _taskPlanner;
    private readonly IRecoverySystem _recoverySystem;
    private readonly IVectorStore _vectorStore;
    private readonly IVectorMemoryRecall _memoryRecall;
    private readonly ITemplateStore _templateStore;
    private readonly ISearchService _searchService;
    private readonly ISubAgentPool _subAgentPool;
    private readonly ISessionManager _sessionManager;
    private readonly IUserInteraction _userInteraction;
    
    // ✅ 新增：ContextAssembler（多数据源上下文组装）
    private readonly IContextAssembler _contextAssembler;
    private readonly ITendencyAnalyzer _tendencyAnalyzer;
    private readonly ITokenCompressor _tokenCompressor;
    
    private readonly List<string> _capabilities = new();
    
    // ✅ 配置选项
    private readonly int _maxTokenBudget;
    private readonly bool _enableWebSearch;
    private readonly bool _enableUserTendency;
    
    public IndustrialAgent(
        ILogger<IndustrialAgent> logger,
        IEnumerable<IMessageHandler> handlers,
        IWorkspace workspace,
        ICodeGenerator codeGenerator,
        ITaskPlanner taskPlanner,
        IRecoverySystem recoverySystem,
        IVectorStore vectorStore,
        IVectorMemoryRecall memoryRecall,
        ITemplateStore templateStore,
        ISearchService searchService,
        ISubAgentPool subAgentPool,
        ISessionManager sessionManager,
        IUserInteraction userInteraction,
        IContextAssembler contextAssembler,
        ITendencyAnalyzer tendencyAnalyzer,
        ITokenCompressor tokenCompressor) : base(logger, handlers)
    {
        _workspace = workspace;
        _codeGenerator = codeGenerator;
        _taskPlanner = taskPlanner;
        _recoverySystem = recoverySystem;
        _vectorStore = vectorStore;
        _memoryRecall = memoryRecall;
        _templateStore = templateStore;
        _searchService = searchService;
        _subAgentPool = subAgentPool;
        _sessionManager = sessionManager;
        _userInteraction = userInteraction;
        
        // ✅ 注入新组件
        _contextAssembler = contextAssembler;
        _tendencyAnalyzer = tendencyAnalyzer;
        _tokenCompressor = tokenCompressor;
        
        Name = "IndustrialAgent";
        _maxTokenBudget = 8000;
        _enableWebSearch = true;
        _enableUserTendency = true;
        
        InitializeCapabilities();
    }
    
    private void InitializeCapabilities()
    {
        _capabilities.AddRange(new[]
        {
            "代码生成", "代码修改", "代码格式化",
            "文件操作", "Git集成", "工作区管理",
            "任务规划", "任务执行", "依赖分析",
            "错误恢复", "自动重试", "回滚管理",
            "语义搜索", "记忆召回", "模板匹配",
            "网络搜索", "代码审查", "测试生成",
            "多数据源上下文注入", "智能上下文压缩"
        });
    }
    
    protected override async Task<AgentResponse> OnProcessAsync(Message message, CancellationToken ct)
    {
        var startTime = DateTime.UtcNow;
        var response = new AgentResponse();
        
        try
        {
            // ✅ 1. 意图识别
            var intent = await RecognizeIntentAsync(message.Content, ct);
            _logger.LogInformation("Intent recognized: {Intent}", intent);
            
            // ✅ 2. 多数据源上下文组装（核心改进）
            var contextResult = await AssembleContextAsync(message, intent, ct);
            
            if (!contextResult.Success)
            {
                _logger.LogWarning("Context assembly failed: {Error}", contextResult.Error);
            }
            
            // ✅ 3. 将上下文注入到消息元数据（供 Handler 使用）
            message.Metadata["ContextSnippets"] = contextResult.Snippets;
            message.Metadata["PromptHeader"] = contextResult.PromptHeader;
            message.Metadata["ContextTokens"] = contextResult.TotalTokens;
            message.Metadata["ContextAssemblyTimeMs"] = contextResult.AssemblyTimeMs;
            
            // ✅ 4. 根据意图路由（现在 Handler 可以访问上下文）
            response = intent switch
            {
                "code_generation" => await HandleCodeGenerationAsync(message, contextResult, ct),
                "code_modification" => await HandleCodeModificationAsync(message, contextResult, ct),
                "task_planning" => await HandleTaskPlanningAsync(message, contextResult, ct),
                "file_operation" => await HandleFileOperationAsync(message, contextResult, ct),
                "git_operation" => await HandleGitOperationAsync(message, contextResult, ct),
                "search" => await HandleSearchAsync(message, contextResult, ct),
                "code_review" => await HandleCodeReviewAsync(message, contextResult, ct),
                "test_generation" => await HandleTestGenerationAsync(message, contextResult, ct),
                "memory_search" => await HandleMemorySearchAsync(message, contextResult, ct),
                "template_matching" => await HandleTemplateMatchingAsync(message, contextResult, ct),
                _ => await HandleGeneralAsync(message, contextResult, ct)
            };
            
            // ✅ 5. 存储到记忆（使用 RAG）
            await StoreToMemoryAsync(message, response, intent, ct);
            
            // ✅ 6. 记录上下文组装统计
            response.Data ??= new Dictionary<string, object>();
            response.Data["ContextStats"] = new ContextStats
            {
                TotalSnippets = contextResult.Snippets.Count,
                TotalTokens = contextResult.TotalTokens,
                AssemblyTimeMs = contextResult.AssemblyTimeMs,
                TokenBudgetUsage = contextResult.TokenBudgetUsage
            };
            
            response.Success = true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing message");
            
            var errorInfo = await _recoverySystem.RecordErrorAsync(ex);
            var recoveryActions = await _recoverySystem.GetRecoveryActionsAsync(errorInfo.Id);
            var bestAction = recoveryActions.FirstOrDefault();
            
            if (bestAction?.IsAutomatic == true)
            {
                var recoveryResult = await _recoverySystem.ExecuteRecoveryAsync(errorInfo.Id, bestAction);
                if (recoveryResult.Success)
                {
                    response.Success = true;
                    response.Content = "操作已自动恢复并重新执行。";
                }
                else
                {
                    response = AgentResponse.ErrorResponse(ex.Message);
                }
            }
            else
            {
                response = AgentResponse.ErrorResponse(ex.Message);
            }
        }
        
        response.ExecutionTimeMs = (long)(DateTime.UtcNow - startTime).TotalMilliseconds;
        return response;
    }
    
    #region Context Assembly (核心改进)
    
    /// <summary>
    /// ✅ 多数据源上下文组装
    /// </summary>
    private async Task<ContextAssemblyResult> AssembleContextAsync(
        Message message, 
        string intent,
        CancellationToken ct)
    {
        var request = new ContextAssemblyRequest
        {
            UserMessage = message.Content,
            SessionId = message.SessionId,
            UserId = message.SenderId,
            Intent = intent,
            MaxTokenBudget = _maxTokenBudget,
            EnableCompression = true,
            CompressionStrategy = CompressionStrategy.Selective,
            MinRelevanceScore = 0.3,

            
            // 根据意图启用不同的数据源
            EnabledSources = new HashSet<DataSourceType>
            {
                DataSourceType.Memory,
                DataSourceType.Session
            }
        };
        
        // 根据意图添加更多数据源
        if (_enableWebSearch && (intent == "search" || intent == "general"))
        {
            request.EnabledSources.Add(DataSourceType.WebSearch);
        }
        
        if (_enableUserTendency && !string.IsNullOrEmpty(message.SenderId))
        {
            request.EnabledSources.Add(DataSourceType.UserTendency);
        }
        
        // 根据意图调整 Token 配额
        switch (intent)
        {
            case "code_generation":
            case "code_modification":
                request.SourceTokenQuota[DataSourceType.Memory] = 3000;
                request.SourceTokenQuota[DataSourceType.Session] = 2000;
                break;
            case "search":
                request.SourceTokenQuota[DataSourceType.WebSearch] = 3000;
                break;
            case "memory_search":
                request.SourceTokenQuota[DataSourceType.Memory] = 5000;
                break;
        }
        
        var result = await _contextAssembler.AssembleAsync(request, ct);
        
        _logger.LogInformation(
            "Context assembled: {Snippets} snippets, {Tokens} tokens, {Sources} sources in {Time}ms",
            result.Snippets.Count,
            result.TotalTokens,
            result.SourceStats.Count(s => s.Value.SnippetCount > 0),
            result.AssemblyTimeMs);
        
        return result;
    }
    
    #endregion
    
    #region Intent Recognition
    
    private async Task<string> RecognizeIntentAsync(string content, CancellationToken ct)
    {
        var lowerContent = content.ToLowerInvariant();
        
        if (lowerContent.Contains("创建") || lowerContent.Contains("生成") || lowerContent.Contains("写"))
        {
            if (lowerContent.Contains("测试"))
                return "test_generation";
            if (lowerContent.Contains("文件") || lowerContent.Contains("代码"))
                return "code_generation";
        }
        
        if (lowerContent.Contains("修改") || lowerContent.Contains("编辑") || lowerContent.Contains("更新"))
            return "code_modification";
        
        if (lowerContent.Contains("计划") || lowerContent.Contains("任务") || lowerContent.Contains("分解"))
            return "task_planning";
        
        if (lowerContent.Contains("搜索") || lowerContent.Contains("查找"))
            return "search";
        
        if (lowerContent.Contains("审查") || lowerContent.Contains("review"))
            return "code_review";
        
        if (lowerContent.Contains("记忆") || lowerContent.Contains("召回"))
            return "memory_search";
        
        if (lowerContent.Contains("模板"))
            return "template_matching";
        
        if (lowerContent.Contains("git") || lowerContent.Contains("commit"))
            return "git_operation";
        
        if (lowerContent.Contains("文件") || lowerContent.Contains("目录"))
            return "file_operation";
        
        return "general";
    }
    
    #endregion
    
    #region Handlers (重构以接收上下文)
    
    private async Task<AgentResponse> HandleCodeGenerationAsync(
        Message message, 
        ContextAssemblyResult context,
        CancellationToken ct)
    {
        // ✅ 使用上下文中的相关记忆
        var relevantCode = context.Snippets
            .Where(s => s.SourceType == DataSourceType.Memory)
            .FirstOrDefault()?.Content;
        
        var templates = await _templateStore.GetRecommendedAsync("Code", 3);
        var template = templates.FirstOrDefault();
        
        if (template != null)
        {
            var request = new CodeGenRequest
            {
                Description = message.Content,
                Type = CodeGenType.Class,
                Parameters = new Dictionary<string, object>
                {
                    { "Name", "GeneratedClass" },
                    { "Context", relevantCode ?? "" }
                }
            };
            
            var result = await _codeGenerator.GenerateAsync(request, ct);
            
            if (result.Success && !string.IsNullOrEmpty(result.Code))
            {
                var filePath = "GeneratedCode.cs";
                await _workspace.CreateFileAsync(filePath, result.Code, ct);
                
                return new AgentResponse
                {
                    Content = $"代码已生成并保存到 {filePath}\n\n{result.Code}",
                    Success = true,
                    Data = new Dictionary<string, object>
                    {
                        { "filePath", filePath },
                        { "template", template.Name },
                        { "contextUsed", !string.IsNullOrEmpty(relevantCode) }
                    }
                };
            }
        }
        
        return new AgentResponse
        {
            Content = "代码生成功能就绪，请提供更详细的需求。",
            Data = new Dictionary<string, object>
            {
                { "contextHeader", context.PromptHeader }
            }
        };
    }
    
    private async Task<AgentResponse> HandleCodeModificationAsync(
        Message message,
        ContextAssemblyResult context,
        CancellationToken ct)
    {
        var filePath = ExtractFilePath(message.Content);
        
        if (!string.IsNullOrEmpty(filePath))
        {
            var fileResult = await _workspace.ReadFileAsync(filePath, ct);
            
            if (fileResult.Success)
            {
                var analysis = await _codeGenerator.AnalyzeAsync(fileResult.Content!, "csharp");
                
                // ✅ 包含上下文摘要
                var contextSummary = GetContextSummary(context);
                
                return new AgentResponse
                {
                    Content = $"文件 {filePath} 分析完成。\n\n发现问题: {analysis.Errors.Count} 个错误, {analysis.Warnings.Count} 个警告\n\n{contextSummary}",
                    Success = true,
                    Data = new Dictionary<string, object>
                    {
                        { "analysis", analysis },
                        { "contextSnippets", context.Snippets.Count }
                    }
                };
            }
        }
        
        return new AgentResponse { Content = "请指定要修改的文件路径。" };
    }
    
    private async Task<AgentResponse> HandleTaskPlanningAsync(
        Message message,
        ContextAssemblyResult context,
        CancellationToken ct)
    {
        var plan = await _taskPlanner.CreatePlanAsync(message.Content, ct);
        
        var task = new TaskNode
        {
            Name = "Main Task",
            Description = message.Content,
            Priority = TaskPriority.High
        };
        
        await _taskPlanner.AddTaskAsync(plan.Id, task, ct);
        var analysis = await _taskPlanner.AnalyzeDependenciesAsync(plan.Id, ct);
        
        return new AgentResponse
        {
            Content = $"任务计划已创建 (ID: {plan.Id})\n\n根任务: {analysis.RootTasks.Count}\n叶子任务: {analysis.LeafTasks.Count}\n预计时间: {plan.Nodes.Values.Sum(n => n.EstimatedMinutes)} 分钟",
            Success = true,
            Data = new Dictionary<string, object>
            {
                { "planId", plan.Id },
                { "analysis", analysis },
                { "contextUsed", context.Snippets.Count > 0 }
            }
        };
    }
    
    private async Task<AgentResponse> HandleFileOperationAsync(
        Message message,
        ContextAssemblyResult context,
        CancellationToken ct)
    {
        var lowerContent = message.Content.ToLowerInvariant();
        
        if (lowerContent.Contains("列出") || lowerContent.Contains("ls") || lowerContent.Contains("dir"))
        {
            var files = await _workspace.ListDirectoryAsync("", true, ct);
            return new AgentResponse
            {
                Content = $"工作区包含 {files.Count} 个文件:\n\n" + string.Join("\n", files.Take(50)),
                Success = true
            };
        }
        
        if (lowerContent.Contains("读取") || lowerContent.Contains("cat"))
        {
            var filePath = ExtractFilePath(message.Content);
            if (!string.IsNullOrEmpty(filePath))
            {
                var result = await _workspace.ReadFileAsync(filePath, ct);
                return new AgentResponse
                {
                    Content = result.Success ? $"文件内容:\n\n{result.Content}" : $"读取失败: {result.Error}",
                    Success = result.Success
                };
            }
        }
        
        return new AgentResponse { Content = "支持的命令: 列出文件, 读取文件" };
    }
    
    private Task<AgentResponse> HandleGitOperationAsync(
        Message message,
        ContextAssemblyResult context,
        CancellationToken ct)
    {
        return Task.FromResult(new AgentResponse
        {
            Content = "Git集成功能就绪。请使用具体的Git命令（如commit, push, pull等）。"
        });
    }
    
    private async Task<AgentResponse> HandleSearchAsync(
        Message message,
        ContextAssemblyResult context,
        CancellationToken ct)
    {
        var query = message.Content.Replace("搜索", "").Replace("查找", "").Trim();
        
        var results = await _searchService.SearchAsync(query, new SearchOptions { MaxResults = 5 }, ct);
        
        // ✅ 整合上下文中的搜索结果
        var webSnippets = context.Snippets
            .Where(s => s.SourceType == DataSourceType.WebSearch)
            .ToList();
        
        var response = new System.Text.StringBuilder();
        response.AppendLine($"搜索结果:\n");
        response.AppendLine($"{results.Title}");
        response.AppendLine(results.Snippet);
        response.AppendLine($"\nURL: {results.Url}");
        
        if (webSnippets.Any())
        {
            response.AppendLine("\n--- 相关上下文 ---");
            foreach (var snippet in webSnippets.Take(2))
            {
                response.AppendLine($"- {snippet.Content}");
            }
        }
        
        return new AgentResponse
        {
            Content = response.ToString(),
            Success = true,
            Data = new Dictionary<string, object> { { "results", results } }
        };
    }
    
    private async Task<AgentResponse> HandleCodeReviewAsync(
        Message message,
        ContextAssemblyResult context,
        CancellationToken ct)
    {
        var filePath = ExtractFilePath(message.Content);
        
        if (!string.IsNullOrEmpty(filePath))
        {
            var fileResult = await _workspace.ReadFileAsync(filePath, ct);
            
            if (fileResult.Success)
            {
                var analysis = await _codeGenerator.AnalyzeAsync(fileResult.Content!, "csharp");
                
                var report = new System.Text.StringBuilder();
                report.AppendLine("代码审查报告\n");
                report.AppendLine($"文件: {filePath}");
                report.AppendLine($"上下文片段: {context.Snippets.Count}");
                report.AppendLine($"Token使用: {context.TotalTokens}");
                report.AppendLine();
                
                if (analysis.Errors.Any())
                {
                    report.AppendLine("错误:");
                    foreach (var error in analysis.Errors)
                        report.AppendLine($"  - L{error.Line}: {error.Message}");
                }
                
                if (analysis.Warnings.Any())
                {
                    report.AppendLine("\n警告:");
                    foreach (var warning in analysis.Warnings)
                        report.AppendLine($"  - L{warning.Line}: {warning.Message}");
                }
                
                if (analysis.Issues.Any())
                {
                    report.AppendLine("\n建议:");
                    foreach (var issue in analysis.Issues)
                        report.AppendLine($"  - [{issue.Severity}] {issue.Message}");
                }
                
                // ✅ 添加相关上下文
                if (context.Snippets.Any())
                {
                    report.AppendLine("\n--- 相关上下文 ---");
                    foreach (var snippet in context.Snippets.Take(3))
                    {
                        report.AppendLine($"[{snippet.SourceType}] {snippet.Content[..Math.Min(100, snippet.Content.Length)]}...");
                    }
                }
                
                return new AgentResponse { Content = report.ToString(), Success = true };
            }
        }
        
        return new AgentResponse { Content = "请指定要审查的文件路径。" };
    }
    
    private async Task<AgentResponse> HandleTestGenerationAsync(
        Message message,
        ContextAssemblyResult context,
        CancellationToken ct)
    {
        var filePath = ExtractFilePath(message.Content);
        
        if (!string.IsNullOrEmpty(filePath))
        {
            var fileResult = await _workspace.ReadFileAsync(filePath, ct);
            
            if (fileResult.Success)
            {
                var className = Path.GetFileNameWithoutExtension(filePath);
                var content = fileResult.Content!;
                
                // ✅ 从文件内容分析要测试的方法
                var methodsToTest = AnalyzeMethodsForTesting(content);
                
                // ✅ 从上下文获取相关测试模式
                var existingTests = context.Snippets
                    .Where(s => s.SourceType == DataSourceType.Memory && 
                               (s.Content.Contains("Test") || s.Content.Contains("测试")))
                    .SelectMany(s => s.Tags)
                    .Where(t => t.Contains("Test"))
                    .Distinct()
                    .ToList();
                
                // ✅ 生成更有意义的测试
                var testCode = GenerateTestCode(className, methodsToTest, existingTests);
                
                var testFilePath = filePath.Replace(".cs", "Tests.cs");
                await _workspace.CreateFileAsync(testFilePath, testCode, ct);
                
                return new AgentResponse
                {
                    Content = $"测试文件已生成: {testFilePath}\n\n共 {methodsToTest.Count} 个方法已生成测试\n\n{testCode}",
                    Success = true,
                    Data = new Dictionary<string, object>
                    {
                        { "testFilePath", testFilePath },
                        { "methodsTested", methodsToTest.Count },
                        { "contextUsed", existingTests.Any() }
                    }
                };
            }
        }
        
        return new AgentResponse { Content = "请指定要生成测试的源代码文件。" };
    }
    
    /// <summary>
    /// ✅ 分析文件中需要测试的方法
    /// </summary>
    private List<MethodInfo> AnalyzeMethodsForTesting(string content)
    {
        var methods = new List<MethodInfo>();
        
        // 提取 public 方法
        var methodPattern = @"(public|internal)\s+(\w+)\s+(\w+)\s*\([^)]*\)";
        var matches = System.Text.RegularExpressions.Regex.Matches(content, methodPattern);
        
        foreach (System.Text.RegularExpressions.Match match in matches)
        {
            var returnType = match.Groups[2].Value;
            var methodName = match.Groups[3].Value;
            
            // 跳过构造函数和属性
            if (methodName == className(content) || returnType == className(content))
                continue;
            
            // 只保留 public 方法
            if (!match.Groups[1].Value.Contains("public"))
                continue;
            
            methods.Add(new MethodInfo
            {
                Name = methodName,
                ReturnType = returnType,
                IsAsync = content.Contains($"{returnType} {methodName}") && 
                          content.Substring(content.IndexOf(methodName)).Contains("async")
            });
        }
        
        return methods.Take(5).ToList(); // 最多5个方法
    }
    
    /// <summary>
    /// 获取类名
    /// </summary>
    private string className(string content)
    {
        var match = System.Text.RegularExpressions.Regex.Match(content, @"class\s+(\w+)");
        return match.Success ? match.Groups[1].Value : "UnknownClass";
    }
    
    /// <summary>
    /// ✅ 生成测试代码
    /// </summary>
    private string GenerateTestCode(
        string className, 
        List<MethodInfo> methods, 
        List<string> existingTestPatterns)
    {
        var sb = new System.Text.StringBuilder();
        
        sb.AppendLine("using Xunit;");
        sb.AppendLine();
        
        sb.AppendLine($"public class {className}Tests");
        sb.AppendLine("{");
        
        foreach (var method in methods)
        {
            // 生成测试方法名
            var testMethodName = $"Test_{method.Name}";
            
            if (existingTestPatterns.Any())
            {
                // 参考现有测试模式
                testMethodName = existingTestPatterns.First().Replace("Test", $"Test_{method.Name}");
            }
            
            sb.AppendLine($"    [Fact]");
            sb.AppendLine($"    public void {testMethodName}()");
            sb.AppendLine("    {");
            
            // 根据返回类型生成不同的断言
            if (method.ReturnType == "void")
            {
                sb.AppendLine($"        // Arrange");
                sb.AppendLine($"        var sut = new {className}();");
                sb.AppendLine();
                sb.AppendLine($"        // Act");
                sb.AppendLine($"        // TODO: Set up test parameters");
                sb.AppendLine($"        sut.{method.Name}();");
                sb.AppendLine();
                sb.AppendLine($"        // Assert");
                sb.AppendLine($"        // TODO: Verify the result");
            }
            else if (method.ReturnType == "bool")
            {
                sb.AppendLine($"        // Arrange");
                sb.AppendLine($"        var sut = new {className}();");
                sb.AppendLine();
                sb.AppendLine($"        // Act");
                sb.AppendLine($"        var result = sut.{method.Name}();");
                sb.AppendLine();
                sb.AppendLine($"        // Assert");
                sb.AppendLine($"        Assert.True(result); // or Assert.False depending on expected behavior");
            }
            else if (method.ReturnType == "Task" || method.IsAsync)
            {
                sb.AppendLine($"        // Arrange");
                sb.AppendLine($"        var sut = new {className}();");
                sb.AppendLine();
                sb.AppendLine($"        // Act");
                sb.AppendLine($"        var result = sut.{method.Name}().Result;");
                sb.AppendLine();
                sb.AppendLine($"        // Assert");
                sb.AppendLine($"        Assert.NotNull(result);");
            }
            else
            {
                sb.AppendLine($"        // Arrange");
                sb.AppendLine($"        var sut = new {className}();");
                sb.AppendLine();
                sb.AppendLine($"        // Act");
                sb.AppendLine($"        var result = sut.{method.Name}();");
                sb.AppendLine();
                sb.AppendLine($"        // Assert");
                sb.AppendLine($"        Assert.NotNull(result);");
            }
            
            sb.AppendLine("    }");
            sb.AppendLine();
        }
        
        sb.AppendLine("}");
        
        return sb.ToString();
    }
    
    private class MethodInfo
    {
        public string Name { get; set; } = "";
        public string ReturnType { get; set; } = "void";
        public bool IsAsync { get; set; }
    }
    
    private async Task<AgentResponse> HandleMemorySearchAsync(
        Message message,
        ContextAssemblyResult context,
        CancellationToken ct)
    {
        // ✅ 直接使用上下文中的 Memory 片段
        var memorySnippets = context.Snippets
            .Where(s => s.SourceType == DataSourceType.Memory)
            .ToList();
        
        if (!memorySnippets.Any())
        {
            return new AgentResponse { Content = "没有找到相关的记忆。" };
        }
        
        var response = new System.Text.StringBuilder();
        response.AppendLine($"找到 {memorySnippets.Count} 条相关记忆:\n");
        
        foreach (var snippet in memorySnippets)
        {
            var content = snippet.Content.Length > 100 
                ? snippet.Content[..100] + "..." 
                : snippet.Content;
            response.AppendLine($"- [{snippet.CreatedAt:yyyy-MM-dd HH:mm}] {content}");
            response.AppendLine($"  相关度: {snippet.RelevanceScore:P0}");
        }
        
        return new AgentResponse
        {
            Content = response.ToString(),
            Success = true,
            Data = new Dictionary<string, object>
            {
                { "snippetCount", memorySnippets.Count },
                { "totalTokens", context.TotalTokens }
            }
        };
    }
    
    private async Task<AgentResponse> HandleTemplateMatchingAsync(
        Message message,
        ContextAssemblyResult context,
        CancellationToken ct)
    {
        var templates = await _templateStore.QueryAsync(new TemplateQuery
        {
            IsEnabled = true,
            Take = 10
        });
        
        var response = new System.Text.StringBuilder();
        response.AppendLine($"可用模板 ({templates.Count()}):\n");
        
        foreach (var template in templates)
        {
            response.AppendLine($"- [{template.Category}] {template.Name}: {template.Description}");
        }
        
        return new AgentResponse { Content = response.ToString(), Success = true };
    }
    
    private async Task<AgentResponse> HandleGeneralAsync(
        Message message,
        ContextAssemblyResult context,
        CancellationToken ct)
    {
        var response = new System.Text.StringBuilder();
        
        // ✅ 整合上下文内容
        if (context.Snippets.Any())
        {
            response.AppendLine("### 相关上下文\n");
            
            foreach (var group in context.Snippets.GroupBy(s => s.SourceType).Take(3))
            {
                response.AppendLine($"**{group.Key}:**");
                foreach (var snippet in group.Take(2))
                {
                    var content = snippet.Content.Length > 150 
                        ? snippet.Content[..150] + "..." 
                        : snippet.Content;
                    response.AppendLine($"- {content}");
                }
                response.AppendLine();
            }
        }
        
        // 网络搜索结果
        var webSnippets = context.Snippets
            .Where(s => s.SourceType == DataSourceType.WebSearch)
            .ToList();
        
        if (webSnippets.Any())
        {
            response.AppendLine("### 网络搜索\n");
            foreach (var snippet in webSnippets)
            {
                response.AppendLine($"- {snippet.Content}");
            }
        }
        
        // 用户偏好
        var tendencySnippets = context.Snippets
            .Where(s => s.SourceType == DataSourceType.UserTendency)
            .ToList();
        
        if (tendencySnippets.Any())
        {
            response.AppendLine("\n### 个性化建议\n");
            foreach (var snippet in tendencySnippets)
            {
                response.AppendLine(snippet.Content);
            }
        }
        
        if (response.Length == 0)
        {
            response.AppendLine($"我理解了。\n\n可用能力:");
            response.AppendLine(string.Join(", ", _capabilities));
        }
        
        return new AgentResponse
        {
            Content = response.ToString(),
            Success = true,
            Data = new Dictionary<string, object>
            {
                { "contextHeader", context.PromptHeader },
                { "snippetsUsed", context.Snippets.Count }
            }
        };
    }
    
    #endregion
    
    #region Helper Methods
    
    private async Task StoreToMemoryAsync(Message input, AgentResponse output, string intent, CancellationToken ct)
    {
        var entry = new VectorDocument
        {
            Content = $"Q: {input.Content}\nA: {output.Content}",
            Summary = output.Content[..Math.Min(100, output.Content.Length)],
            Keywords = new List<string> { intent },
            Metadata = new Dictionary<string, object>
            {
                { "intent", intent },
                { "success", output.Success }
            }
        };
        
        await _vectorStore.StoreAsync(entry);
        
        // ✅ 同时索引到 RAG
        var ragDoc = new RAGDocument
        {
            Content = entry.Content,
            Summary = entry.Summary,
            Keywords = entry.Keywords,
            DocumentType = "agent_memory",
            Metadata = entry.Metadata
        };
        
        try
        {
            // 获取 RAGRecall 服务（如果可用）
            var ragRecall = _contextAssembler as IRAGRecall;
            if (ragRecall != null)
            {
                await ragRecall.IndexAsync(ragDoc);
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to index memory to RAG");
        }
    }
    
    private string ExtractFilePath(string content)
    {
        var patterns = new[] { @"\S+\.(cs|js|ts|py|java|go|rs)", @"[A-Za-z]:\\[^\s]+", @"/[^\s]+" };
        
        foreach (var pattern in patterns)
        {
            var match = System.Text.RegularExpressions.Regex.Match(content, pattern);
            if (match.Success)
                return match.Value;
        }
        
        return string.Empty;
    }
    
    private string GetContextSummary(ContextAssemblyResult context)
    {
        if (!context.Snippets.Any())
            return "";
        
        var sb = new System.Text.StringBuilder();
        sb.AppendLine("\n--- 上下文摘要 ---");
        sb.AppendLine($"来源: {context.SourceStats.Count(s => s.Value.SnippetCount > 0)} 个数据源");
        sb.AppendLine($"片段: {context.Snippets.Count} 条");
        sb.AppendLine($"Token: ~{context.TotalTokens}");
        
        return sb.ToString();
    }
    
    #endregion
}

/// <summary>
/// 上下文统计（用于响应元数据）
/// </summary>
public class ContextStats
{
    public int TotalSnippets { get; set; }
    public int TotalTokens { get; set; }
    public long AssemblyTimeMs { get; set; }
    public double TokenBudgetUsage { get; set; }
}
