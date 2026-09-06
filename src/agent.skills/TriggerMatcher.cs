using System.Text.RegularExpressions;

namespace agent.skills;

/// <summary>匹配结果 (裁决排序用)</summary>
public sealed class SkillMatch
{
    public SkillDefinition Skill { get; set; } = null!;

    /// <summary>0=未命中 1=疑似(仅领域词) 2=关键词 3=正则精匹配</summary>
    public int Level { get; set; }

    /// <summary>精确度 (正则>关键词>领域词)</summary>
    public double Precision { get; set; }
}

/// <summary>
/// 三级触发匹配 (原文 §5): 一级关键词 → 二级正则精匹配 → 领域词疑似。
/// v0.10.0 P3 语义层: 关键词/正则/领域词全未命中时, 注入 ITextEmbedder (bge) 用
/// 余弦相似度判疑似 (cos ≥ SemanticThreshold = 0.45) — 语义近邻触发。
/// 裁决: 排他 > 优先级 > 精确度 (S.5 冲突四组合覆盖)。
/// </summary>
public sealed class TriggerMatcher
{
    private readonly bool _suspectedTrigger;
    private readonly agent.contextgradient.ITextEmbedder? _embedder;
    private readonly double _semanticThreshold;

    public TriggerMatcher(bool suspectedTrigger = true) : this(null, suspectedTrigger) { }

    /// <summary>v0.10.0 P3: 语义匹配构造 (bge 嵌入器 + 相似度阈值, 默认 0.45)</summary>
    public TriggerMatcher(agent.contextgradient.ITextEmbedder? embedder, bool suspectedTrigger = true,
        double semanticThreshold = 0.45)
    {
        _suspectedTrigger = suspectedTrigger;
        _embedder = embedder;
        _semanticThreshold = semanticThreshold;
    }

    /// <summary>返回全部命中 (已按裁决排序; 空 = 未命中)</summary>
    public List<SkillMatch> Match(string input, List<SkillDefinition> skills, CancellationToken ct = default)
        // sync 边界 (保留兼容): async 主链请用 MatchAsync — 本方法语义等价, 内部一次 GetResult
        => MatchCoreAsync(input, skills, ct).GetAwaiter().GetResult();

    /// <summary>async 匹配主链 (v0.11.0 性能修复: 语义嵌入 await 化, 不再逐 skill GetResult 阻塞线程池线程)。</summary>
    public async Task<List<SkillMatch>> MatchAsync(string input, List<SkillDefinition> skills, CancellationToken ct = default)
        => await MatchCoreAsync(input, skills, ct).ConfigureAwait(false);

    private async Task<List<SkillMatch>> MatchCoreAsync(string input, List<SkillDefinition> skills, CancellationToken ct)
    {
        var hits = new List<SkillMatch>();
        float[]? semanticCos = null; // 本轮输入向量缓存 (惰性嵌入一次)
        foreach (var s in skills)
        {
            var level = 0;
            double precision = 0;

            // 一级: 关键词 (包含匹配)
            var keywordHit = s.Keywords.Any(k =>
                k.Length > 0 && input.Contains(k, StringComparison.OrdinalIgnoreCase));
            if (keywordHit)
            {
                level = 2;
                precision = 0.6;
            }

            // 二级: 正则精匹配 (覆盖一级 — 更精确)
            foreach (var pattern in s.RegexPatterns)
            {
                try
                {
                    if (Regex.IsMatch(input, pattern, RegexOptions.IgnoreCase))
                    {
                        level = 3;
                        precision = 0.95;
                        break;
                    }
                }
                catch (ArgumentException)
                {
                    // 坏正则跳过 (定义文件错误不崩调度)
                }
            }

            // 疑似: 无关键词/正则命中但有领域词
            if (level == 0 && _suspectedTrigger && s.DomainWords.Any(w =>
                    w.Length > 0 && input.Contains(w, StringComparison.OrdinalIgnoreCase)))
            {
                level = 1;
                precision = 0.3;
            }

            // v0.10.0 P3 语义层: 全部词面未命中 → bge 余弦相似度疑似判定
            // (嵌入器不可用/嵌入失败 → 静默跳过, 行为兼容; 语义命中 precision 介于领域词与关键词之间)
            if (level == 0 && _suspectedTrigger && _embedder is { IsAvailable: true } && semanticCos is null)
            {
                try
                {
                    var inputVec = await _embedder.EmbedAsync(input, ct).ConfigureAwait(false);
                    semanticCos = inputVec; // 缓存本轮输入向量 (多 skill 复用一次嵌入)
                }
                catch
                {
                    semanticCos = Array.Empty<float>(); // 失败 → 本轮不再尝试语义
                }
            }
            if (level == 0 && _suspectedTrigger && semanticCos is { Length: > 0 } vec)
            {
                var text = SemanticText(s);
                if (text.Length > 0)
                {
                    try
                    {
                        var skillVec = await _embedder!.EmbedAsync(text, ct).ConfigureAwait(false);
                        var cos = agent.contextgradient.VectorMath.Cosine(vec, skillVec);
                        if (cos >= _semanticThreshold)
                        {
                            level = 1;                       // 语义命中 = 疑似级
                            precision = 0.30 + 0.25 * Math.Min(1.0, (cos - _semanticThreshold) / 0.5);
                        }
                    }
                    catch
                    {
                        // 嵌入失败跳过 — 词面匹配语义不变
                    }
                }
            }

            if (level > 0)
                hits.Add(new SkillMatch { Skill = s, Level = level, Precision = precision });
        }

        // 裁决: 匹配级别 > 排他 > 优先级 > 精确度
        // v0.11.0 (打点驱动修复): 词面强命中 (正则3/关键词2) 不被语义疑似(L1)+排他 抢占 —
        // 实测 bge 短文本基线 cos 偏高 (~0.73), identity 排他恒 top, 淹没 wordcount 正则命中
        return hits
            .OrderByDescending(m => m.Level)
            .ThenByDescending(m => m.Skill.Exclusive)
            .ThenByDescending(m => m.Skill.Priority)
            .ThenByDescending(m => m.Precision)
            .ToList();
    }


    /// <summary>Skill 语义代表文本 (bge 嵌入目标): 名称 + 领域 + 关键词串接</summary>
    private static string SemanticText(SkillDefinition s)
    {
        var parts = new List<string>();
        if (s.Name.Length > 0) parts.Add(s.Name);
        if (s.Domain.Length > 0) parts.Add(s.Domain);
        if (s.Keywords.Count > 0) parts.Add(string.Join(", ", s.Keywords));
        return string.Join(" ", parts);
    }
}
