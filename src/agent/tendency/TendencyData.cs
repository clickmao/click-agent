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
    // v0.11.0 R133: 置信度诊断信息 (max-based 公式的稀释保留: 弱/强信号条目数)
    public Dictionary<string, object> Metadata { get; set; } = new();
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
            // v0.11.0 R123 (真缺陷 52): 空 userId 信号持久化到 ".json" (Sanitize 后空文件名) —
            // 召回链 (GetContextBiasAsync→AnalyzeUserTendencyAsync) 永不读取它, 纯无意义写盘。跳过。
            if (string.IsNullOrWhiteSpace(userId))
                return;
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
        
        // v0.11.0 R133 (K1 断链根因): 画像统计只基于有信号记录 (TopicScores/StyleScores 任一非空)。
        // 空信号记录 (问候/系统消息) 不携带主题信息, 混入窗口只会稀释命中占比 —
        // 此前 TakeLast 最近 10 条常被空记录占满 → 得分恒 <0.3 → 画像恒空 → 召回恒 0。
        var signaled = dataList.Where(d => d.TopicScores.Count > 0 || d.StyleScores.Count > 0).ToList();
        if (signaled.Count == 0)
        {
            return Task.FromResult(profile);
        }
        
        profile.SampleSize = signaled.Count;
        
        // 计算主题倾向
        foreach (var (topic, keywords) in TopicKeywords)
        {
            var score = CalculateTendencyScore(signaled, keywords);
            if (score > 0.3)
            {
                profile.TopicTendencies[topic] = score;
            }
        }
        
        // 计算风格倾向
        foreach (var (style, keywords) in StyleKeywords)
        {
            var score = CalculateTendencyScore(signaled, new[] { style });
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
        
        // 计算置信度 (有信号样本数口径 — 空记录不构成画像证据)
        profile.Confidence = Math.Min(1.0, signaled.Count / 20.0);
        profile.LastUpdated = DateTime.UtcNow;
        
        return Task.FromResult(profile);
    }
    
    public Task UpdateTendencyAsync(string userId, TendencyData data)
    {
        // v0.11.0 R123 (缺陷 52): 空 userId 不入库不落盘 — 召回链永不读取, 内存/磁盘双重跳过
        if (string.IsNullOrWhiteSpace(userId))
            return Task.CompletedTask;
        // v0.11.0 R133 (K1 断链根因): 全空信号 (TopicScores/StyleScores 皆空, 如问候/系统消息)
        // 不入库 — 它们不携带任何主题/风格信息, 只占 MaxHistorySize 窗口稀释命中占比,
        // 是 AnalyzeUserTendencyAsync 画像被拉低到恒 <0.3 的元凶 (cli_user.json 实证 100 条中 76 条空)。
        if (data.TopicScores.Count == 0 && data.StyleScores.Count == 0)
            return Task.CompletedTask;
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
                    // v0.11.0 R133 (K1 断链修复 A): 原防覆盖逻辑 (!ContainsKey) 让历史高分被当前查询低分
                    // 完全屏蔽 ("python api" 查询 → Python=1/5=0.2 覆盖历史 0.341 → avg 稀释 → 恒被 0.3 阈值拦截)。
                    // 改为取 max: 历史与当前是同一信号的两个观测, 取更强者 (历史仍降权防压制现场)。
                    if (score >= 0.3)
                        bias.BiasScores[style] = Math.Max(bias.BiasScores.GetValueOrDefault(style), score * 0.8);
                }
                foreach (var (topic, score) in profile.TopicTendencies)
                {
                    if (score >= 0.3)
                        bias.BiasScores[topic] = Math.Max(bias.BiasScores.GetValueOrDefault(topic), score * 0.8);
                }
            }
        }
        catch
        {
            // 历史倾向读取失败不阻断 — 保持纯当前查询行为
        }

        // v0.11.0 R133 (K1 断链修复 B): 原 avg 公式有结构性稀释缺陷 — BiasScores 条目越多
        // (用户画像越丰富), 平均值越低: {Python:0.2, WebAPI:0.2} → 0.2 恒被 0.3 阈值拦截,
        // 而单主题用户反而轻松通过 (信号质量与条目数成反比, 语义颠倒)。
        // 改 max-based: 最强信号代表置信度 (任一倾向≥0.34 即可信), WeakCount 打点保留稀释信息。
        bias.OverallConfidence = bias.BiasScores.Values.DefaultIfEmpty(0).DefaultIfEmpty(0).Max();
        bias.Metadata["weak_count"] = bias.BiasScores.Values.Count(v => v < 0.3);
        bias.Metadata["strong_count"] = bias.BiasScores.Values.Count(v => v >= 0.3);
        // R133: K1 观测点位 (此前 bias 计算全程无打点 — 立项卡 T5/K1): 每次召回计算必 emit
        agent.config.AgentTelemetry.Emit("tendency_bias", "TendencyAnalyzer",
            ("user", userId), ("scores", string.Join(";", bias.BiasScores.Select(kv => $"{kv.Key}={kv.Value:F2}"))),
            ("conf", Math.Round(bias.OverallConfidence, 3)), ("sample", AnalyzeUserTendencyAsync(userId).GetAwaiter().GetResult().SampleSize));
        
        return Task.FromResult(bias);
    }
    
    private double CalculateTendencyScore(List<TendencyData> dataList, string[] keywords)
    {
        // v0.11.0 R14 修复: 原实现只按样本计数 (与 keywords 无关, 需 6 条才过 0.3 阈值),
        // 改为 "关键词命中占比 × 时间衰减权重" — 新用户少量样本即可反映倾向。
        // v0.11.0 R146 (K1 门槛卡点修复): TakeLast(MinSampleSize=10) 只看最近 10 条 —
        // cli_user.json 实证 64 条有信号历史中 AI/LLM 最近 10 条窗口恰 0.2965, 差 0.004 被门 0.3 拦截
        // (画像明明稳定, 却因窗口过窄波动在门槛两侧) → 改为全量有信号历史, 旧信号由 DecayFactor=0.95^k
        // 自然降权 (10 条前权重已 <0.6, 30 条前 <0.21), 窗口语义由"最近倾向"回归"带衰减的稳定画像"。
        var recent = dataList.TakeLast(_config.MaxHistorySize).ToList();
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
