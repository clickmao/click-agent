using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.rag;


/// <summary>
/// RAG召回系统实现
/// </summary>
public class RAGRecall : IRAGRecall
{
    private readonly ILogger<RAGRecall> _logger;
    private readonly RAGConfig _config;
    private readonly Dictionary<string, RAGDocument> _documents = new();
    private readonly object _lock = new();
    // R404: 融合召回 (bge-base 语义路 + 词法路 + RRF); null = 关闭 ⇒ 完全走旧路径
    private readonly FusionRecall? _fusion;

    /// <summary>精排打分器 (第二级相关性模型)。默认零依赖词法基线; 换本地 cross-encoder / 本地 LLM 打分即升级精排。</summary>
    private readonly IRerankScorer _rerank = new LexicalRerankScorer(0.5);
    // R404: 文档二元组记忆化 — 按 (Id, UpdatedAt) 校验, 内容变了自动失效 (不脏读);
    // 无它则每次召回对全库重切二元组 (O(库大小) 字符操作)。
    private readonly Dictionary<string, (DateTime Stamp, string[] Grams)> _bigramMemo = new(StringComparer.Ordinal);
    // v0.11.0 R109 (fix#41): 内容去重索引 (归一化哈希 → 既有文档 Id)
    private readonly object _dedupLock = new();
    private readonly Dictionary<string, string> _contentDedup = new(StringComparer.Ordinal);
    
    // 倒排索引
    private readonly Dictionary<string, HashSet<string>> _keywordIndex = new();
    
    // 文档类型索引
    private readonly Dictionary<string, HashSet<string>> _typeIndex = new();
    
    // v0.16.3 (R331, P12): 落盘裁剪摊销 — 上限 512 行 (保留最新), 每 RagPruneInterval 次追加
    // 才整读一次判裁剪 (原每 append 无条件整读+可能整写 → 过上限后每消息 O(库大小) 文件 IO)。
    // 语义: 文件可在两次裁剪间瞬时达 512+63 行 (有界松弛), 每次裁剪终态 = 保留最新 512,
    // 与逐次裁剪内容集一致 (追加+保尾裁剪单调); 文件被外部删除/重建后计数器最多漂移
    // RagPruneInterval 次 append, 下次裁剪整读实测自愈, 无永久漂移。
    private const int RagPersistMaxLines = 512;
    private const int RagPruneInterval = 64;
    private int _persistAppendsSincePrune;
    
    // v0.11.0 R79 (真缺陷 33): RAG 索引落盘路径 — 进程重启后恢复 (与 TendencyData 同类缺陷修复)
    private static readonly string PersistPath = Path.Combine(
        AppContext.BaseDirectory, "..", "..", "..", "..", "..", "..", "data", "rag", "index.jsonl");
    private string ResolvePersistPath()
    {
        // v0.11.0 R109: 覆写优先 (评测隔离) → CWD 优先 (仓库根运行 = 真机标准形态) → AppContext 推导 (AOT 独立运行)
        if (!string.IsNullOrEmpty(_config.PersistPathOverride)) return _config.PersistPathOverride;
        var cwdPath = Path.GetFullPath("data/rag/index.jsonl");
        var usePath = File.Exists(cwdPath) || Directory.Exists("data") ? cwdPath : PersistPath;
        return usePath;
    }

    /// <summary>v0.13.0 (用户钦定): 当前 RAG 数据文件路径 (/rag 查询用)</summary>
    public string CurrentPersistPath() => ResolvePersistPath();

    /// <summary>v0.13.0 (用户钦定): 运行时切换 RAG 数据文件 (/rag <path>; 新文档落新路径; 历史重载需重启)</summary>
    public void SetPersistOverride(string path)
    {
        _config.PersistPathOverride = path;
        _logger.LogInformation("RAG persist path override set: {Path}", path);
    }

    public RAGRecall(ILogger<RAGRecall> logger, RAGConfig? config = null)
    {
        _logger = logger;
        _config = config ?? new RAGConfig();
        _fusion = _config.Fusion is { Enabled: true }
            ? new FusionRecall(_config.Fusion, new DenseRoute(), new LexicalRoute())
            : null;
        // v0.11.0 R79: 构造时恢复上次落盘索引 (跨进程召回)
        LoadPersisted();
    }

    /// <summary>R404: 融合路计数 (证据打点 — 每路真实被用次数/降级次数; null = 融合关闭)。</summary>
    public FusionCounters? FusionCounters => _fusion?.Counters;

    /// <summary>v0.11.0 R79: 读侧恢复 — JSONL 每行一文档 (手写解析, 零反射)</summary>
    private void LoadPersisted()
    {
        try
        {
            var path = ResolvePersistPath();
            if (!File.Exists(path)) return;
            var loaded = 0;
            foreach (var line in File.ReadLines(path))
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                var doc = ParsePersistedDocument(line);
                if (doc == null) continue;
                lock (_lock)
                {
                    UpdateKeywordIndex(doc);
                    UpdateTypeIndex(doc);
                    _documents[doc.Id] = doc;
                }
                loaded++;
            }
            if (loaded > 0)
                _logger.LogInformation("RAG index restored: {Count} documents from {Path}", loaded, path);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "RAG index restore failed (non-fatal)");
        }
    }

    /// <summary>v0.11.0 R92: STJ source-gen 反序列化 (替换 R79 手写解析 — 零反射保持, AOT 官方路径)</summary>
    private static RAGDocument? ParsePersistedDocument(string json)
    {
        try
        {
            var dto = System.Text.Json.JsonSerializer.Deserialize(json, RAGPersistJsonContext.Default.RAGPersistDoc);
            if (dto is null || dto.Content.Length == 0) return null;
            return new RAGDocument
            {
                Id = dto.Id,
                Content = dto.Content,
                DocumentType = string.IsNullOrEmpty(dto.Type) ? "general" : dto.Type,
                Embedding = dto.Embedding.Count > 0 ? dto.Embedding.ToArray() : null,
                Keywords = dto.Keywords,
            };
        }
        catch { return null; }
    }
    /// <summary>v0.11.0 R92: 写侧落盘 — STJ source-gen (零反射); 追加写, 上限 512 文档裁剪</summary>
    private void PersistDocument(RAGDocument doc)
    {
        try
        {
            var path = ResolvePersistPath();
            var dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
            var emb = doc.Embedding ?? GenerateEmbedding(doc.Content);
            // v0.11.0 R92: STJ source-gen 序列化 (替换 R79 手写拼 JSON — 用户注意点 2, 零反射保持)
            var dto = new RAGPersistDoc
            {
                Id = doc.Id,
                Type = doc.DocumentType ?? "general",
                Keywords = doc.Keywords,
                Embedding = emb.ToList(),
                Content = doc.Content,
            };
            var line = System.Text.Json.JsonSerializer.Serialize(dto, RAGPersistJsonContext.Default.RAGPersistDoc) + "\n";
            File.AppendAllText(path, line);
            // v0.16.3 (R331, P12): 上限裁剪摊销 — 原每 append 无条件整读判裁剪 (过 512 后每消息
            // 整读+整写 ~512 行 = 每消息 O(库大小) 文件 IO); 改内存计数, 每 64 次追加整读一次,
            // 超限重建保留最新 512 (lines[^512..] 语义不变)。文件瞬时上限 512+63 行, 有界。
            if (Interlocked.Increment(ref _persistAppendsSincePrune) % RagPruneInterval == 0)
            {
                Interlocked.Exchange(ref _persistAppendsSincePrune, 0);
                var lines = File.ReadAllLines(path);
                if (lines.Length > RagPersistMaxLines)
                {
                    File.WriteAllLines(path, lines[^RagPersistMaxLines..]);
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "RAG index persist failed (non-fatal)");
        }
    }
    
    public Task IndexAsync(RAGDocument document)
    {
        if (string.IsNullOrEmpty(document.Id))
        {
            document.Id = Guid.NewGuid().ToString();
        }
        
        document.CreatedAt = DateTime.UtcNow;
        document.UpdatedAt = DateTime.UtcNow;
        
        // v0.11.0 R109 (fix#41): 同内容去重 — 千轮循环场景同题记忆反复写入, 召回 rel 并列退化、
        // token 随库线性涨 (实测 C11 Memory 126→465tok)。归一化内容哈希命中 → 复用既有 Id (更新语义)。
        var contentKey = NormalizeForDedup(document.Content);
        lock (_dedupLock)
        {
            if (_contentDedup.TryGetValue(contentKey, out var existingId)
                && _documents.ContainsKey(existingId))
            {
                document.Id = existingId;
                _logger.LogDebug("Dedup hit for document {DocumentId}", existingId);
            }
            else
            {
                _contentDedup[contentKey] = document.Id;
            }
        }
        
        // 生成embedding
        if (document.Embedding == null)
        {
            document.Embedding = GenerateEmbedding(document.Content);
        }

        // v0.13.3 缺陷69 根治 (B 期召回全量化): 长文档 (>440ch) 单向量只覆盖首块 —
        // 切多 chunk (每 chunk ≤440ch, 独立向量), chunk 文档 Id=base#cN + Metadata[parent_id]=base。
        // 召回命中 chunk → RecalAsync 层映射回父文档 (全文浮出)。主文档 Embedding = 首块向量。
        var chunkDocs = new List<RAGDocument>();
        if (document.Content.Length > 440)
        {
            var chunkSize = 440;
            var chunkIdx = 0;
            for (var pos = 0; pos < document.Content.Length; pos += chunkSize)
            {
                var chunkText = document.Content.Substring(pos, Math.Min(chunkSize, document.Content.Length - pos));
                if (chunkIdx == 0)
                {
                    // 首块 = 主文档向量 (已生成); 记 parent_id:
                    document.Metadata["parent_id"] = document.Id;
                }
                else
                {
                    var cd = new RAGDocument
                    {
                        Id = $"{document.Id}#c{chunkIdx}",
                        Content = chunkText,
                        DocumentType = document.DocumentType ?? "general",
                        CreatedAt = document.CreatedAt,
                        UpdatedAt = document.UpdatedAt,
                        Keywords = document.Keywords.Any() ? document.Keywords : ExtractKeywords(chunkText),
                    };
                    cd.Metadata["parent_id"] = document.Id;
                    cd.Metadata["chunk_count"] = (document.Content.Length + chunkSize - 1) / chunkSize;
                    cd.Embedding = GenerateEmbedding(chunkText);
                    chunkDocs.Add(cd);
                }
                chunkIdx++;
            }
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
        
        // v0.13.3 缺陷69 根治: chunk 文档入索引 (关键词/类型索引复用主文档的 — chunk 检索靠向量):
        foreach (var cd in chunkDocs)
        {
            lock (_lock)
            {
                UpdateKeywordIndex(cd);
                UpdateTypeIndex(cd);
                _documents[cd.Id] = cd;
            }
        }
        
        _logger.LogDebug("Indexed document {DocumentId} (+{ChunkN} chunks)", document.Id, chunkDocs.Count);
        PersistDocument(document);
        
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
            
            // R404 (用户钦定): 融合路 —— 优化后的 bge 形态 (bge-base 语义路 + 词法路 + RRF)。
            // 纯 RRF 打分: 不做内容命中下限补偿 / IDF 加成 (那是词袋档补丁, 冻结口径里不存在),
            // 分数线性归一到 0..1 后再与调用方 MinScore 比较 (RRF 原始分数量纲 ≈ 0.18, 不归一会被阈值全砍)。
            if (_fusion is not null)
            {
                var pool = new List<RetrievalCandidate>();
                foreach (var d in candidates)
                {
                    if (d.Embedding is null && string.IsNullOrEmpty(d.Content)) continue;
                    var cand = new RetrievalCandidate
                    {
                        Id = d.Id,
                        Text = d.Content ?? string.Empty,
                        Embedding = d.Embedding,
                    };
                    if (_bigramMemo.TryGetValue(d.Id, out var memo) && memo.Stamp == d.UpdatedAt)
                    {
                        cand.Bigrams = memo.Grams;
                        _fusion.Counters.BigramMemoHits++;
                    }
                    else
                    {
                        _bigramMemo[d.Id] = (d.UpdatedAt, cand.Bigrams);
                    }
                    pool.Add(cand);
                }

                var ranked = _fusion.Rank(new QueryContext(request.Query, queryEmbedding), pool);
                var max = _fusion.MaxScore();
                foreach (var kv in ranked)
                {
                    var norm = max > 0 ? kv.Value / max : 0.0;
                    if (request.MinScore.HasValue && norm < request.MinScore.Value) continue;
                    if (!_documents.TryGetValue(kv.Key.Id, out var doc)) continue;
                    if (!seen.Add(doc.Id)) continue;
                    results.Add(new RecallResult
                    {
                        Document = doc,
                        Score = norm,
                        HighlightedContent = HighlightContent(doc.Content, queryKeywords),
                        Rank = 0,
                        MatchType = "rrf",
                    });
                }
            }

            // 语义搜索
            if (_fusion is null && (_config.EnableHybridSearch || request.TopK > 0))
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
                    {
                        // v0.13.3 R267 (B 期靶点: 短查询判别力 0.45→): 稀缺词 IDF 加权 —
                        // query 词命中数 × log(N/df): 每篇都有的模板词 (df≈N) 加权≈0, 稀缺词 (df=1-2) 加权高。
                        var totalDocs = Math.Max(1, _documents.Count);
                        var rarityBoost = 0.0;
                        foreach (var k in queryKeywords)
                        {
                            if (k.Length < 2 || !doc.Content.Contains(k, StringComparison.OrdinalIgnoreCase)) continue;
                            var df = _keywordIndex.TryGetValue(k, out var ids) ? ids.Count : 0;
                            if (df == 0) df = 1; // keywordIndex 未收录但内容命中的词 — 视为极稀缺
                            rarityBoost += Math.Log(1 + (double)totalDocs / df) * 0.08;
                        }
                        finalScore = Math.Max(finalScore, 0.45 + Math.Min(0.35, rarityBoost));
                    }

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
            if (_fusion is null && _config.EnableHybridSearch)
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
        
        // v0.13.3 缺陷69 根治 (chunk→parent 归并): 所有结果按父 Id 归并取最高分 —
        // 主文档与它的 chunks 会同时命中 (诊断实证: 同 Id 两条 0.45/0.90 占坑), 不归并 → 重复占坑挤掉其他文档。
        // 词袋档补偿: chunk 分数 × chunk 数 ≈ 全文粒度分数。
        var bestByParent = new Dictionary<string, RecallResult>(StringComparer.Ordinal);
        foreach (var r in finalResults)
        {
            var docId = r.Document?.Id ?? string.Empty;
            var hashIdx = docId.IndexOf("#c", StringComparison.Ordinal);
            var parentId = hashIdx > 0 ? docId[..hashIdx] : docId;
            RecallResult effective;
            if (hashIdx > 0 && _documents.TryGetValue(parentId, out var parent))
            {
                // A3e (诊断实证): 补偿倍增 (×chunk_count) 让弱相关 chunk 压过强相关主文档 (q1 实证:
                // 无关文档 chunk 1.35 分压过期望文档 0.90) — chunk 分数不放大, 与主文档分数同池取 max。
                effective = new RecallResult
                {
                    Document = parent,
                    Score = r.Score,
                    HighlightedContent = r.HighlightedContent,
                    Rank = r.Rank,
                    MatchType = r.MatchType + "+chunk",
                };
            }
            else
            {
                effective = r;
            }
            if (!bestByParent.TryGetValue(parentId, out var prev) || effective.Score > prev.Score)
                bestByParent[parentId] = effective;
        }
        var parentMapped = bestByParent.Values
            .OrderByDescending(r => r.Score)
            .ToList();
        for (int i = 0; i < parentMapped.Count; i++) parentMapped[i].Rank = i + 1;

        // ── 精排段 (用户钦定 KPI 2026-09-19; 口径 docs/evidence/RF0001/KPI.md §5) ──
        // 漏斗: 召回 → 粗排(RRF 融合, 上方已做) → **精排(此处)** → 装配。
        // 铁律: ① 只重排池内候选 (不扩召回); ② 产物只影响顺序 ⇒ 恒前缀不受影响 (命中率 ≥97% 不得破);
        //       ③ 遥测: RerankApplied / LastRerankSwaps 非零才算"生效" (有代码行 ≠ 生效)。
        parentMapped = ApplyRerank(parentMapped, request.Query);

        _logger.LogInformation("Recall returned {Count} results for query: {Query}", parentMapped.Count, request.Query);
        
        return Task.FromResult(parentMapped);
    }
    
    /// <summary>精排段真正执行的次数 (生效证据; 恒 0 ⇒ 该段是孤岛)。</summary>
    public int RerankApplied { get; private set; }

    /// <summary>最近一次精排相对粗排序的错位数 (0 = 精排未改变顺序 ⇒ 打分器未生效)。</summary>
    public int LastRerankSwaps { get; private set; }

    /// <summary>
    /// 精排段: 对**已召回池**重排序 (只重排, 不扩召回), 稳定确定 (同分按粗排序), 并写回 Rank。
    /// 精排只作用于 prompt 的可变区 ⇒ 恒前缀与缓存命中率不受影响。
    /// </summary>
    private List<RecallResult> ApplyRerank(List<RecallResult> coarse, string query)
    {
        LastRerankSwaps = 0;
        if (!_config.RerankEnabled || coarse.Count < 2) return coarse;
        var pool = new RerankCandidate[coarse.Count];
        for (var i = 0; i < coarse.Count; i++)
        {
            pool[i] = new RerankCandidate(
                coarse[i].Document?.Id ?? string.Empty,
                coarse[i].Document?.Content ?? string.Empty,
                coarse[i].Score);
        }
        var idx = RerankStage.OrderIndices(pool, query, _rerank);
        var ordered = new List<RecallResult>(coarse.Count);
        for (var i = 0; i < idx.Length; i++)
        {
            if (idx[i] != i) LastRerankSwaps++;
            ordered.Add(coarse[idx[i]]);
        }
        for (var i = 0; i < ordered.Count; i++) ordered[i].Rank = i + 1;
        RerankApplied++;
        return ordered;
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
        // v0.13.3 真缺陷 69 修复 (bge 召回测量实证): bge ctx=512, 全文 (~730tok/500tok 样本) 超窗 →
        // LLamaSharp ArgumentException → IndexAsync 失败/静默回退词袋。修复: embedding 输入截断至
        // 安全窗 (440ch ≈ 460tok), 与 RAG chunking 语义一致 (首块优先); 词袋档无窗口限制不截断。
        if (_config.EmbeddingFunction != null)
        {
            const int maxEmbedChars = 440;
            var embedInput = text.Length > maxEmbedChars ? text[..maxEmbedChars] : text;
            return _config.EmbeddingFunction(embedInput);
        }

        // 改进的 embedding 实现：为每个词分配一个维度位置
        var words = Tokenize(text);
        var dimension = _config.EmbeddingDimension;
        var embedding = new float[dimension];
        
        // 使用词袋模型：将每个词哈希到不同维度 (R422 附带修复)
        // 真缺陷: 原为 `Math.Abs(word.GetHashCode())` + `(hash + seed * 31337) % dimension`:
        //   ① string.GetHashCode() 在 .NET 中**进程随机化** ⇒ 同一文档跨进程向量不同 (落盘索引不可复现);
        //   ② 加法**可溢出为负** (hash 落在 int.MaxValue-62674 窗口) ⇒ `% dimension` 为负 ⇒ `embedding[负]`
        //      ⇒ IndexOutOfRangeException。实测概率 ~20%/进程 (R422 基线取证: 全量与隔离两跑各红 2 例,
        //      随后 6 连跑全绿; 700 文档 × ~20 token ⇒ 每进程期望溢出次数 ~0.2)。
        // 修: FNV-1a 确定性哈希 + **无符号**取模 (恒非负)。两处均抽为可被测试**确定性**钉住的 internal 助手。
        for (int wordIndex = 0; wordIndex < words.Count; wordIndex++)
        {
            var hash = StableHash(words[wordIndex]);

            // 将词分布到多个维度（使用不同种子）
            for (int seed = 0; seed < 3; seed++)
            {
                embedding[BucketOf(hash, seed, dimension)] += 1.0f;
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
    
    /// <summary>
    /// R422 附带修复: FNV-1a (32 位) —— 确定性、跨进程/跨平台一致, 替代进程随机化的 string.GetHashCode()。
    /// 契约: 同输入恒同输出 (可被测试跨实现对账钉住)。
    /// </summary>
    internal static uint StableHash(string s)
    {
        unchecked
        {
            var h = 2166136261u;
            for (int i = 0; i < s.Length; i++)
            {
                h ^= s[i];
                h *= 16777619u;
            }
            return h;
        }
    }

    /// <summary>
    /// R422 附带修复: 词元哈希 → 桶下标。**无符号**运算 ⇒ 结果恒在 [0, dimension);
    /// 旧实现 `(hash + seed * 31337) % dimension` 在有符号域可溢出为负 ⇒ 负下标 IndexOutOfRange。
    /// </summary>
    internal static int BucketOf(uint hash, int seed, int dimension)
    {
        ArgumentOutOfRangeException.ThrowIfLessThan(dimension, 1);
        unchecked
        {
            return (int)((hash + (uint)seed * 31337u) % (uint)dimension);
        }
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
    
    /// <summary>R109 fix#41: 归一化内容指纹 — 小写/压空白/去标点差异, 用于同内容写入去重</summary>
    private static string NormalizeForDedup(string content)
    {
        if (string.IsNullOrWhiteSpace(content)) return string.Empty;
        // 只保留字母数字 (Unicode 类别), 丢弃空白+全部标点 (全角/半角差异一并归零) — 防同内容因标点变体漏判
        var buf = new char[content.Length];
        int n = 0;
        foreach (var ch in content)
        {
            if (char.IsLetterOrDigit(ch)) buf[n++] = char.ToLowerInvariant(ch);
        }
        var normalized = new string(buf, 0, n);
        // 64-bit FNV-1a — 零反射、无 crypto 依赖 (AOT)
        ulong h = 14695981039346656037UL;
        foreach (var c in normalized) { h ^= c; h *= 1099511628211UL; }
        return h.ToString(System.Globalization.CultureInfo.InvariantCulture);
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
