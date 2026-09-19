namespace agent.rag;

/// <summary>
/// 上下文精排读数 (用户钦定 KPI, 口径见 docs/evidence/RF0001/KPI.md §5)。
/// 四件套缺一不可: NDCG@k (主) / MRR / Precision@k / Recall@N (前置天花板)。
/// 器具有缺口时 <see cref="Status"/> 必须写 `未测(器具有缺口)` —— 禁以 0 或空白代替读数。
/// </summary>
public readonly record struct RerankReading(
    double NdcgAtK,
    double Mrr,
    double PrecisionAtK,
    double RecallAtN,
    int K,
    string Status)
{
    /// <summary>单行台账形态 (KPI 表 / 日志用, 无本地化依赖)。</summary>
    public string Line() =>
        $"rerank k={K} ndcg={NdcgAtK:F4} mrr={Mrr:F4} p@k={PrecisionAtK:F4} recall@N={RecallAtN:F4} status={Status}";
}
