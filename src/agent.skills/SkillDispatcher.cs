using System.IO;
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
    private readonly SkillExecutor _executor;

    /// <summary>生命周期状态机 (P2: 缓存/话题切换卸载/熔断托管)</summary>
    public SkillLifecycle Lifecycle { get; }

    /// <summary>executive 执行委托注册表 (entry → 委托; P1 仅注册制, 不做文件加载)</summary>
    private readonly Dictionary<string, Func<string, CancellationToken, Task<string>>> _entries = new();

    /// <summary>v0.11.0: 执行型脚本调度器 (SKILL.md 包 scripts/ 目录; null = 未启用脚本执行)</summary>
    private readonly SkillScriptRunner? _scriptRunner;

    public SkillDispatcher(SkillRegistry registry, TriggerMatcher? matcher = null,
        Func<string, string, int, int>? getConfig = null, SkillScriptRunner? scriptRunner = null)
    {
        _registry = registry;
        _matcher = matcher ?? new TriggerMatcher();
        Func<string, string, int, int> cfg = getConfig ?? new Func<string, string, int, int>((_, _, fallback) => fallback); // 未注入配置 → 兜底默认 (测试兼容)
        Lifecycle = new SkillLifecycle(cfg);
        _executor = new SkillExecutor(Lifecycle, cfg);
        _scriptRunner = scriptRunner;
    }

    public void RegisterEntry(string skillId, Func<string, CancellationToken, Task<string>> entry) =>
        _entries[skillId] = entry;

    /// <summary>便捷注册 (转发 Registry — 测试/动态注册同 API)</summary>
    public void Register(SkillDefinition skill) => _registry.Register(skill);

    /// <summary>包脚本默认入口名 (scripts/main.py → main.sh → main.js 顺序探测)。</summary>
    private static string DefaultScriptName(SkillDefinition skill)
    {
        foreach (var name in new[] { "main.py", "main.sh", "main.js" })
        {
            if (File.Exists(Path.Combine(skill.PackageDir ?? string.Empty, "scripts", name)))
                return name;
        }
        return "main.py"; // 不存在时由 ScriptRunner 抛 FileNotFoundException (诚实报错)
    }

    /// <summary>调度入口 (V2 主链阶段一: 推理前调用)。返回 null = 未命中/降级 → 走普通推理。</summary>
    public async Task<SkillResult?> DispatchAsync(string input, CancellationToken ct = default)
    {
        try
        {
            var hits = await _matcher.MatchAsync(input, _registry.All, ct);
            if (hits.Count == 0)
            {
                Lifecycle.ReportRound(false); // 未命中任何域 → Active 项脱域计数
                return null;
            }

            var top = hits[0];

            // P2 熔断: 开启期 → 静默降级普通推理
            if (Lifecycle.IsBreakerOpen(top.Skill.SkillId))
                return null;

            var sw = System.Diagnostics.Stopwatch.StartNew();
            Lifecycle.Activate(top.Skill);

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
                // 执行型: entry 委托 → 经 Executor (超时/幂等重试/熔断上报)
                if (!_entries.TryGetValue(top.Skill.SkillId, out var entry))
                {
                    // v0.11.0: 无显式注册 → 尝试包内脚本 (SKILL.md scripts/; 进程实跑 + @cmd 命令转发)
                    if (_scriptRunner is null || top.Skill.PackageDir is null)
                        return null;
                    var scriptOut = await _executor.ExecuteAsync(top.Skill,
                        token => _scriptRunner.RunAsync(top.Skill, DefaultScriptName(top.Skill), input, token), ct);
                    if (scriptOut is null)
                        return null; // 失败/超时/熔断 → 降级普通推理
                    content = scriptOut;
                }
                else
                {
                    var executed = await _executor.ExecuteAsync(top.Skill,
                        token => entry(input, token), ct);
                    if (executed is null)
                        return null; // 失败/超时/熔断 → 降级普通推理
                    content = executed;
                }
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

            Lifecycle.ReportRound(true, top.Skill.SkillId);

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
