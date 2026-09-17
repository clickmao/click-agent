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
