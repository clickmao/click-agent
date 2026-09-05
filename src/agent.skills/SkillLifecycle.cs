using agent.config;

namespace agent.skills;

/// <summary>Skill 生命周期状态 (原文 §3.4: Unloaded→Loaded→Active→Suspended→Unloaded)</summary>
public enum SkillState
{
    Unloaded,
    Loaded,
    Active,
    Suspended,
}

/// <summary>会话内单个 Skill 的运行时状态</summary>
public sealed class SkillRuntime
{
    public SkillDefinition Skill { get; init; } = null!;
    public SkillState State { get; set; } = SkillState.Unloaded;
    public DateTimeOffset ActivatedAt { get; set; }
    public DateTimeOffset LastUsedAt { get; set; }
    public int OffTopicRounds { get; set; }

    /// <summary>熔断: 连续失败计数 / 熔断开启截止时刻</summary>
    public int ConsecutiveFailures { get; set; }
    public DateTimeOffset BreakerOpenUntil { get; set; }
}

/// <summary>
/// Skill 生命周期状态机 (P2, plan_skill_dispatch.md S.2 SkillLifecycle):
/// 会话级缓存 (上限配置) + 话题切换检测 (连续 N 轮脱域自动卸载) + 挂起/恢复 + 闲置超时回收 +
/// 熔断状态托管 (连续 N 败临时禁用, 到期半开)。全部阈值从 base/skill.yaml 读, 零硬编码。
/// 线程安全: 所有状态读写持锁。
/// </summary>
public sealed class SkillLifecycle
{
    private readonly object _lock = new();
    private readonly Dictionary<string, SkillRuntime> _runtimes = new(StringComparer.OrdinalIgnoreCase);

    private readonly int _cacheMax;
    private readonly int _idleTimeoutSeconds;
    private readonly int _offTopicRoundsToUnload;
    private readonly int _breakerFailureThreshold;
    private readonly int _breakerOpenSeconds;

    public SkillLifecycle(Func<string, string, int, int> getConfig)
    {
        // module, key, fallback — 配置契约: 调用方传 ConfigSnapshot 委托, 本模块不自读 yaml
        _cacheMax = getConfig("skill", "lifecycle:session_cache_max", 32);
        _idleTimeoutSeconds = getConfig("skill", "lifecycle:idle_timeout_seconds", 1800);
        _offTopicRoundsToUnload = getConfig("skill", "lifecycle:off_topic_rounds_to_unload", 2);
        _breakerFailureThreshold = getConfig("skill", "executor:breaker_failure_threshold", 3);
        _breakerOpenSeconds = getConfig("skill", "executor:breaker_open_seconds", 120);
    }

    /// <summary>查询运行时状态 (无则 Unloaded)</summary>
    public SkillRuntime GetOrLoad(SkillDefinition skill)
    {
        lock (_lock)
        {
            if (!_runtimes.TryGetValue(skill.SkillId, out var rt))
            {
                rt = new SkillRuntime { Skill = skill, State = SkillState.Loaded };
                _runtimes[skill.SkillId] = rt;
            }
            return rt;
        }
    }

    /// <summary>激活 (Loaded/Suspended → Active); 缓存满时按最久未用回收非 Active 项</summary>
    public bool Activate(SkillDefinition skill)
    {
        lock (_lock)
        {
            var rt = GetOrLoadUnsafe(skill);
            EvictIfFullUnsafe();
            rt.State = SkillState.Active;
            rt.ActivatedAt = DateTimeOffset.UtcNow;
            rt.LastUsedAt = DateTimeOffset.UtcNow;
            rt.OffTopicRounds = 0;
            return true;
        }
    }

    /// <summary>轮次上报: 命中该 Skill 域 → 清零脱域计数; 未命中任何域 → 全部 Active 项脱域 +1,
    /// 达阈值自动卸载 (话题切换)</summary>
    public List<string> ReportRound(bool domainHit, string? hitSkillId = null)
    {
        lock (_lock)
        {
            var unloaded = new List<string>();
            var now = DateTimeOffset.UtcNow;
            foreach (var rt in _runtimes.Values)
            {
                if (rt.State != SkillState.Active)
                    continue;
                if (domainHit && rt.Skill.SkillId.Equals(hitSkillId, StringComparison.OrdinalIgnoreCase))
                {
                    rt.OffTopicRounds = 0;
                    rt.LastUsedAt = now;
                    continue;
                }
                rt.OffTopicRounds++;
                if (rt.OffTopicRounds >= _offTopicRoundsToUnload)
                {
                    rt.State = SkillState.Unloaded;
                    unloaded.Add(rt.Skill.SkillId);
                }
            }
            // 闲置超时回收
            foreach (var rt in _runtimes.Values)
            {
                if (rt.State == SkillState.Active &&
                    (now - rt.LastUsedAt).TotalSeconds >= _idleTimeoutSeconds)
                {
                    rt.State = SkillState.Suspended; // 闲置 → 挂起 (保状态可恢复)
                }
            }
            return unloaded;
        }
    }

    /// <summary>熔断判定: 熔断开启中 → true (调用方跳过执行直接降级)</summary>
    public bool IsBreakerOpen(string skillId)
    {
        lock (_lock)
        {
            return GetOrLoadByIdUnsafe(skillId).BreakerOpenUntil > DateTimeOffset.UtcNow;
        }
    }

    /// <summary>执行成功上报: 清零失败计数 (半开恢复)</summary>
    public void ReportSuccess(string skillId)
    {
        lock (_lock)
        {
            var rt = GetOrLoadByIdUnsafe(skillId);
            rt.ConsecutiveFailures = 0;
            rt.BreakerOpenUntil = DateTimeOffset.MinValue;
        }
    }

    /// <summary>执行失败上报: 连续失败达阈值 → 开启熔断 N 秒</summary>
    public void ReportFailure(string skillId)
    {
        lock (_lock)
        {
            var rt = GetOrLoadByIdUnsafe(skillId);
            rt.ConsecutiveFailures++;
            if (rt.ConsecutiveFailures >= _breakerFailureThreshold)
            {
                rt.BreakerOpenUntil = DateTimeOffset.UtcNow.AddSeconds(_breakerOpenSeconds);
                rt.ConsecutiveFailures = 0; // 重开计数窗口
            }
        }
    }

    public IReadOnlyList<SkillRuntime> Snapshot()
    {
        lock (_lock)
            return _runtimes.Values.ToList();
    }

    /// <summary>按 id 惰性取 (熔断计数不需要 Definition — Skill 字段留空待 Activate 补)</summary>
    private SkillRuntime GetOrLoadByIdUnsafe(string skillId)
    {
        if (!_runtimes.TryGetValue(skillId, out var rt))
        {
            rt = new SkillRuntime { Skill = new SkillDefinition { SkillId = skillId }, State = SkillState.Loaded };
            _runtimes[skillId] = rt;
        }
        return rt;
    }

    private SkillRuntime GetOrLoadUnsafe(SkillDefinition skill)
    {
        if (!_runtimes.TryGetValue(skill.SkillId, out var rt))
        {
            rt = new SkillRuntime { Skill = skill, State = SkillState.Loaded };
            _runtimes[skill.SkillId] = rt;
        }
        return rt;
    }

    private void EvictIfFullUnsafe()
    {
        var active = _runtimes.Values.Count(r => r.State == SkillState.Active);
        if (active < _cacheMax)
            return;
        var victim = _runtimes.Values
            .Where(r => r.State == SkillState.Active)
            .OrderBy(r => r.LastUsedAt)
            .FirstOrDefault();
        if (victim is not null)
            victim.State = SkillState.Unloaded; // 最久未用回收
    }
}
