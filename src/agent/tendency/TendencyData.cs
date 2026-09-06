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
    // v0.11.0 R34 (真 bug 24): _userData 纯内存 — 进程重启丢光, 跨会话 UserTendency 恒 0。
    // 落盘 data/tendency/{userId-safe}.json, 构造时惰性加载 (与 SessionMemory 落盘模式一致)。
    private readonly string _storeDir;
    private bool _loaded;
    
    // 预定义主题
    private static readonly Dictionary<string, string[]> TopicKeywords = new()
    {
        { "C#/.NET", new[] { "csharp", "dotnet", "aspnet", "efcore", "nuget" } },
        { "Web API", new[] { "api", "rest", "graphql", "http", "endpoint" } },
        { "Database", new[] { "sql", "mysql", "postgresql", "mongodb", "database" } },
        { "Testing", new[] { "test", "xunit", "nunit", "mock", "assert" } },
        { "DevOps", new[] { "docker", "kubernetes", "ci", "cd", "pipeline" } },
        // v0.11.0 R34: 语言/系统主题扩充 (打点实证 "Rust" 信号 0 → 偏好画像空)
        { "Rust", new[] { "rust", "cargo", "rustc" } },
        { "Python", new[] { "python", "pip", "pytest", "django", "flask" } },
        { "Go", new[] { "golang", " go ", "goroutine" } },
        { "Frontend", new[] { "javascript", "typescript", "react", "vue", "css" } },
        { "AI/LLM", new[] { "llm", "agent", "prompt", "embedding", "rag" } },
    };
    
    // 预定义风格
    private static readonly Dictionary<string, string[]> StyleKeywords = new()
    {
        { "detailed", new[] { "详细", "完整", "说明", "explain", "documentation" } },
        { "concise", new[] { "简洁", "简短", "精炼", "concise", "brief" } },
        { "with_docs", new[] { "注释", "文档", "comment", "xml", "md" } },
        { "code_only", new[] { "代码", "实现", "code", "only" } },
    };
    
    public TendencyAnalyzer() : this("data/tendency") { }

    public TendencyAnalyzer(string storeDir)
    {
        _config = new TendencyConfig();
        _storeDir = storeDir;
        LoadAll();
    }

    /// <summary>v0.11.0 R34: 进程启动加载已落盘的倾向数据 (跨会话画像连续性)</summary>
    private void LoadAll()
    {
        try
        {
            if (!Directory.Exists(_storeDir))
                return;
            foreach (var file in Directory.EnumerateFiles(_storeDir, "*.json"))
            {
                using var doc = System.Text.Json.JsonDocument.Parse(File.ReadAllText(file));
                var list = new List<TendencyData>();
                foreach (var el in doc.RootElement.EnumerateArray())
                {
                    var d = new TendencyData
                    {
                        UserId = el.TryGetProperty("UserId", out var u) ? (u.GetString() ?? "anonymous") : "anonymous",
                        Timestamp = el.TryGetProperty("Timestamp", out var t) && t.ValueKind == System.Text.Json.JsonValueKind.String
                            ? DateTime.TryParse(t.GetString(), null, System.Globalization.DateTimeStyles.RoundtripKind, out var dt) ? dt : DateTime.UtcNow
                            : DateTime.UtcNow,
                    };
                    if (el.TryGetProperty("TopicScores", out var tp) && tp.ValueKind == System.Text.Json.JsonValueKind.Object)
                        foreach (var p in tp.EnumerateObject())
                            d.TopicScores[p.Name] = p.Value.GetDouble();
                    if (el.TryGetProperty("StyleScores", out var sp) && sp.ValueKind == System.Text.Json.JsonValueKind.Object)
                        foreach (var p in sp.EnumerateObject())
                            d.StyleScores[p.Name] = p.Value.GetDouble();
                    list.Add(d);
                }
                if (list is { Count: > 0 } && list[0].UserId is { Length: > 0 } uid)
                    _userData[uid] = list;
            }
        }
        catch { /* 倾向加载失败不阻断 — 内存态继续可用 */ }
    }

    /// <summary>v0.11.0 R34: 写入后落盘 (整体快照, 单用户一文件)。
    /// 手写 JSON — 全局禁反射序列化 (AOT), TendencyData 仅字典+标量, 手写可控。</summary>
    private static string EscapeJson(string t) => t
        .Replace("\\", "\\\\").Replace("\"", "\\\"")
        .Replace("\n", "\\n").Replace("\r", "\\r").Replace("\t", "\\t");

    private static string SerializeScores(Dictionary<string, double> d) => "{" +
        string.Join(",", d.Select(kv => $"\"{EscapeJson(kv.Key)}\":{kv.Value.ToString(System.Globalization.CultureInfo.InvariantCulture)}")) + "}";

    private void Persist(string userId)
    {
        try
        {
            Directory.CreateDirectory(_storeDir);
            var safe = string.Concat(userId.Select(c => char.IsLetterOrDigit(c) ? c : '_'));
            var sb = new System.Text.StringBuilder("[");
            var first = true;
            foreach (var d in _userData[userId])
            {
                if (!first) sb.Append(',');
                first = false;
                sb.Append("{\"UserId\":\"").Append(EscapeJson(d.UserId ?? ""));
                sb.Append("\",\"Timestamp\":\"").Append(d.Timestamp.ToString("O"))
                  .Append("\",\"TopicScores\":").Append(SerializeScores(d.TopicScores))
                  .Append(",\"StyleScores\":").Append(SerializeScores(d.StyleScores))
                  .Append('}');
            }
            sb.Append(']');
            File.WriteAllText(Path.Combine(_storeDir, safe + ".json"), sb.ToString());
            agent.config.AgentTelemetry.Emit("tendency", "TendencyAnalyzer",
                ("op", "persist"), ("ok", true), ("user", safe), ("count", _userData[userId].Count));
        }
        catch (Exception pEx)
        {
            agent.config.AgentTelemetry.Emit("tendency", "TendencyAnalyzer",
                ("op", "persist"), ("ok", false), ("error", pEx.GetType().Name + ": " + pEx.Message));
        }
    }

    /// <summary>
    /// v0.11.0 R14: 从用户消息提取主题/风格信号 (静态纯函数, 写入侧用)。
    /// 命中关键词计 1.0, 未命中不计 — 与 CalculateTendencyScore 的关键词表共用数据。
    /// </summary>
    public static Dictionary<string, double> ExtractSignals(string text)
    {
        var result = new Dictionary<string, double>();
        if (string.IsNullOrWhiteSpace(text))
            return result;
        var lower = text.ToLowerInvariant();
        foreach (var (topic, keywords) in TopicKeywords)
        {
            var hitKw = keywords.FirstOrDefault(k => lower.Contains(k, StringComparison.Ordinal));
            if (hitKw != null)
            {
                result[topic] = 1.0;
                result[hitKw] = 1.0; // 关键词本身也入信号 (CalculateTendencyScore 相交判定用)
            }
        }
        foreach (var (style, keywords) in StyleKeywords)
        {
            var hitKw = keywords.FirstOrDefault(k => lower.Contains(k, StringComparison.Ordinal));
            if (hitKw != null)
            {
                result[style] = 1.0;
                result[hitKw] = 1.0;
            }
        }
        return result;
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
            var score = CalculateTendencyScore(dataList, new[] { style });
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

            Persist(userId); // v0.11.0 R34: 落盘 (锁内快照, 防并发写坏)
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
        
        // v0.11.0 R14 修复: 原实现只看当前查询关键词命中 (用户历史倾向完全没用上)。
        // 融合 AnalyzeUserTendencyAsync 的历史 profile: 历史风格/主题倾向 ≥0.3 的条目注入 BiasScores。
        try
        {
            var profile = AnalyzeUserTendencyAsync(userId).GetAwaiter().GetResult();
            if (profile.SampleSize > 0)
            {
                foreach (var (style, score) in profile.StyleTendencies)
                {
                    if (score >= 0.3 && !bias.BiasScores.ContainsKey(style))
                        bias.BiasScores[style] = score * 0.8; // 历史信号略降权, 当前查询优先
                }
                foreach (var (topic, score) in profile.TopicTendencies)
                {
                    if (score >= 0.3 && !bias.BiasScores.ContainsKey(topic))
                        bias.BiasScores[topic] = score * 0.8;
                }
            }
        }
        catch
        {
            // 历史倾向读取失败不阻断 — 保持纯当前查询行为
        }

        // 计算总体置信度
        bias.OverallConfidence = bias.BiasScores.Values.DefaultIfEmpty(0).Average();
        
        return Task.FromResult(bias);
    }
    
    private double CalculateTendencyScore(List<TendencyData> dataList, string[] keywords)
    {
        // v0.11.0 R14 修复: 原实现只按样本计数 (与 keywords 无关, 需 6 条才过 0.3 阈值),
        // 改为 "关键词命中占比 × 时间衰减权重" — 新用户少量样本即可反映倾向。
        var recent = dataList.TakeLast(_config.MinSampleSize).ToList();
        if (recent.Count == 0)
            return 0.0;

        var weight = 1.0;
        var weightedHit = 0.0;
        var weightSum = 0.0;
        foreach (var data in recent)
        {
            // 命中判定: 信号字典直接含主题名, 或原始信号任一关键词与目标关键词表相交
            var allKeys = data.TopicScores.Keys.Concat(data.StyleScores.Keys).ToList();
            var hit = keywords.Any(kw => allKeys.Contains(kw, StringComparer.OrdinalIgnoreCase)) ||
                      allKeys.Any(k => keywords.Any(kw => k.Contains(kw, StringComparison.OrdinalIgnoreCase)));
            if (hit)
                weightedHit += weight;
            weightSum += weight;
            weight *= _config.DecayFactor;
        }

        return weightSum > 0 ? Math.Min(1.0, weightedHit / weightSum * 1.2) : 0.0;
    }
}
