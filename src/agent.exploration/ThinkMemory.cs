namespace agent.exploration;

public sealed class ThinkMemory
{
    private readonly ThinkMemoryConfig _config;
    private readonly ThinkMemorySwitch.Mode _mode;
    private readonly List<ThinkRecord> _records = new();
    private readonly object _lock = new();

    public ThinkMemory(ThinkMemoryConfig? config = null, ThinkMemorySwitch.Mode? mode = null)
        => (_config, _mode) = (config ?? new ThinkMemoryConfig(), mode ?? ThinkMemorySwitch.Current);

    /// <summary>R449: 本实例档位 (遥测/普查可见)。</summary>
    public string ModeName => ThinkMemorySwitch.Name(_mode);

    public int Count { get { lock (_lock) return _records.Count; } }

    /// <summary>R449: 库形状快照 (只读计数, 无内容) — 供普查与「非空心」判据。</summary>
    public ThinkMemoryShape Shape()
    {
        lock (_lock)
        {
            var dims = _records.Where(r => r.QuestionEmbedding is { Length: > 0 })
                .GroupBy(r => r.QuestionEmbedding!.Length)
                .OrderByDescending(g => g.Count())
                .Select(g => g.Key + ":" + g.Count());
            return new ThinkMemoryShape
            {
                Count = _records.Count,
                Negative = _records.Count(r => r.Outcome == "negative"),
                Unbacked = _records.Count(r => r.Refs.Count == 0),
                ZeroDim = _records.Count(r => r.QuestionEmbedding is null || r.QuestionEmbedding.Length == 0),
                HitPositive = _records.Count(r => r.HitCount > 0),
                RefHitPositive = _records.Count(r => r.RefHitCount > 0),
                Dimensions = string.Join("|", dims),
                Mode = ModeName,
            };
        }
    }

    /// <summary>写入 (高质量思考; 低置信/负样本同样可写 — outcome 标记供降权)。
    /// R449: `write0`/`off` 档抑制写入 (但计数可见 — 反空心)。</summary>
    public string Write(ThinkRecord record)
    {
        if (_mode is ThinkMemorySwitch.Mode.Off or ThinkMemorySwitch.Mode.WriteOff)
        {
            ThinkMemoryStats.RecordWriteSuppressed();
            return record.Id;
        }
        lock (_lock) _records.Add(record);
        ThinkMemoryStats.RecordWrite(record.Outcome == "negative", record.Refs.Count);
        return record.Id;
    }

    /// <summary>
    /// 联想检索: 余弦相似度 ≥ 阈值; 负样本降权; 返回按 (相似度×置信) 排序的命中,
    /// PreferredRefs = 历史高置信链接 (用户钦定: 链接过多时凭 RAG 偏好优先阅览)。
    /// </summary>
    public IReadOnlyList<ThinkMemoryHit> Recall(float[] questionEmbedding, int topK = 3)
    {
        ThinkMemoryStats.RecordRecallAttempt();   // R449: 尝试计数先行 (反空心: 结论必须能引用它)
        if (_mode is ThinkMemorySwitch.Mode.Off or ThinkMemorySwitch.Mode.RecallOff)
        {
            ThinkMemoryStats.RecordRecallSuppressed();
            return Array.Empty<ThinkMemoryHit>();
        }
        lock (_lock)
        {
            var hits = new List<(ThinkRecord r, double sim, double rank)>();
            foreach (var r in _records)
            {
                if (r.QuestionEmbedding is null || r.QuestionEmbedding.Length == 0) continue;
                if (r.QuestionEmbedding.Length != questionEmbedding.Length)
                {
                    // R449: 维度不一致原被静默吃成 sim=0 (记录不可达但读数看不见) ⇒ 显式计数
                    ThinkMemoryStats.RecordDimMismatch();
                    continue;
                }
                var sim = Cosine(questionEmbedding, r.QuestionEmbedding);
                if (sim < _config.MinSimilarity) continue;
                var penalty = r.Outcome == "negative" ? _config.NegativePenalty : 1.0;
                hits.Add((r, sim, sim * Math.Max(0.05, r.AvgConfidence) * penalty));
            }
            var ordered = hits.OrderByDescending(h => h.rank)
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
            ThinkMemoryStats.RecordRecallHits(ordered.Count);
            return ordered;
        }
    }

    /// <summary>
    /// 用户钦定核心: 历史链接被本次思考引用并采纳 → 稍微提升其置信度 (+0.05, 上限 1.0),
    /// 并计一次命中 (供衰减逻辑豁免)。
    /// </summary>
    public bool ApplyCitationBoost(string recordId, string reference)
    {
        if (_mode == ThinkMemorySwitch.Mode.Off) return false;   // R449: off 档不改库
        lock (_lock)
        {
            var r = _records.FirstOrDefault(x => x.Id == recordId);
            if (r is null) return false;
            // R449 修复: 「被引用一次」无条件计数。原实现只在 reference 命中 Refs 时才 HitCount++,
            // 而写入侧 refs 恒空 ⇒ HitCount 永远 0, 衰减逻辑 (HitCount>0 豁免) 与遥测双失效。
            r.HitCount++;
            ThinkMemoryStats.RecordHit();
            var i = r.Refs.FindIndex(x => string.Equals(x, reference, StringComparison.OrdinalIgnoreCase));
            if (i < 0) return false;
            r.RefHitCount++;
            ThinkMemoryStats.RecordRefHit();
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
        if (_mode == ThinkMemorySwitch.Mode.Off) return;   // R449: off 档不落盘 ⇒ 库文件 mtime 不变 (可机检)
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

    /// <summary>加载 (宿主启动时调用; 文件缺失/损坏 → 空库启动, 行为兼容)。
    /// R449: 可注入档位; `off` 档不读盘 ⇒ 空库 (库文件不被触碰)。</summary>
    public static ThinkMemory Load(string path, ThinkMemorySwitch.Mode? mode = null)
    {
        var mem = new ThinkMemory(null, mode);
        if (mem._mode == ThinkMemorySwitch.Mode.Off) return mem;
        try
        {
            if (!File.Exists(path)) return mem;
            using var fs = File.OpenRead(path);
            var records = System.Text.Json.JsonSerializer.Deserialize(fs, ExplorationJsonContext.Default.ListThinkRecord);
            if (records != null)
            {
                lock (mem._lock) mem._records.AddRange(records);
                ThinkMemoryStats.RecordLoaded(records.Count);
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
