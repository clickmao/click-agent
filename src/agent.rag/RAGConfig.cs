using Microsoft.Extensions.Logging;
using System.Text.Json;


namespace agent.rag;

/// <summary>
/// RAG召回配置
/// </summary>
public class RAGConfig
{
    /// <summary>v0.11.0 R109: 落盘路径覆写 (评测隔离用; null = 默认 CWD/BaseDirectory 解析)</summary>
    public string? PersistPathOverride { get; set; }

    public int MaxRecallResults { get; set; } = 10;

    /// <summary>精排段开关 (用户钦定 KPI 2026-09-19)。关 = 退回纯粗排 (RRF 融合) 序; 开 = 召回池经精排重排。</summary>
    public bool RerankEnabled { get; set; } = true;
    public double MinSimilarityScore { get; set; } = 0.3;

    // v0.11.0 R101: 本地向量召回 (bge) — null=纯词面 (默认, AOT 安全);
    // JIT 部署形态由 host 注入 embedding 函数 (BgeEmbeddingProvider.Embed), RAG 层零 LLamaSharp 依赖。
    public Func<string, float[]>? EmbeddingFunction { get; set; }
    public int EmbeddingDimension { get; set; } = 384;
    public bool EnableHybridSearch { get; set; } = true;

    /// <summary>R404 (用户钦定): 检索融合配置 —— null = 关闭 (走旧 hybrid 加权路径, 既有单测不受影响);
    /// 产品 DI 显式开启 = dense 语义路 + 词法路 + RRF(k0=10, w=1:1)。dense 路实际喂的是链上真身
    /// (25.2MB bge-small-zh-v1.5 q8 = bge-q8.gguf) ⇒ **产品口径** 冻结集实测 r@10 0.6333 → 0.7833
    /// (+18 条查询, 配对 p=4e-05), 证据 eval/bge/results/fusion-lex-small-2026-09-14.json。
    /// 旧记的 0.8500 是 dense-base(110MB) 评测对照口径 —— 跨基座混算之误, 已订正
    /// (该权重已按用户令删除; 向量缓存保留 ⇒ 对照读数仍可复现)。</summary>
    public FusionOptions? Fusion { get; set; }
    public List<string> StopWords { get; set; } = new() { "的", "了", "在", "是", "我", "有", "和", "就", "不", "人" };
}
