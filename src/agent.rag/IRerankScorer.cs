namespace agent.rag;

/// <summary>
/// 精排打分器 (第二级相关性模型)。实现可以是本地模型 (cross-encoder / 本地 LLM 精准 prompt 产结构化序),
/// 也可以是零依赖词法基线; 但**不得**引入任何判定词表 (用户钦定: 不造特定词表)。
/// 本地模型承担精排 = 「本地 LLM 角色变更」的落点 (远端只做生成)。
/// </summary>
public interface IRerankScorer
{
    /// <param name="query">查询原文。</param>
    /// <param name="document">候选正文。</param>
    /// <param name="coarseScore">粗排分 (线性归一后可直接融合)。</param>
    double Score(string query, string document, double coarseScore);
}
