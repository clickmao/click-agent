using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.vectormemory;


/// <summary>
/// 向量存储实现（简化版）
/// </summary>
public class VectorStore : IVectorStore
{
    private readonly ILogger<VectorStore> _logger;
    private readonly Dictionary<string, VectorDocument> _store = new();
    private readonly EmbeddingConfig _config;
    private readonly object _lock = new();
    // v0.11.0 R100: embedding 提供者可插拔 (默认词频 hash 行为不变; JIT 形态可注册 BgeEmbeddingProvider)
    private readonly IEmbeddingProvider _embeddingProvider;

    public VectorStore(ILogger<VectorStore> logger, EmbeddingConfig? config = null, IEmbeddingProvider? embeddingProvider = null)
    {
        _logger = logger;
        _config = config ?? new EmbeddingConfig();
        _embeddingProvider = embeddingProvider ?? new HashEmbeddingProvider(_config.Dimension);
    }
    
    public Task<string> StoreAsync(VectorDocument entry)
    {
        if (string.IsNullOrEmpty(entry.Id))
        {
            entry.Id = Guid.NewGuid().ToString();
        }
        
        entry.CreatedAt = DateTime.UtcNow;
        entry.LastAccessedAt = DateTime.UtcNow;
        
        // 生成embedding
        if (entry.Embedding == null && !string.IsNullOrEmpty(entry.Content))
        {
            entry.Embedding = GenerateEmbedding(entry.Content);
        }
        
        lock (_lock)
        {
            _store[entry.Id] = entry;
        }
        
        _logger.LogDebug("Stored memory entry: {EntryId}", entry.Id);
        
        return Task.FromResult(entry.Id);
    }
    
    public Task<List<SemanticSearchResult>> SearchAsync(SemanticSearchRequest request)
    {
        var results = new List<SemanticSearchResult>();
        
        // 生成查询embedding
        var queryEmbedding = GenerateEmbedding(request.Query);
        
        lock (_lock)
        {
            var candidates = _store.Values.AsEnumerable();
            
            // 过滤
            if (request.FilterKeywords?.Any() == true)
            {
                candidates = candidates.Where(e => 
                    request.FilterKeywords!.Any(k => 
                        e.Keywords.Contains(k, StringComparer.OrdinalIgnoreCase)));
            }
            
            if (request.FromDate.HasValue)
            {
                candidates = candidates.Where(e => e.CreatedAt >= request.FromDate.Value);
            }
            
            if (request.ToDate.HasValue)
            {
                candidates = candidates.Where(e => e.CreatedAt <= request.ToDate.Value);
            }
            
            // 计算相似度
            foreach (var entry in candidates)
            {
                if (entry.Embedding == null) continue;
                
                var score = CosineSimilarity(queryEmbedding, entry.Embedding);
                
                if (request.MinScore.HasValue && score < request.MinScore.Value)
                    continue;
                
                results.Add(new SemanticSearchResult
                {
                    Entry = entry,
                    Score = score,
                    HighlightedContent = HighlightContent(entry.Content, request.Query)
                });
            }
        }
        
        // 排序并取TopK
        return Task.FromResult(
            results.OrderByDescending(r => r.Score)
                   .Take(request.TopK)
                   .ToList());
    }
    
    public Task<VectorDocument?> GetAsync(string id)
    {
        lock (_lock)
        {
            if (_store.TryGetValue(id, out var entry))
            {
                entry.AccessCount++;
                entry.LastAccessedAt = DateTime.UtcNow;
                return Task.FromResult<VectorDocument?>(entry);
            }
        }
        
        return Task.FromResult<VectorDocument?>(null);
    }
    
    public Task UpdateAsync(VectorDocument entry)
    {
        lock (_lock)
        {
            if (_store.ContainsKey(entry.Id))
            {
                _store[entry.Id] = entry;
            }
        }
        
        return Task.CompletedTask;
    }
    
    public Task DeleteAsync(string id)
    {
        lock (_lock)
        {
            _store.Remove(id);
        }
        
        return Task.CompletedTask;
    }
    
    public Task<float[]?> GenerateEmbeddingAsync(string text)
    {
        var embedding = GenerateEmbedding(text);
        return Task.FromResult<float[]?>(embedding);
    }
    
    public Task<List<VectorDocument>> GetSimilarAsync(string id, int topK = 5)
    {
        VectorDocument? entry;
        
        lock (_lock)
        {
            _store.TryGetValue(id, out entry);
        }
        
        if (entry?.Embedding == null)
        {
            return Task.FromResult(new List<VectorDocument>());
        }
        
        var results = new List<(VectorDocument Entry, double Score)>();
        
        lock (_lock)
        {
            foreach (var kvp in _store)
            {
                if (kvp.Key == id || kvp.Value.Embedding == null)
                    continue;
                
                var score = CosineSimilarity(entry.Embedding, kvp.Value.Embedding);
                results.Add((kvp.Value, score));
            }
        }
        
        return Task.FromResult(
            results.OrderByDescending(r => r.Score)
                   .Take(topK)
                   .Select(r => r.Entry)
                   .ToList());
    }
    
    private float[] GenerateEmbedding(string text)
    {
        // v0.11.0 R100: 委托给 IEmbeddingProvider (默认 hash provider 行为与原词频实现一致)
        var embedding = _embeddingProvider.Embed(text);
        // 归一化 (保持原行为)
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
    
    private string HighlightContent(string content, string query)
    {
        // 简单的文本高亮
        var words = query.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        var result = content;
        
        foreach (var word in words)
        {
            result = System.Text.RegularExpressions.Regex.Replace(
                result, 
                word, 
                match => $"**{match.Value}**", 
                System.Text.RegularExpressions.RegexOptions.IgnoreCase);
        }
        
        return result.Length > 500 ? result[..500] + "..." : result;
    }
}
