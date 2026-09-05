using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.skills;

/// <summary>
/// Skill 调度器 (S.2 SkillDispatcher — 对外唯一入口, V2 阶段一接线点)。
/// DispatchAsync: 匹配 → 命中 → 生成 SkillResult (normative: force_template 原样承载 + 禁语校验;
/// executive: entry 委托) → 合并 (force_use 独占口径)。异常自动降级 (返回未命中, 不阻塞主链)。
/// </summary>
public sealed class SkillDispatcher
{
    private readonly SkillRegistry _registry;
    private readonly TriggerMatcher _matcher;

    /// <summary>executive 执行委托注册表 (entry → 委托; P1 仅注册制, 不做文件加载)</summary>
    private readonly Dictionary<string, Func<string, CancellationToken, Task<string>>> _entries = new();

    public SkillDispatcher(SkillRegistry registry, TriggerMatcher? matcher = null)
    {
        _registry = registry;
        _matcher = matcher ?? new TriggerMatcher();
    }

    public void RegisterEntry(string skillId, Func<string, CancellationToken, Task<string>> entry) =>
        _entries[skillId] = entry;

    /// <summary>便捷注册 (转发 Registry — 测试/动态注册同 API)</summary>
    public void Register(SkillDefinition skill) => _registry.Register(skill);

    /// <summary>调度入口 (V2 主链阶段一: 推理前调用)。返回 null = 未命中/降级 → 走普通推理。</summary>
    public async Task<SkillResult?> DispatchAsync(string input, CancellationToken ct = default)
    {
        try
        {
            var hits = _matcher.Match(input, _registry.All);
            if (hits.Count == 0)
                return null;

            var top = hits[0];
            var sw = System.Diagnostics.Stopwatch.StartNew();

            string content;
            var forceUse = false;
            if (top.Skill.Type == SkillType.Normative)
            {
                // 口径型: force_template 原样承载 (S.6: 模型只做合规润色, 不改口径)
                if (string.IsNullOrEmpty(top.Skill.ForceTemplate))
                    return null;
                content = top.Skill.ForceTemplate.Replace("{input}", input);
                forceUse = true;
            }
            else
            {
                // 执行型: entry 委托
                if (!_entries.TryGetValue(top.Skill.SkillId, out var entry))
                    return null;
                content = await entry(input, ct);
            }

            // 禁语校验 (normative 口径保护)
            foreach (var w in top.Skill.ForbiddenWords)
            {
                if (w.Length > 0 && content.Contains(w, StringComparison.OrdinalIgnoreCase))
                {
                    return new SkillResult
                    {
                        SkillId = top.Skill.SkillId,
                        Success = false,
                        Content = string.Empty,
                        ForbiddenHit = w,
                        ElapsedMs = sw.ElapsedMilliseconds,
                    };
                }
            }

            return new SkillResult
            {
                SkillId = top.Skill.SkillId,
                Success = true,
                Content = content,
                ForceUse = forceUse,
                ElapsedMs = sw.ElapsedMilliseconds,
            };
        }
        catch (Exception)
        {
            // 降级: Skill 入口异常 → 回普通推理 (S.5: 用户无感, 错误只进日志 — 调用方记)
            return null;
        }
    }
}

[JsonSerializable(typeof(SkillResult))]
[JsonSourceGenerationOptions(DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull)]
public partial class SkillJsonContext : JsonSerializerContext
{
}
