namespace agent.exploration;


/// <summary>
/// v0.13.1 F2 (用户钦定) — 问题级粘性路由记录 (RAG route-memory 语义层)。
/// 成功/失败请求均记录: 相似问题首用成功模型; 已知失败模型避免。
/// </summary>
public sealed class RouteRecord
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N")[..16];
    public float[]? QuestionEmbedding { get; set; }
    public string QuestionHead { get; set; } = string.Empty;
    /// <summary>意图指纹 (双门护栏: 相似度+意图一致才粘)</summary>
    public string Intent { get; set; } = string.Empty;
    /// <summary>实体指纹 (URL/路径等强区分物 — 形近意远防线)</summary>
    public string EntityFingerprint { get; set; } = string.Empty;
    public string ModelId { get; set; } = string.Empty;
    /// <summary>success / fail</summary>
    public string Outcome { get; set; } = "success";
    public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
    public int HitCount { get; set; }
}
