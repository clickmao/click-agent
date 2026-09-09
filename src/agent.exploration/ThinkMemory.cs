namespace agent.exploration;

/// <summary>
/// v0.13.0 T3 M-B — 思考记忆 (RAG 联想, 用户钦定核心):
/// 高质量思考收敛后写入 (问题向量+依据链接+置信度); 新思考检索相似历史 →
/// 优先阅览历史高置信度链接; 被引用后稍微提升置信度 (+boost, 上限 1.0)。
/// 负样本思考降权; 30 天未命中衰减 (由宿主定期整理调用 Decay)。
/// 纯内存模型 (持久化由 RAG 命名空间 think-memory 承担, 本类只管语义)。
/// </summary>
public sealed class ThinkRecord
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N")[..16];
    /// <summary>问题 embedding (bge, 宿主侧生成后注入; 本类不算向量 — AOT 约束)</summary>
    public float[]? QuestionEmbedding { get; set; }
    /// <summary>问题原文头 256ch (展示/调试)</summary>
    public string QuestionHead { get; set; } = string.Empty;
    /// <summary>本次思考引用的依据 (URL/文件)</summary>
    public List<string> Refs { get; set; } = new();
    /// <summary>各依据置信度快照 (与 Refs 对齐)</summary>
    public List<double> RefConfidences { get; set; } = new();
    public double AvgConfidence { get; set; }
    /// <summary>positive (验证有效) / negative (证伪/幻觉) — 负样本检索降权</summary>
    public string Outcome { get; set; } = "positive";
    public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
    /// <summary>历史命中引用次数</summary>
    public int HitCount { get; set; }
}

public sealed class ThinkMemoryConfig
{
    /// <summary>检索相似度阈值 (保守 — bge 小模型语义漂移防护)</summary>
    public double MinSimilarity { get; set; } = 0.75;
    /// <summary>引用命中后的置信提升量 (用户钦定 "稍微提升")</summary>
    public double CitationBoost { get; set; } = 0.05;
    /// <summary>置信上限</summary>
    public double MaxConfidence { get; set; } = 1.0;
    /// <summary>长期未命中衰减量 (30 天未引用)</summary>
    public double DecayAmount { get; set; } = 0.10;
    public int DecayAfterDays { get; set; } = 30;
    /// <summary>衰减后归档线</summary>
    public double ArchiveBelow { get; set; } = 0.30;
    /// <summary>负样本思考的检索降权乘数</summary>
    public double NegativePenalty { get; set; } = 0.5;
}

public sealed class ThinkMemoryHit
{
    public ThinkRecord Record { get; set; } = new();
    public double Similarity { get; set; }
    /// <summary>命中后前置的优先阅览链接 (按历史置信降序)</summary>
    public List<string> PreferredRefs { get; set; } = new();
}

public sealed class ThinkMemory
{
    private readonly ThinkMemoryConfig _config;
    private readonly List<ThinkRecord> _records = new();
    private readonly object _lock = new();

    public ThinkMemory(ThinkMemoryConfig? config = null) => _config = config ?? new ThinkMemoryConfig();

    public int Count { get { lock (_lock) return _records.Count; } }

    /// <summary>写入 (高质量思考; 低置信/负样本同样可写 — outcome 标记供降权)。</summary>
    public string Write(ThinkRecord record)
    {
        lock (_lock) _records.Add(record);
        return record.Id;
    }

    /// <summary>
    /// 联想检索: 余弦相似度 ≥ 阈值; 负样本降权; 返回按 (相似度×置信) 排序的命中,
    /// PreferredRefs = 历史高置信链接 (用户钦定: 链接过多时凭 RAG 偏好优先阅览)。
    /// </summary>
    public IReadOnlyList<ThinkMemoryHit> Recall(float[] questionEmbedding, int topK = 3)
    {
        lock (_lock)
        {
            var hits = new List<(ThinkRecord r, double sim, double rank)>();
            foreach (var r in _records)
            {
                if (r.QuestionEmbedding is null || r.QuestionEmbedding.Length == 0) continue;
                var sim = Cosine(questionEmbedding, r.QuestionEmbedding);
                if (sim < _config.MinSimilarity) continue;
                var penalty = r.Outcome == "negative" ? _config.NegativePenalty : 1.0;
                hits.Add((r, sim, sim * Math.Max(0.05, r.AvgConfidence) * penalty));
            }
            return hits.OrderByDescending(h => h.rank)
                .Take(topK)
                .Select(h => new ThinkMemoryHit
                {
                    Record = h.r,
                    Similarity = Math.Round(h.sim, 4),
                    PreferredRefs = h.r.Refs
                        .Zip(h.r.RefConfidences, (reference, c) => (reference, c))
                        .OrderByDescending(x => x.c)
                        .Select(x => x.reference)
                        .ToList(),
                })
                .ToList();
        }
    }

    /// <summary>
    /// 用户钦定核心: 历史链接被本次思考引用并采纳 → 稍微提升其置信度 (+0.05, 上限 1.0),
    /// 并计一次命中 (供衰减逻辑豁免)。
    /// </summary>
    public bool ApplyCitationBoost(string recordId, string reference)
    {
        lock (_lock)
        {
            var r = _records.FirstOrDefault(x => x.Id == recordId);
            if (r is null) return false;
            r.HitCount++;
            var i = r.Refs.FindIndex(x => string.Equals(x, reference, StringComparison.OrdinalIgnoreCase));
            if (i < 0) return false;
            r.RefConfidences[i] = Math.Min(_config.MaxConfidence, r.RefConfidences[i] + _config.CitationBoost);
            r.AvgConfidence = r.RefConfidences.Count > 0 ? r.RefConfidences.Average() : r.AvgConfidence;
            return true;
        }
    }

    /// <summary>定期衰减 (宿主调用): 指定时刻起 DecayAfterDays 天未命中的记录置信 -decay。</summary>
    public int Decay(DateTime utcNow)
    {
        var n = 0;
        lock (_lock)
        {
            foreach (var r in _records)
            {
                if (r.HitCount > 0) continue; // 命中过的不衰减 (本轮简化: 命中清零计数)
                if ((utcNow - r.CreatedAtUtc).TotalDays < _config.DecayAfterDays) continue;
                r.RefConfidences = r.RefConfidences.Select(c => Math.Max(0.0, c - _config.DecayAmount)).ToList();
                r.AvgConfidence = r.RefConfidences.Count > 0 ? r.RefConfidences.Average() : r.AvgConfidence;
                r.HitCount = 0;
                n++;
            }
        }
        return n;
    }

    /// <summary>归档候选 (置信 < 阈值 — 宿主决定移除或降权存储)。</summary>
    public IReadOnlyList<string> ArchiveCandidates()
    {
        lock (_lock)
            return _records.Where(r => r.AvgConfidence < _config.ArchiveBelow).Select(r => r.Id).ToList();
    }
    /// <summary>
    /// v0.13.3 R283: 持久化 — 联想库进程重启后保留 (STJ source-gen, AOT 铁律)。
    /// 保存路径由宿主给 (./data/think-memory.json); 失败静默 (联想库非关键路径)。
    /// </summary>
    public void Save(string path)
    {
        try
        {
            List<ThinkRecord> snapshot;
            lock (_lock) snapshot = new List<ThinkRecord>(_records);
            var dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
            using var fs = File.Create(path);
            System.Text.Json.JsonSerializer.Serialize(fs, snapshot, ExplorationJsonContext.Default.ListThinkRecord);
        }
        catch
        {
            // 联想库非关键路径 — 写失败不影响主链 (打点在宿主侧)
        }
    }

    /// <summary>加载 (宿主启动时调用; 文件缺失/损坏 → 空库启动, 行为兼容)。</summary>
    public static ThinkMemory Load(string path)
    {
        var mem = new ThinkMemory();
        try
        {
            if (!File.Exists(path)) return mem;
            using var fs = File.OpenRead(path);
            var records = System.Text.Json.JsonSerializer.Deserialize(fs, ExplorationJsonContext.Default.ListThinkRecord);
            if (records != null)
            {
                lock (mem._lock) mem._records.AddRange(records);
            }
        }
        catch
        {
            // 损坏文件 → 空库启动
        }
        return mem;
    }


    private static double Cosine(float[] a, float[] b)
    {
        if (a.Length != b.Length || a.Length == 0) return 0;
        double dot = 0, na = 0, nb = 0;
        for (var i = 0; i < a.Length; i++) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
        return na == 0 || nb == 0 ? 0 : dot / (Math.Sqrt(na) * Math.Sqrt(nb));
    }
}
