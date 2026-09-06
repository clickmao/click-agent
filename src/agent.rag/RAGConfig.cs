using Microsoft.Extensions.Logging;
using System.Text.Json;


namespace agent.rag;

/// <summary>
/// RAG召回配置
/// </summary>
public class RAGConfig
{
    public int MaxRecallResults { get; set; } = 10;
    public double MinSimilarityScore { get; set; } = 0.3;
    public int EmbeddingDimension { get; set; } = 384;
    public bool EnableHybridSearch { get; set; } = true;
    public List<string> StopWords { get; set; } = new() { "的", "了", "在", "是", "我", "有", "和", "就", "不", "人" };
}

/// <summary>
/// RAG文档
/// </summary>
public class RAGDocument
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Content { get; set; } = string.Empty;
    public string? Summary { get; set; }
    public float[]? Embedding { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
    public List<string> Keywords { get; set; } = new();
    public string DocumentType { get; set; } = "general";
    public Dictionary<string, object> Metadata { get; set; } = new();
    public double? RelevanceScore { get; set; }
    public int AccessCount { get; set; }
    public DateTime LastAccessedAt { get; set; } = DateTime.UtcNow;
}

/// <summary>
/// 召回请求
/// </summary>
public class RecallRequest
{
    public string Query { get; set; } = string.Empty;
    public string? SessionId { get; set; }
    public string? UserId { get; set; }
    public string? DocumentType { get; set; }
    public int TopK { get; set; } = 5;
    public double? MinScore { get; set; }
    public List<string>? FilterKeywords { get; set; }
    public DateTime? FromDate { get; set; }
    public DateTime? ToDate { get; set; }
    public bool IncludeMetadata { get; set; } = true;
}

/// <summary>
/// 召回结果
/// </summary>
public class RecallResult
{
    public RAGDocument Document { get; set; } = null!;
    public double Score { get; set; }
    public string? HighlightedContent { get; set; }
    public int Rank { get; set; }
    public string MatchType { get; set; } = "semantic"; // semantic, keyword, hybrid
}

/// <summary>
/// RAG召回系统接口
/// </summary>
public interface IRAGRecall
{
    /// <summary>
    /// 索引文档
    /// </summary>
    Task IndexAsync(RAGDocument document);
    
    /// <summary>
    /// 批量索引
    /// </summary>
    Task IndexBatchAsync(IEnumerable<RAGDocument> documents);
    
    /// <summary>
    /// 召回
    /// </summary>
    Task<List<RecallResult>> RecallAsync(RecallRequest request);
    
    /// <summary>
    /// 获取文档
    /// </summary>
    Task<RAGDocument?> GetAsync(string id);
    
    /// <summary>
    /// 更新文档
    /// </summary>
    Task UpdateAsync(RAGDocument document);
    
    /// <summary>
    /// 删除文档
    /// </summary>
    Task DeleteAsync(string id);
    
    /// <summary>
    /// 获取统计信息
    /// </summary>
    Task<RAGStats> GetStatsAsync();
  
}

/// <summary>
/// RAG统计
/// </summary>
public class RAGStats
{
    public int TotalDocuments { get; set; }
    public int TotalKeywords { get; set; }
    public Dictionary<string, int> DocumentsByType { get; set; } = new();
    public DateTime OldestDocument { get; set; }
    public DateTime NewestDocument { get; set; }
}

/// <summary>
/// RAG召回系统实现
/// </summary>
public class RAGRecall : IRAGRecall
{
    private readonly ILogger<RAGRecall> _logger;
    private readonly RAGConfig _config;
    private readonly Dictionary<string, RAGDocument> _documents = new();
    private readonly object _lock = new();
    
    // 倒排索引
    private readonly Dictionary<string, HashSet<string>> _keywordIndex = new();
    
    // 文档类型索引
    private readonly Dictionary<string, HashSet<string>> _typeIndex = new();
    
    public RAGRecall(ILogger<RAGRecall> logger, RAGConfig? config = null)
    {
        _logger = logger;
        _config = config ?? new RAGConfig();
    }
    
    public Task IndexAsync(RAGDocument document)
    {
        if (string.IsNullOrEmpty(document.Id))
        {
            document.Id = Guid.NewGuid().ToString();
        }
        
        document.CreatedAt = DateTime.UtcNow;
        document.UpdatedAt = DateTime.UtcNow;
        
        // 生成embedding
        if (document.Embedding == null)
        {
            document.Embedding = GenerateEmbedding(document.Content);
        }
        
        // 提取关键词
        if (!document.Keywords.Any())
        {
            document.Keywords = ExtractKeywords(document.Content);
        }
        
        lock (_lock)
        {
            // 更新索引
            UpdateKeywordIndex(document);
            UpdateTypeIndex(document);
            
            _documents[document.Id] = document;
        }
        
        _logger.LogDebug("Indexed document {DocumentId}", document.Id);
        
        return Task.CompletedTask;
    }
    
    public async Task IndexBatchAsync(IEnumerable<RAGDocument> documents)
    {
        foreach (var doc in documents)
        {
            await IndexAsync(doc);
        }
    }
    
    public Task<List<RecallResult>> RecallAsync(RecallRequest request)
    {
        var results = new List<RecallResult>();
        var seen = new HashSet<string>();
        
        // 生成查询embedding
        var queryEmbedding = GenerateEmbedding(request.Query);
        var queryKeywords = ExtractKeywords(request.Query);
        
        lock (_lock)
        {
            IEnumerable<RAGDocument> candidates = _documents.Values;
            
            // 过滤
            if (!string.IsNullOrEmpty(request.DocumentType))
            {
                if (_typeIndex.TryGetValue(request.DocumentType, out var ids))
                {
                    candidates = candidates.Where(d => ids.Contains(d.Id));
                }
            }
            
            if (request.FromDate.HasValue)
            {
                candidates = candidates.Where(d => d.CreatedAt >= request.FromDate.Value);
            }
            
            if (request.ToDate.HasValue)
            {
                candidates = candidates.Where(d => d.CreatedAt <= request.ToDate.Value);
            }
            
            if (request.FilterKeywords?.Any() == true)
            {
                candidates = candidates.Where(d => 
                    d.Keywords.Any(k => request.FilterKeywords!.Contains(k, StringComparer.OrdinalIgnoreCase)));
            }
            
            // 语义搜索
            if (_config.EnableHybridSearch || request.TopK > 0)
            {
                foreach (var doc in candidates)
                {
                    if (seen.Contains(doc.Id)) continue;
                    
                    if (doc.Embedding == null) continue;
                    
                    var semanticScore = CosineSimilarity(queryEmbedding, doc.Embedding);
                    var keywordScore = CalculateKeywordScore(queryKeywords, doc.Keywords);
                    var finalScore = _config.EnableHybridSearch 
                        ? semanticScore * 0.7 + keywordScore * 0.3 
                        : semanticScore;

                    // v0.11.0 R44 (真缺陷 27): 词袋哈希 embedding 被长答案稀释 — 查询词命中文档内容
                    // 是强相关信号, 却可能整体得分 0.29 < 0.3 被砍 (实测 "Rust" 命中文档 0.291)。
                    // 直接内容命中 → 相关性下限 0.45 (比降阈值更精准: 不放噪声, 只保真命中)。
                    var contentHit = queryKeywords.Any(k =>
                        k.Length >= 2 && doc.Content.Contains(k, StringComparison.OrdinalIgnoreCase));
                    if (contentHit)
                        finalScore = Math.Max(finalScore, 0.45);

                    if (request.MinScore.HasValue && finalScore < request.MinScore.Value)
                        continue;
                    
                    seen.Add(doc.Id);
                    
                    results.Add(new RecallResult
                    {
                        Document = doc,
                        Score = finalScore,
                        HighlightedContent = HighlightContent(doc.Content, queryKeywords),
                        Rank = 0,
                        MatchType = _config.EnableHybridSearch ? "hybrid" : "semantic"
                    });
                }
            }
            
            // 纯关键词搜索（补充）
            if (_config.EnableHybridSearch)
            {
                foreach (var keyword in queryKeywords)
                {
                    if (_keywordIndex.TryGetValue(keyword.ToLowerInvariant(), out var docIds))
                    {
                        foreach (var docId in docIds)
                        {
                            if (seen.Contains(docId)) continue;
                            
                            if (_documents.TryGetValue(docId, out var doc))
                            {
                                seen.Add(docId);
                                
                                var keywordScore = CalculateKeywordScore(queryKeywords, doc.Keywords);
                                
                                results.Add(new RecallResult
                                {
                                    Document = doc,
                                    Score = keywordScore * 0.5, // 关键词搜索权重较低
                                    HighlightedContent = HighlightContent(doc.Content, queryKeywords),
                                    Rank = 0,
                                    MatchType = "keyword"
                                });
                            }
                        }
                    }
                }
            }
        }
        
        // 排序并去重
        var finalResults = results
            .GroupBy(r => r.Document.Id)
            .Select(g => g.OrderByDescending(r => r.Score).First())
            .OrderByDescending(r => r.Score)
            .Take(request.TopK > 0 ? request.TopK : _config.MaxRecallResults)
            .ToList();
        
        // 更新排名和访问统计
        for (int i = 0; i < finalResults.Count; i++)
        {
            finalResults[i].Rank = i + 1;
            finalResults[i].Document.AccessCount++;
            finalResults[i].Document.LastAccessedAt = DateTime.UtcNow;
        }
        
        _logger.LogInformation("Recall returned {Count} results for query: {Query}", finalResults.Count, request.Query);
        
        return Task.FromResult(finalResults);
    }
    
    public Task<RAGDocument?> GetAsync(string id)
    {
        lock (_lock)
        {
            _documents.TryGetValue(id, out var doc);
            return Task.FromResult(doc);
        }
    }
    
    public Task UpdateAsync(RAGDocument document)
    {
        lock (_lock)
        {
            if (_documents.ContainsKey(document.Id))
            {
                document.UpdatedAt = DateTime.UtcNow;
                _documents[document.Id] = document;
            }
        }
        
        return Task.CompletedTask;
    }
    
    public Task DeleteAsync(string id)
    {
        lock (_lock)
        {
            if (_documents.TryGetValue(id, out var doc))
            {
                // 清理索引
                RemoveFromKeywordIndex(doc);
                RemoveFromTypeIndex(doc);
                _documents.Remove(id);
            }
        }
        
        return Task.CompletedTask;
    }
    
    public Task<RAGStats> GetStatsAsync()
    {
        lock (_lock)
        {
            var docs = _documents.Values.ToList();
            
            return Task.FromResult(new RAGStats
            {
                TotalDocuments = docs.Count,
                TotalKeywords = _keywordIndex.Count,
                DocumentsByType = _typeIndex.ToDictionary(
                    kvp => kvp.Key, 
                    kvp => kvp.Value.Count),
                OldestDocument = docs.Any() ? docs.Min(d => d.CreatedAt) : DateTime.MinValue,
                NewestDocument = docs.Any() ? docs.Max(d => d.CreatedAt) : DateTime.MaxValue
            });
        }
    }
    
    private float[] GenerateEmbedding(string text)
    {
        // 改进的 embedding 实现：为每个词分配一个维度位置
        var words = Tokenize(text);
        var dimension = _config.EmbeddingDimension;
        var embedding = new float[dimension];
        
        // 使用词袋模型：将每个词哈希到不同维度
        for (int wordIndex = 0; wordIndex < words.Count; wordIndex++)
        {
            var word = words[wordIndex];
            var hash = Math.Abs(word.GetHashCode());
            
            // 将词分布到多个维度（使用不同种子）
            for (int seed = 0; seed < 3; seed++)
            {
                var combinedHash = hash + seed * 31337;
                var targetIndex = combinedHash % dimension;
                embedding[targetIndex] += 1.0f;
            }
        }
        
        // 归一化
        var magnitude = (float)Math.Sqrt(embedding.Sum(e => e * e));
        if (magnitude > 0)
        {
            for (int i = 0; i < embedding.Length; i++)
            {
                embedding[i] /= magnitude;
            }
        }
        
        return embedding;
    }
    
    private List<string> Tokenize(string text)
    {
        // 简单的中文/英文分词
        var tokens = new List<string>();
        
        // 移除停用词
        var words = text.ToLowerInvariant()
            .Split(new[] { ' ', '\t', '\n', '\r', '.', ',', '!', '?', ';', ':', '(', ')', '[', ']', '{', '}', '"', '\'', '`', '~', '@', '#', '$', '%', '^', '&', '*', '+', '=', '<', '>', '/', '\\', '|' }, 
                   StringSplitOptions.RemoveEmptyEntries);
        
        foreach (var word in words)
        {
            // v0.11.0 R44 (真缺陷 27 根因): 中英混写黏连 ("rust的所有权" 一个 token) —
            // 词面/嵌入/命中全失效。按 ascii↔非 ascii 边界再切:
            var segments = new List<string>();
            var sb = new System.Text.StringBuilder();
            var prevAscii = false;
            foreach (var ch in word)
            {
                var isAscii = ch < 0x80;
                if (sb.Length > 0 && isAscii != prevAscii)
                {
                    segments.Add(sb.ToString());
                    sb.Clear();
                }
                sb.Append(ch);
                prevAscii = isAscii;
            }
            if (sb.Length > 0) segments.Add(sb.ToString());

            foreach (var seg in segments)
            {
                if (!_config.StopWords.Contains(seg) && seg.Length >= 2)
                {
                    tokens.Add(seg);
                }
            }

            // v0.11.0 R6 (打点驱动修复): 中文无分词导致整句成一个 token — 词面/嵌入全部失效。
            // 轻量修复: 中文段 2-gram 滑窗补充 token (英文词已由上面的整词覆盖)。
            for (var i = 0; i + 2 <= word.Length; i++)
            {
                var gram = word.Substring(i, 2);
                if (gram[0] >= 0x4e00 && gram[0] <= 0x9fff &&
                    gram[1] >= 0x4e00 && gram[1] <= 0x9fff &&
                    !_config.StopWords.Contains(gram))
                {
                    tokens.Add(gram);
                }
            }
        }
        
        return tokens;
    }
    
    private List<string> ExtractKeywords(string text)
    {
        var tokens = Tokenize(text);
        
        // 词频统计
        var freq = tokens
            .GroupBy(t => t)
            .ToDictionary(g => g.Key, g => g.Count());
        
        // 返回高频词作为关键词
        return freq
            .OrderByDescending(kv => kv.Value)
            .Take(10)
            .Select(kv => kv.Key)
            .ToList();
    }
    
    private double CosineSimilarity(float[]? a, float[]? b)
    {
        if (a == null || b == null || a.Length != b.Length)
            return 0;
        
        var dot = 0.0;
        var normA = 0.0;
        var normB = 0.0;
        
        for (int i = 0; i < a.Length; i++)
        {
            dot += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }
        
        var denominator = Math.Sqrt(normA) * Math.Sqrt(normB);
        return denominator > 0 ? dot / denominator : 0;
    }
    
    private double CalculateKeywordScore(List<string> queryKeywords, List<string> docKeywords)
    {
        if (!queryKeywords.Any() || !docKeywords.Any())
            return 0;
        
        var intersection = queryKeywords.Intersect(docKeywords, StringComparer.OrdinalIgnoreCase).Count();
        var union = queryKeywords.Union(docKeywords, StringComparer.OrdinalIgnoreCase).Count();
        
        return union > 0 ? (double)intersection / union : 0;
    }
    
    private string HighlightContent(string content, List<string> keywords)
    {
        var result = content;
        
        foreach (var keyword in keywords)
        {
            result = System.Text.RegularExpressions.Regex.Replace(
                result,
                keyword,
                match => $"**{match.Value}**",
                System.Text.RegularExpressions.RegexOptions.IgnoreCase);
        }
        
        return result.Length > 500 ? result[..500] + "..." : result;
    }
    
    private void UpdateKeywordIndex(RAGDocument doc)
    {
        RemoveFromKeywordIndex(doc);
        
        foreach (var keyword in doc.Keywords)
        {
            var key = keyword.ToLowerInvariant();
            
            if (!_keywordIndex.ContainsKey(key))
            {
                _keywordIndex[key] = new HashSet<string>();
            }
            
            _keywordIndex[key].Add(doc.Id);
        }
    }
    
    private void UpdateTypeIndex(RAGDocument doc)
    {
        RemoveFromTypeIndex(doc);
        
        if (!_typeIndex.ContainsKey(doc.DocumentType))
        {
            _typeIndex[doc.DocumentType] = new HashSet<string>();
        }
        
        _typeIndex[doc.DocumentType].Add(doc.Id);
    }
    
    private void RemoveFromKeywordIndex(RAGDocument doc)
    {
        foreach (var keyword in doc.Keywords)
        {
            var key = keyword.ToLowerInvariant();
            
            if (_keywordIndex.TryGetValue(key, out var ids))
            {
                ids.Remove(doc.Id);
                
                if (ids.Count == 0)
                {
                    _keywordIndex.Remove(key);
                }
            }
        }
    }
    
    private void RemoveFromTypeIndex(RAGDocument doc)
    {
        if (_typeIndex.TryGetValue(doc.DocumentType, out var ids))
        {
            ids.Remove(doc.Id);
            
            if (ids.Count == 0)
            {
                _typeIndex.Remove(doc.DocumentType);
            }
        }
    }
}

/// <summary>
/// 用户反馈持久化服务
/// </summary>
public interface IFeedbackPersistence
{
    /// <summary>
    /// 保存用户反馈
    /// </summary>
    Task SaveAsync(UserFeedback feedback);
    
    /// <summary>
    /// 查询相似反馈（用于RAG召回）
    /// </summary>
    Task<List<RecallResult>> QuerySimilarAsync(string query, int topK = 5);
    
    /// <summary>
    /// 获取任务的所有反馈
    /// </summary>
    Task<List<UserFeedback>> GetByTaskAsync(string taskId);
    
    /// <summary>
    /// 获取会话的所有反馈
    /// </summary>
    Task<List<UserFeedback>> GetBySessionAsync(string sessionId);
    
    /// <summary>
    /// 标记反馈结果
    /// </summary>
    Task UpdateOutcomeAsync(string feedbackId, string outcome, double? satisfaction = null);
}

/// <summary>
/// 用户反馈持久化实现
/// </summary>
public class FeedbackPersistence : IFeedbackPersistence
{
    private readonly ILogger<FeedbackPersistence> _logger;
    private readonly IRAGRecall _ragRecall;
    private readonly Dictionary<string, UserFeedback> _feedbackStore = new();
    private readonly object _lock = new();
    
    public FeedbackPersistence(ILogger<FeedbackPersistence> logger, IRAGRecall ragRecall)
    {
        _logger = logger;
        _ragRecall = ragRecall;
    }
    
    public async Task SaveAsync(UserFeedback feedback)
    {
        if (string.IsNullOrEmpty(feedback.Id))
        {
            feedback.Id = Guid.NewGuid().ToString();
        }
        
        lock (_lock)
        {
            _feedbackStore[feedback.Id] = feedback;
        }
        
        // 索引到RAG
        var doc = new RAGDocument
        {
            Id = $"feedback_{feedback.Id}",
            Content = $"Task: {feedback.TaskDescription}\nContext: {feedback.Context}\nComment: {feedback.UserComment}\nOutcome: {feedback.Outcome}",
            Summary = $"{feedback.SelectedOptionLabel}: {feedback.TaskDescription}",
            Keywords = feedback.Keywords,
            DocumentType = "user_feedback",
            Metadata = new Dictionary<string, object>
            {
                { "feedbackId", feedback.Id },
                { "taskId", feedback.TaskId },
                { "sessionId", feedback.SessionId },
                { "selectedOption", feedback.SelectedOptionLabel ?? "" },
                { "outcome", feedback.Outcome ?? "" }
            }
        };
        
        await _ragRecall.IndexAsync(doc);
        
        _logger.LogInformation("Saved feedback {FeedbackId} and indexed to RAG", feedback.Id);
    }
    
    public async Task<List<RecallResult>> QuerySimilarAsync(string query, int topK = 5)
    {
        var request = new RecallRequest
        {
            Query = query,
            DocumentType = "user_feedback",
            TopK = topK
        };
        
        return await _ragRecall.RecallAsync(request);
    }
    
    public Task<List<UserFeedback>> GetByTaskAsync(string taskId)
    {
        lock (_lock)
        {
            var feedbacks = _feedbackStore.Values
                .Where(f => f.TaskId == taskId)
                .OrderByDescending(f => f.CreatedAt)
                .ToList();
            
            return Task.FromResult(feedbacks);
        }
    }
    
    public Task<List<UserFeedback>> GetBySessionAsync(string sessionId)
    {
        lock (_lock)
        {
            var feedbacks = _feedbackStore.Values
                .Where(f => f.SessionId == sessionId)
                .OrderByDescending(f => f.CreatedAt)
                .ToList();
            
            return Task.FromResult(feedbacks);
        }
    }
    
    public Task UpdateOutcomeAsync(string feedbackId, string outcome, double? satisfaction = null)
    {
        lock (_lock)
        {
            if (_feedbackStore.TryGetValue(feedbackId, out var feedback))
            {
                feedback.Outcome = outcome;
                feedback.Satisfaction = satisfaction;
            }
        }
        
        return Task.CompletedTask;
    }
}
