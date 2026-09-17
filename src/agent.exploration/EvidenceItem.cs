namespace agent.exploration;


/// <summary>单条依据 (探索/检索所得)。</summary>
public sealed class EvidenceItem
{
    public string Ref { get; set; } = string.Empty;          // URL/文件/RAG id
    public string Domain { get; set; } = string.Empty;       // 来源域 (URL host / 文件根)
    public double SourceHistoryConfidence { get; set; } = 0.5; // think-memory 历史置信
    public double Relevance { get; set; } = 0.5;             // bge 相似度 (与问题)
    public bool SupportsClaim { get; set; } = true;          // 是否支持当前论断
}
