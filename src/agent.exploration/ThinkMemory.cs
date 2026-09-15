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
    /// <summary>
    /// R449: 引用"依据"真正被采纳的次数 (refs 命中)。原实现把 HitCount 兼作此用,
    /// 但仅在 reference 命中 Refs 时才自增 ⇒ refs 全空时 HitCount 恒 0, 「被引用」无法计数。
    /// 现: HitCount = 被引用次数(无条件), RefHitCount = 其中命中具体依据的次数。
    /// </summary>
    public int RefHitCount { get; set; }
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

/// <summary>
/// R449: think-memory 总开关 — 最低面实现 (宿主零改动, 默认档零产品变更)。
/// 环境变量 <c>AGENTFRAMEWORK_THINK_MEMORY</c>:
///   未设 / "1" / "on" / "true" ⇒ On (现网行为, 默认)
///   "off"        ⇒ 全关: 不加载 / 不写入 / 不召回 / 不落盘 (库文件 mtime 不变)
///   "recall0"    ⇒ 禁召回 (仍写入): 用于 A/B 消融「召回是否有用」
///   "write0"     ⇒ 禁写入 (仍召回): 用于 A/B 消融「写入是否有用」
/// 取值在进程启动时读一次 (AOT 安全, 无反射); 测试可经 Mode 参数注入。
/// </summary>
public static class ThinkMemorySwitch
{
    public enum Mode { On = 0, Off = 1, RecallOff = 2, WriteOff = 3 }

    /// <summary>进程级档位 (env 读一次)。</summary>
    public static readonly Mode Current = Parse(Environment.GetEnvironmentVariable("AGENTFRAMEWORK_THINK_MEMORY"));

    /// <summary>未知取值 ⇒ On (fail-open: 开关本身不得成为主链故障点)。</summary>
    public static Mode Parse(string? raw) => (raw ?? string.Empty).Trim().ToLowerInvariant() switch
    {
        "off" or "0" or "false" or "disable" or "disabled" => Mode.Off,
        "recall0" or "recall-off" or "no-recall" => Mode.RecallOff,
        "write0" or "write-off" or "no-write" => Mode.WriteOff,
        _ => Mode.On,
    };

    public static string Name(Mode m) => m switch
    {
        Mode.Off => "off", Mode.RecallOff => "recall0", Mode.WriteOff => "write0", _ => "on",
    };
}

/// <summary>
/// R449: think-memory 计数器 — 反「空心读数」闸。任何「开关有效果」的结论必须先满足
/// <c>Recalls &gt; 0</c> (尝试过召回) 或 <c>Writes &gt; 0</c>, 否则该臂记 n/a 而不是 0
/// (R380 铁律: 「没测到」≠「测过通过/无效果」)。
/// </summary>
public static class ThinkMemoryStats
{
    private static int _writes, _writesSuppressed, _negativeWrites, _unbackedWrites;
    private static int _recalls, _recallsSuppressed, _recallHits, _dimMismatch;
    private static int _hits, _refHits, _loaded;

    public static void RecordWrite(bool isNegative, int refCount)
    {
        Interlocked.Increment(ref _writes);
        if (isNegative) Interlocked.Increment(ref _negativeWrites);
        if (refCount <= 0) Interlocked.Increment(ref _unbackedWrites);
    }

    public static void RecordWriteSuppressed() => Interlocked.Increment(ref _writesSuppressed);
    public static void RecordRecallAttempt() => Interlocked.Increment(ref _recalls);
    public static void RecordRecallSuppressed() => Interlocked.Increment(ref _recallsSuppressed);
    public static void RecordRecallHits(int n) { if (n > 0) Interlocked.Add(ref _recallHits, n); }
    public static void RecordDimMismatch() => Interlocked.Increment(ref _dimMismatch);
    public static void RecordHit() => Interlocked.Increment(ref _hits);
    public static void RecordRefHit() => Interlocked.Increment(ref _refHits);
    public static void RecordLoaded(int n) => Interlocked.Add(ref _loaded, n);

    public static (int Writes, int WritesSuppressed, int NegativeWrites, int UnbackedWrites,
                   int Recalls, int RecallsSuppressed, int RecallHits, int DimMismatch,
                   int Hits, int RefHits, int Loaded) Snapshot()
        => (Volatile.Read(ref _writes), Volatile.Read(ref _writesSuppressed), Volatile.Read(ref _negativeWrites),
            Volatile.Read(ref _unbackedWrites), Volatile.Read(ref _recalls), Volatile.Read(ref _recallsSuppressed),
            Volatile.Read(ref _recallHits), Volatile.Read(ref _dimMismatch), Volatile.Read(ref _hits),
            Volatile.Read(ref _refHits), Volatile.Read(ref _loaded));

    /// <summary>测试/测量用 (生产不调用)。</summary>
    public static void Reset()
    {
        Interlocked.Exchange(ref _writes, 0); Interlocked.Exchange(ref _writesSuppressed, 0);
        Interlocked.Exchange(ref _negativeWrites, 0); Interlocked.Exchange(ref _unbackedWrites, 0);
        Interlocked.Exchange(ref _recalls, 0); Interlocked.Exchange(ref _recallsSuppressed, 0);
        Interlocked.Exchange(ref _recallHits, 0); Interlocked.Exchange(ref _dimMismatch, 0);
        Interlocked.Exchange(ref _hits, 0); Interlocked.Exchange(ref _refHits, 0);
        Interlocked.Exchange(ref _loaded, 0);
    }
}

/// <summary>R449: 库形状快照 (只读; 供普查/遥测 — 不含内容)。</summary>
public sealed class ThinkMemoryShape
{
    public int Count { get; set; }
    public int Negative { get; set; }
    public int Unbacked { get; set; }
    public int ZeroDim { get; set; }
    public int HitPositive { get; set; }
    public int RefHitPositive { get; set; }
    public string Dimensions { get; set; } = string.Empty;
    public string Mode { get; set; } = "on";
}

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
