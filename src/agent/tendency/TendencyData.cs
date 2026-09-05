namespace agent.tendency;

/// <summary>
/// 倾向数据
/// </summary>
public class TendencyData
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string UserId { get; set; } = string.Empty;
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    public Dictionary<string, double> TopicScores { get; set; } = new();
    public Dictionary<string, double> StyleScores { get; set; } = new();
    public Dictionary<string, double> ComplexityPreferences { get; set; } = new();
    public string? PreferredResponseFormat { get; set; }
    public int ContextDepthPreference { get; set; } = 2; // 1-3
}

/// <summary>
/// 倾向配置
/// </summary>
public class TendencyConfig
{
    public double DecayFactor { get; set; } = 0.95; // 旧数据衰减
    public int MinSampleSize { get; set; } = 10;
    public int MaxHistorySize { get; set; } = 100;
    public TimeSpan DataRetention { get; set; } = TimeSpan.FromDays(30);
}

/// <summary>
/// 上下文偏见
/// </summary>
public class ContextBias
{
    public string UserId { get; set; } = string.Empty;
    public string Context { get; set; } = string.Empty;
    public Dictionary<string, double> BiasScores { get; set; } = new();
    public double OverallConfidence { get; set; }
}

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

/// <summary>
/// 倾向配置
/// </summary>
public class TendencyProfile
{
    public string UserId { get; set; } = string.Empty;
    public Dictionary<string, double> TopicTendencies { get; set; } = new();
    public Dictionary<string, double> StyleTendencies { get; set; } = new();
    public string ComplexityTendency { get; set; } = "medium";
    public double Confidence { get; set; }
    public DateTime LastUpdated { get; set; } = DateTime.UtcNow;
    public int SampleSize { get; set; }
}

/// <summary>
/// 倾向分析器实现（线程安全）
/// </summary>
public class TendencyAnalyzer : ITendencyAnalyzer
{
    private readonly Dictionary<string, List<TendencyData>> _userData = new();
    private readonly TendencyConfig _config;
    private readonly object _lock = new();
    
    // 预定义主题
    private static readonly Dictionary<string, string[]> TopicKeywords = new()
    {
        { "C#/.NET", new[] { "csharp", "dotnet", "aspnet", "efcore", "nuget" } },
        { "Web API", new[] { "api", "rest", "graphql", "http", "endpoint" } },
        { "Database", new[] { "sql", "mysql", "postgresql", "mongodb", "database" } },
        { "Testing", new[] { "test", "xunit", "nunit", "mock", "assert" } },
        { "DevOps", new[] { "docker", "kubernetes", "ci", "cd", "pipeline" } },
    };
    
    // 预定义风格
    private static readonly Dictionary<string, string[]> StyleKeywords = new()
    {
        { "detailed", new[] { "详细", "完整", "说明", "explain", "documentation" } },
        { "concise", new[] { "简洁", "简短", "精炼", "concise", "brief" } },
        { "with_docs", new[] { "注释", "文档", "comment", "xml", "md" } },
        { "code_only", new[] { "代码", "实现", "code", "only" } },
    };
    
    public TendencyAnalyzer()
    {
        _config = new TendencyConfig();
    }
    
    public Task<TendencyProfile> AnalyzeUserTendencyAsync(string userId)
    {
        var profile = new TendencyProfile { UserId = userId };
        
        if (!_userData.TryGetValue(userId, out var dataList) || !dataList.Any())
        {
            return Task.FromResult(profile);
        }
        
        profile.SampleSize = dataList.Count;
        
        // 计算主题倾向
        foreach (var (topic, keywords) in TopicKeywords)
        {
            var score = CalculateTendencyScore(dataList, keywords);
            if (score > 0.3)
            {
                profile.TopicTendencies[topic] = score;
            }
        }
        
        // 计算风格倾向
        foreach (var (style, keywords) in StyleKeywords)
        {
            var score = CalculateTendencyScore(dataList, keywords);
            if (score > 0.3)
            {
                profile.StyleTendencies[style] = score;
            }
        }
        
        // 计算复杂度倾向
        var avgComplexity = dataList.Average(d => d.ComplexityPreferences.Values.DefaultIfEmpty(2).Average());
        profile.ComplexityTendency = avgComplexity switch
        {
            < 1.5 => "simple",
            < 2.5 => "medium",
            _ => "complex"
        };
        
        // 计算置信度
        profile.Confidence = Math.Min(1.0, dataList.Count / 20.0);
        profile.LastUpdated = DateTime.UtcNow;
        
        return Task.FromResult(profile);
    }
    
    public Task UpdateTendencyAsync(string userId, TendencyData data)
    {
        lock (_lock)
        {
            data.UserId = userId;
            data.Timestamp = DateTime.UtcNow;
            
            if (!_userData.ContainsKey(userId))
            {
                _userData[userId] = new List<TendencyData>();
            }
        
            _userData[userId].Add(data);
            
            // 限制历史大小
            while (_userData[userId].Count > _config.MaxHistorySize)
            {
                _userData[userId].RemoveAt(0);
            }
        }
        
        return Task.CompletedTask;
    }
    
    public Task<ContextBias> GetContextBiasAsync(string userId, string context)
    {
        var bias = new ContextBias
        {
            UserId = userId,
            Context = context
        };
        
        // 分析上下文中的关键词
        var contextLower = context.ToLowerInvariant();
        
        foreach (var (topic, keywords) in TopicKeywords)
        {
            var matches = keywords.Count(k => contextLower.Contains(k.ToLowerInvariant()));
            if (matches > 0)
            {
                bias.BiasScores[topic] = (double)matches / keywords.Length;
            }
        }
        
        // 计算总体置信度
        bias.OverallConfidence = bias.BiasScores.Values.DefaultIfEmpty(0).Average();
        
        return Task.FromResult(bias);
    }
    
    private double CalculateTendencyScore(List<TendencyData> dataList, string[] keywords)
    {
        var totalScore = 0.0;
        var weights = 1.0;
        
        // 按时间递减权重
        foreach (var data in dataList.TakeLast(_config.MinSampleSize))
        {
            totalScore += weights;
            weights *= _config.DecayFactor;
        }
        
        return Math.Min(1.0, totalScore / 20.0);
    }
}
