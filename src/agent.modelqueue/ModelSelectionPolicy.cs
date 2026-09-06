namespace agent.modelqueue;

/// <summary>任务种类提示 (C.3.4): 调用方标注本次 LLM 调用的用途, 供计价路由/意图选模。</summary>
public enum TaskKindHint
{
    /// <summary>主回答 (默认, 用主模型)</summary>
    General,

    /// <summary>上下文压缩 (性能不敏感 → 便宜模型)</summary>
    ContextCompression,

    /// <summary>关键词标注 (性能不敏感)</summary>
    KeywordTagging,

    /// <summary>倾向分析 (性能不敏感)</summary>
    TendencyAnalysis,

    /// <summary>意图分类 (轻任务)</summary>
    IntentClassification,
}

/// <summary>
/// 模型选择策略 (C.3.4 + C.6.3):
/// 1. 手动指定最高优先 (/model xxx)
/// 2. 计价策略: 性能不敏感任务 → 便宜模型 (C.6.3 轻意图同路径)
/// 3. 自动: 意图 × 推理需求 × 预估费用 综合打分 (C.6.3)
/// </summary>
public sealed class ModelSelectionPolicy
{
    /// <summary>性能不敏感任务集合 (计价路由)</summary>
    private static readonly TaskKindHint[] LowSensitivityKinds =
    {
        TaskKindHint.ContextCompression,
        TaskKindHint.KeywordTagging,
        TaskKindHint.TendencyAnalysis,
        TaskKindHint.IntentClassification,
    };

    /// <summary>
    /// 选模型 (返回目录条目; 目录空/无匹配 → null 调用方回退默认模型)。
    /// </summary>
    /// <param name="manualOverride">手动指定模型 id (非空 = 最高优先)</param>
    /// <param name="kind">任务种类提示</param>
    /// <param name="intent">意图 (自动模式: 重推理意图→高分模型, 轻意图→flash)</param>
    /// <param name="estimatedTokens">预估输入 token (费用估算)</param>
    /// <param name="estimatedOutputTokens">预估输出 token</param>
    public ModelCatalogEntry? Select(
        string? manualOverride,
        TaskKindHint kind,
        string intent,
        int estimatedTokens,
        int estimatedOutputTokens,
        ModelCatalog catalog)
    {
        // 1. 手动最高优先
        if (!string.IsNullOrEmpty(manualOverride))
            return catalog.Find(manualOverride);

        if (catalog.Models.Count == 0)
            return null;

        // 2. 计价策略: 性能不敏感 → 最便宜可用
        if (LowSensitivityKinds.Contains(kind))
        {
            return catalog.Models
                .OrderBy(m => EstimatedCost(m, estimatedTokens, estimatedOutputTokens))
                .FirstOrDefault();
        }

        // 3. 自动: 意图×能力×费用综合打分 (C.6.3-2)
        // v0.11.0 (打点驱动修复): key 未配置的模型不可调用 → 先过滤 (曾实测选 gpt-4o-mini 而其 env 缺失 → 整轮失败)
        var callable = new List<ModelCatalogEntry>();
        foreach (var m in catalog.Models)
        {
            if (m.Provider != "official" &&
                string.IsNullOrEmpty(Environment.GetEnvironmentVariable(m.ApiKeyEnv)))
                continue;
            callable.Add(m);
        }
        // 全部无 key → 回退全目录 (让调用失败语义给出明确报错, 而非静默无模型)
        var pool = callable.Count > 0 ? callable : catalog.Models;
        ModelCatalogEntry? best = null;
        var bestScore = double.MinValue;
        foreach (var m in pool)
        {
            // fitness: suited_for 命中意图 +2; 推理/编码需求按意图权重
            var fitness = m.SuitedFor.Contains(intent, StringComparer.OrdinalIgnoreCase) ? 2.0 : 0.0;
            var reasoningNeed = IsReasoningHeavyIntent(intent) ? m.ReasoningScore / 10.0 : 0.0;
            var codingNeed = IsCodingIntent(intent) ? m.CodingScore / 10.0 : 0.0;
            // 费用惩罚: 归一化到与 fitness 同量纲 (1 USD 差 ≈ 2 分)
            var cost = EstimatedCost(m, estimatedTokens, estimatedOutputTokens);
            var score = fitness * 2.0 + reasoningNeed * 3.0 + codingNeed * 3.0 - cost * 2.0;
            if (score > bestScore)
            {
                bestScore = score;
                best = m;
            }
        }
        return best;
    }

    /// <summary>预估费用 USD = in_tok/1M×price_in + out_tok/1M×price_out</summary>
    public static double EstimatedCost(ModelCatalogEntry m, int inTok, int outTok) =>
        inTok / 1_000_000.0 * m.PriceInPerM + outTok / 1_000_000.0 * m.PriceOutPerM;

    /// <summary>重推理意图 (planning/debug/reasoning → 需要高分模型)</summary>
    public static bool IsReasoningHeavyIntent(string intent) =>
        intent is "planning" or "debug" or "reasoning" or "architecture";

    /// <summary>编码意图</summary>
    public static bool IsCodingIntent(string intent) =>
        intent is "coding" or "create_project" or "write_test" or "refactor";
}
